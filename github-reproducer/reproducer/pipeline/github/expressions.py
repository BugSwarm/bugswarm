import json
import re
import shlex

import pyparsing as pp


from bugswarm.common import log
from reproducer.reproduce_exception import ReproduceError


class Token:
    """
    Simple class for expression tokens.
    """

    def __init__(self, kind: str, val):
        self.kind = kind
        self.val = val

    def stringify(self, root_context) -> 'tuple[str, bool]':
        """
        Resolves the token into a string that can be interpolated into the build script.

        :returns: A tuple (`resolved_string`, `is_dynamic`) where `resolved_string` is the string to be interpolated
            and `is_dynamic` is whether or not the value is dynamic (`True` --> string should NOT be shell-quoted).
        """
        if self.kind == 'context':
            val, dyn = root_context.get(self.val)
            return to_str(val), dyn
        return to_str(self.val), False

    def to_eval_argument(self, root_context) -> str:
        if self.kind == 'context':
            val, _ = root_context.get(self.val)
            prefix = 's' if isinstance(val, str) else 'l'
        elif self.kind == 'string':
            prefix = 's'
        elif self.kind == 'number':
            prefix = 'n'
        elif self.kind == 'literal':
            prefix = 'l'
        elif self.kind == 'function':
            prefix = 'f'
        elif self.kind == 'op':
            prefix = 'o'
        elif self.kind == 'par':
            prefix = 'p'
        else:
            raise Exception('Unsupported token type "{}"'.format(self.kind))

        val, dyn = self.stringify(root_context)
        if not dyn:
            val = shlex.quote(val)
        return '{}:{}'.format(prefix, val)

    def __repr__(self) -> str:
        return f'{self.kind}:{self.val}'


def parse_expression(expression_string: str, job_id, root_context, quote_result=False) -> 'tuple[str, bool]':
    try:
        parsed = EXPRESSION_GRAMMAR.parse_string(expression_string, True).as_list()
    except pp.ParseException as e:
        raise ReproduceError('Could not parse expression: {}'.format(expression_string)) from e
    flattened = _flatten_token_list(parsed)

    if len(flattened) == 1 and flattened[0].kind in ['string', 'number', 'literal', 'context']:
        val, is_dynamic = flattened[0].stringify(root_context)
        if quote_result and not is_dynamic:
            return shlex.quote(val), True
        return val, is_dynamic
    else:
        eval_script = '/home/github/{}/helpers/eval_expression'.format(job_id)
        args = [tok.to_eval_argument(root_context) for tok in flattened]
        return '"$({} {})"'.format(eval_script, ' '.join(args)), True


def substitute_expressions(string, job_id, root_context):
    string = to_str(string)

    log.debug('Substituting expressions in string:', string)
    expr_regex = re.compile(r"\${{([^}']|'(''|[^'])*')*}}")

    # We don't just use re.sub because we have to make sure that everything *except* dynamic variables
    # is shell-quoted.
    parts = ['']
    idx = 0
    for match in re.finditer(expr_regex, string):
        parts[-1] += string[idx:match.start()]
        idx = match.end()
        resolved_expr, is_dynamic = parse_expression(match[0], job_id, root_context)

        if is_dynamic:
            # Shell-quote the static part (if it's not an empty string), then move on to the dynamic part.
            if parts[-1] != '':
                parts[-1] = shlex.quote(parts[-1])
            parts.append(str(resolved_expr))
            parts.append('')
        else:
            parts[-1] += str(resolved_expr)

    parts[-1] += string[idx:]
    if parts[-1] != '':
        parts[-1] = shlex.quote(parts[-1])

    result = ''.join(parts)
    log.debug('Resulting string after substitution:', result)
    return result


def to_str(val) -> str:
    if val is None:
        return ''
    if isinstance(val, str):
        return val
    return json.dumps(val)


def _create_grammar() -> pp.ParserElement:
    ppc = pp.pyparsing_common
    # ws = pp.Opt(pp.White()).suppress()

    kw_literal = pp.one_of(['true', 'false', 'null'], as_keyword=True)
    kw_literal.set_parse_action(lambda tokens: Token('literal', json.loads(tokens[0])))
    hex_literal = pp.Regex('[+-]?0x[0-9A-Fa-f]+').set_parse_action(pp.token_map(int, 16))
    num_literal = hex_literal | ppc.number
    num_literal.set_parse_action(lambda tokens: Token('number', tokens[0]))
    string_literal = pp.QuotedString(quote_char="'", esc_quote="''")
    string_literal.set_parse_action(lambda tokens: Token('string', tokens[0]))

    identifier = pp.Word(pp.identchars, pp.identbodychars + '-')

    function_name = pp.one_of([
        'contains', 'startsWith', 'endsWith', 'format', 'join', 'toJSON', 'fromJSON', 'hashFiles', 'success', 'always',
        'cancelled', 'failure'],
        as_keyword=True,
        caseless=True
    ).set_parse_action(lambda tokens: Token('function', tokens[0]))

    # An identifier followed by any amount of ".<identifier>"
    # We don't support object filters (".*") or indexing ("['index']") yet.
    variable = pp.Combine(identifier + pp.ZeroOrMore(
        '.' + identifier  # |
        # '.*' |
        # '[' + ws + (num_literal | string_literal) + ws + ']'
    )).set_parse_action(lambda tokens: Token('context', tokens[0]))

    expression = pp.Forward()
    workflow_function = pp.Group(
        function_name +
        pp.Suppress('(') +
        pp.Group(pp.Opt(pp.delimited_list(expression))) +
        pp.Suppress(')')
    )

    expression <<= pp.infix_notation(kw_literal | num_literal | string_literal | workflow_function | variable, [
        (pp.Literal('!').set_parse_action(lambda tokens: Token('op', tokens[0])), 1, pp.OpAssoc.RIGHT),
        (pp.one_of('< > <= >= == !=').set_parse_action(lambda tokens: Token('op', tokens[0])), 2, pp.OpAssoc.LEFT),
        (pp.Literal('&&').set_parse_action(lambda tokens: Token('op', tokens[0])), 2, pp.OpAssoc.LEFT),
        (pp.Literal('||').set_parse_action(lambda tokens: Token('op', tokens[0])), 2, pp.OpAssoc.LEFT),
    ])

    return pp.Suppress('${{') + expression + pp.Suppress('}}') | expression


EXPRESSION_GRAMMAR = _create_grammar()


def _should_unwrap(expr: pp.ParseResults):
    # Only unwrap nested lists
    if not isinstance(expr, list) or len(expr) != 1 or not isinstance(expr[0], list):
        return False

    # Do not unwrap functions in argument lists.
    if len(expr[0]) > 0 and isinstance(expr[0][0], Token) and expr[0][0].kind == 'function':
        return False
    return True


def _flatten_token_list(parsed_expression: pp.ParseResults) -> 'list[Token]':
    result = []

    while _should_unwrap(parsed_expression):
        parsed_expression = parsed_expression[0]
    for group in parsed_expression:
        if isinstance(group, list):
            result.extend([Token('par', '('), *_flatten_token_list(group), Token('par', ')')])
        else:
            result.append(group)

    return result
