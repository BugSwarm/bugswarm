#!/usr/bin/python3

import hashlib
import json
import math
import operator
import os
import re
import sys
from pathlib import Path


class Token:
    """Small helper class to help with typing."""

    def __init__(self, kind, val):
        self.kind = kind
        self.val = val

    def __repr__(self):
        return '{}:{}'.format(self.kind, self.val)


def to_str(x):
    # if isinstance(x, list):
    #     return '[Array]'
    # if isinstance(x, dict):
    #     return '[Object]'
    if x is None:
        return ''
    if isinstance(x, str):
        return x
    return json.dumps(x)


########################
# EXPRESSION FUNCTIONS #
########################


def contains(search, item):
    if not isinstance(search, (list, str)):
        search = to_str(search)
    item = to_str(item)
    return item in search


def startsWith(search, val):
    search = to_str(search).lower()
    val = to_str(val).lower()
    return search.startswith(val)


def endsWith(search, val):
    search = to_str(search).lower()
    val = to_str(val).lower()
    return search.endswith(val)


def format(fstr, *args):
    def repl(m):
        if m.group(0) == '{{':
            return '{'
        if m.group(0) == '}}':
            return '}'
        return to_str(args[int(m.group(1))])

    fstr = to_str(fstr)
    return re.sub(r'{{|{(\d+)}|}}', repl, fstr)


def join(arr, sep=','):
    sep = to_str(sep)
    if isinstance(arr, list):
        return sep.join(to_str(x) for x in arr)
    return to_str(arr)


def toJSON(val):
    return json.dumps(val, indent=2)


def fromJSON(val):
    return json.loads(val)


def hashFiles(*paths):
    """
    Adapted from https://github.com/actions/runner/blob/main/src/Misc/expressionFunc/hashFiles/src/hashFiles.ts
    """
    files = []
    for path in paths:
        assert not re.search(r'(^|/)\.\.(/|$)', path)
        files.extend(Path(os.environ['GITHUB_WORKSPACE']).glob(path))

    if not files:
        return ''

    result = hashlib.sha256()
    for filepath in files:
        with open(str(filepath), 'rb') as f:
            hash = hashlib.sha256(f.read())
        result.update(hash.digest())
    return result.hexdigest()


def always():
    return True


def success():
    return os.environ['_GITHUB_JOB_STATUS'] == 'success'


def failure():
    return os.environ['_GITHUB_JOB_STATUS'] == 'failure'


def cancelled():
    return os.environ['_GITHUB_JOB_STATUS'] == 'cancelled'


EXPRESSION_FUNCTIONS = {
    'contains': contains,
    'startswith': startsWith,
    'endswith': endsWith,
    'format': format,
    'join': join,
    'tojson': toJSON,
    'fromjson': fromJSON,
    'hashfiles': hashFiles,
    'always': always,
    'success': success,
    'failure': failure,
    'cancelled': cancelled,
}


#############
# OPERATORS #
#############


def to_num(x):
    if x is None or x is False or x == '':
        return 0
    if x is True:
        return 1
    if isinstance(x, (int, float)):
        return x
    try:
        num = json.loads(x)
        if not isinstance(num, (int, float)):
            return math.nan
        return num
    except (ValueError, TypeError):
        return math.nan


def apply_operator(op, lhs, rhs):
    try:
        op_fn = OPERATORS[op]
    except KeyError as e:
        raise ValueError('Unsupported operator: {}'.format(op)) from e

    if isinstance(lhs, str):
        lhs = lhs.lower()
    if isinstance(rhs, str):
        rhs = rhs.lower()

    if op != '!' and not isinstance(lhs, type(rhs)):
        lhs = to_num(lhs)
        rhs = to_num(rhs)

    return op_fn(lhs, rhs)


OPERATORS = {
    '!': lambda _, x: not x,
    '&&': lambda x, y: x and y,
    '||': lambda x, y: x or y,
    '>': operator.gt,
    '<': operator.lt,
    '>=': operator.ge,
    '<=': operator.le,
    '!=': operator.ne,
    '==': operator.eq,
}


##########################
# PARSING AND EVALUATION #
##########################


def group_paren(tokens: 'list[Token]'):
    result = []
    stack = []
    for tok in tokens:
        if tok.kind == 'par':
            if tok.val == '(':
                result.append(Token('group', []))
                stack.append(result)
                result = result[-1].val
            elif tok.val == ')':
                result = stack.pop()
            continue

        result.append(tok)

    if stack:
        raise Exception('Mismatched parentheses')
    return result


def evaluate(group):
    group = iter(group)

    result = None
    while True:
        try:
            prev_token = result
            result = next(group)
        except StopIteration:
            break

        if result.kind == 'group':
            result = evaluate(result.val)

        if result.kind == 'fun':
            args = next(group)
            if args.kind != 'group':
                raise Exception('Group not found after function')
            args = [evaluate(arg.val).val if arg.kind == 'group' else arg.val for arg in args.val]
            result = Token('val', EXPRESSION_FUNCTIONS[result.val](*args))
        elif result.kind == 'op':
            if result.val != '!' and (prev_token is None or prev_token.kind != 'val'):
                raise Exception('Binary operator has no LHS')

            next_token = next(group)
            if next_token.kind == 'group':
                next_token = evaluate(next_token.val)
            if result.val == '!':
                result = Token('val', apply_operator(result.val, None, next_token.val))
            else:
                result = Token('val', apply_operator(result.val, prev_token.val, next_token.val))

    return result


def main(args: 'list[str]'):
    tokens = []
    for arg in args:
        kind, _, val = arg.partition(':')
        # tokens.append(arg)
        if kind == 'l' or kind == 'n':
            if kind == 'l' and val == '':
                tokens.append(Token('val', None))
            else:
                tokens.append(Token('val', json.loads(val)))
        elif kind == 's':
            tokens.append(Token('val', val))
        elif kind == 'f':
            tokens.append(Token('fun', val.lower()))
        elif kind == 'o':
            tokens.append(Token('op', val))
        elif kind == 'p':
            tokens.append(Token('par', val))
        else:
            raise Exception('Unknown token type indicator: "{}"'.format(kind))

    groups = group_paren(tokens)
    result = evaluate(groups)

    print(to_str(result.val))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
