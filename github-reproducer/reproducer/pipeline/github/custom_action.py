import os
import copy
from bugswarm.common import log
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

    if 'env' in step and isinstance(step['env'], dict):
        step_envs = step['env']
        envs = {**envs, **step_envs}

    # Convert envs dictionary into a string
    env_str = GitHubBuilder.get_env_str(github_envs, envs)

    shell = step['shell'] if 'shell' in step else github_builder.SHELL
    working_dir = step['working-directory'] if 'working-directory' in step else working_dir

    if shell is None:
        filename = 'bugswarm_{}.sh'.format(step_number)
        run_command = 'bash -e {}'.format(filename)
    elif shell == 'bash':
        filename = 'bugswarm_{}.sh'.format(step_number)
        run_command = 'bash --noprofile --norc -eo pipefail {}'.format(filename)
    elif shell == 'python':
        filename = 'bugswarm_{}.py'.format(step_number)
        run_command = 'python {}'.format(filename)
    elif shell == 'sh':
        filename = 'bugswarm_{}.sh'.format(step_number)
        run_command = 'sh -e {}'.format(filename)
    elif shell == 'pwsh':
        filename = 'bugswarm_{}.ps1'.format(step_number)
        run_command = 'pwsh -command ". \'{}\'"'.format(filename)
    else:
        # Default, custom shell
        filename = 'bugswarm_{}.script'.format(step_number)
        run_command = step['shell'].replace('{0}', filename)

    if working_dir is not None:
        # TODO: if working_dir starts with / then use absolute path. Skip if working_dir is '.'
        working_dir_path = '${{BUILD_PATH}}/{}'.format(working_dir)
        setup_command = 'chmod u+x {} && cp {} {}'.format(filename, filename, working_dir_path)
    else:
        setup_command = 'chmod u+x {}'.format(filename)

    step_name = 'Run {}'.format(step['run'].partition('\n')[0])

    with open(os.path.join(github_builder.location, 'steps', filename), 'w') as f:
        f.write(step['run'])

    return step_number, step_name, True, setup_command, run_command, env_str, working_dir, step
