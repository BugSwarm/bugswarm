import copy
import re
import shlex

from bugswarm.common import log
from reproducer.model.step import Step

from . import expressions, github_action_env
from .github_builder import GitHubBuilder


def parse(github_builder: GitHubBuilder, step_number, step, envs, working_dir):
    """
        Parse a custom action step.

        Parameters:
            github_builder (GitHubBuilder): The GitHubBuilder object
            step_number (str): zero-indexed step's number
            step (dict): a custom action step
            envs (dict): environment variables from previous level
            working_dir (str/None): working directory from previous level
        Returns:
            step_number (str): step_number parameter
            step_name (str): human-readable name
            is_custom_command (bool): True
            setup (str): setup command
            run (run): run command
            envs (str): environment variables in string
            working_dir (str/None): working directory
            step (dict): step from input
    """
    job_id = github_builder.job.job_id
    contexts = github_builder.contexts

    github_envs = github_action_env.get_all(github_builder, step_number, '')
    log.debug('Got GitHub {} envs.'.format(len(github_envs)))
    envs = copy.deepcopy(envs)

    log.debug('Setting up build code for custom commands action #{}'.format(step_number))

    env_str = ''.join('{}={} '.format(k, shlex.quote(str(v))) for k, v in github_envs.items())
    env_str += github_builder.contexts.env.to_env_str()

    run_command = expressions.substitute_expressions(step['run'], job_id, contexts)
    first_line = expressions.substitute_expressions(step['run'].split('\n')[0], job_id, contexts)
    step_name = 'Run {}'.format(first_line)

    # Substitute expressions for every step key that supports them
    # (see https://docs.github.com/en/actions/learn-github-actions/contexts#context-availability)
    continue_on_error = 'false'
    if 'continue-on-error' in step:
        continue_on_error = expressions.substitute_expressions(step['continue-on-error'], job_id, contexts)

    step_if = '$(test "$_GITHUB_JOB_STATUS" = "success" && echo true || echo false)'
    if 'if' in step:
        step_if = step['if']
        if not re.search(r'\b(success|failure|cancelled|always)\s*\(\s*\)', str(step['if'])):
            step_if = re.sub(r'^\s*\${{|}}\s*$', '', str(step['if']))
            step_if = 'success() && ({})'.format(expressions.to_str(step_if))
        step_if, _ = expressions.parse_expression(step_if, job_id, contexts)

    timeout_minutes = 360
    if 'timeout-minutes' in step:
        timeout_minutes = expressions.substitute_expressions(step['timeout-minutes'], job_id, contexts)

    if 'working-directory' in step:
        working_dir = expressions.substitute_expressions(step['working-directory'], job_id, contexts)

    # Set the shell command
    shell = github_builder.SHELL
    if 'shell' in step:
        shell = expressions.substitute_expressions(step['shell'], job_id, contexts)

    if shell:
        # This prevent "No such file or directory" error, substitute_expressions will put command in quotes
        # If shell is bash -l {0}
        # Wrong: env CI=true 'bash -l test.script'
        # Correct: env CI=true bash -l test.script
        shell = ' '.join(shlex.split(shell))

    if shell is None:
        filename = 'bugswarm_{}.sh'.format(step_number)
        exec_template = 'bash -e {}'
    elif shell == 'bash':
        filename = 'bugswarm_{}.sh'.format(step_number)
        exec_template = 'bash --noprofile --norc -eo pipefail {}'
    elif shell == 'python':
        filename = 'bugswarm_{}.py'.format(step_number)
        exec_template = 'python {}'
    elif shell == 'sh':
        filename = 'bugswarm_{}.sh'.format(step_number)
        exec_template = 'sh -e {}'
    elif shell == 'pwsh':
        filename = 'bugswarm_{}.ps1'.format(step_number)
        exec_template = 'pwsh -command ". \'{}\'"'
    else:
        # Default, custom shell
        filename = 'bugswarm_{}.script'.format(step_number)
        exec_template = shell

    return Step(step_name, step_number, True, None, run_command, env_str, step, working_dir=working_dir,
                filename=filename, exec_template=exec_template, continue_on_error=continue_on_error, step_if=step_if,
                timeout_minutes=timeout_minutes)
