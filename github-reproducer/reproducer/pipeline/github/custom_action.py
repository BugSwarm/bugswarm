import copy
import os
import shlex

from bugswarm.common import log
from reproducer.model.step import Step
from reproducer.utils import Utils

from . import github_action_env
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
    github_envs = github_action_env.get_all(github_builder, step_number, '')
    log.debug('Got GitHub {} envs.'.format(len(github_envs)))
    envs = copy.deepcopy(envs)

    log.debug('Setting up build code for custom commands action #{}'.format(step_number))

    env_str = ''.join('{}={} '.format(k, shlex.quote(str(v))) for k, v in github_envs.items())
    env_str += ''.join('{}={} '.format(k, shlex.quote(v)) for k, v in envs.items())
    env_str += github_builder.contexts.env.to_env_str()

    shell = step['shell'] if 'shell' in step else github_builder.SHELL
    working_dir = step['working-directory'] if 'working-directory' in step else working_dir

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
        exec_template = step['shell']

    step_name = 'Run {}'.format(step['run'].partition('\n')[0])

    run_command = Utils.substitute_expressions(github_builder.contexts, step['run'])

    return Step(step_name, step_number, True, None, run_command, env_str, step,
                working_dir=working_dir, filename=filename, exec_template=exec_template)
