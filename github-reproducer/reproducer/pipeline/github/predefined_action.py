import copy
import os
import shlex

import git
import yaml
from bugswarm.common import log
from reproducer.model.step import Step
from reproducer.utils import Utils

from . import github_action_env
from .github_builder import GitHubBuilder

IGNORE_ACTIONS = {'codecov/codecov-action', 'actions/checkout', 'actions/upload-artifact', 'actions/download-artifact',
                  'actions/cache', 'gradle/wrapper-validation-action', 'styfle/cancel-workflow-action'}


def get_action_data(github_builder: GitHubBuilder, step):
    """
        Get action metadata

        Parameters:
            github_builder (GitHubBuilder): The GitHubBuilder object
            step (dict): a predefined action step
        Returns:
            action_repo (str): Repo name
            action_ref (str): Repo ref
            action_path (str): action.yml location (Relative path), empty if path is action directory path
            action_path_abs (str): action.yml location (Absolute path in job runner container)
            action_dir (str): Name of the action directory
    """
    name = step['uses']
    action_repo_path, _, tag = name.partition('@')

    action_repo_path_split = action_repo_path.split('/')
    if len(action_repo_path_split) == 2 and tag != '':
        # uses: {owner}/{repo}@{ref}
        action_repo = action_repo_path.strip('/')
        action_path = ''
    elif len(action_repo_path_split) > 2 and tag != '':
        # uses: {owner}/{repo}/{path}@{ref}
        action_repo = '/'.join(action_repo_path_split[:2]).strip('/')
        action_path = '/'.join(action_repo_path_split[2:]).strip('/')
    elif action_repo_path.startswith('.'):
        # Local action
        action_repo = github_builder.job.repo
        action_path = action_repo_path
    else:
        # uses: {unknown}@{ref}
        log.error('The \'uses\' attribute has invalid value: {}'.format(name))
        return None, None, None, None, None

    action_dir = '@'.join((action_repo.replace('/', '-'), tag)) if tag != '' else action_repo.replace('/', '-')

    if action_path:
        action_path_abs = os.path.join(os.sep, 'home', 'github', github_builder.job.job_id, 'actions', action_dir,
                                       action_path)
    else:
        action_path_abs = os.path.join(os.sep, 'home', 'github', github_builder.job.job_id, 'actions', action_dir)

    return action_repo, tag, action_path, action_path_abs, action_dir


def parse(github_builder: GitHubBuilder, step_number, step, envs):
    """
    Parse a predefined action step.

    Parameters:
        github_builder (GitHubBuilder): The GitHubBuilder object
        step_number (str): zero-indexed step's number
        step (dict): a predefined action step
        envs (dict): environment variables from previous level
    Returns:
        step_number (str): step_number parameter
        step_name (str): human-readable name
        is_custom_command (bool): False
        setup (str): setup command
        run (run): run command
        envs (str): environment variables in string
        working_dir (str/None): working directory
        step (dict): step from input
    """
    name = step['uses']
    action_repo_path, _, tag = name.partition('@')

    # Throw error if we have:
    # Docker actions
    # Action in the same repository as the workflow

    if action_repo_path.startswith('docker'):
        log.error('The \'uses\' attribute has invalid value: {}'.format(name))
        GitHubBuilder.raise_error('Workflow file contains unsupported action in step {}'.format(step_number), 1)
        return

    if action_repo_path.lower() in IGNORE_ACTIONS:
        return

    log.debug('Setting up build code for predefined_action {}(#{})'.format(name, step_number))

    action_repo, action_ref, action_path, action_path_abs, action_dir = get_action_data(github_builder, step)
    if action_repo is None:
        GitHubBuilder.raise_error('Workflow file contains unsupported action in step {}'.format(step_number), 1)
        return

    # Download action source code
    clone_action_repo_if_not_exists(github_builder, action_dir, action_repo, tag)

    github_envs = github_action_env.get_all(github_builder, step_number, action_repo)
    log.debug('Got GitHub {} envs.'.format(len(github_envs)))

    envs = copy.deepcopy(envs)
    run_command = None
    is_setup = 'actions/setup-' in action_repo

    env_str = ''.join('{}={} '.format(k, shlex.quote(str(v))) for k, v in github_envs.items())
    env_str += ''.join('{}={} '.format(k, shlex.quote(v)) for k, v in envs.items())
    env_str += github_builder.contexts.env.to_env_str()

    setup_command = None
    filename = 'bugswarm_cmd.sh'

    try:
        if os.path.exists(os.path.join(github_builder.location, 'actions', action_dir, action_path, 'action.yml')):
            action_file_path = os.path.join(github_builder.location, 'actions', action_dir, action_path, 'action.yml')
        elif os.path.exists(os.path.join(github_builder.location, 'actions', action_dir, action_path, 'action.yaml')):
            action_file_path = os.path.join(github_builder.location, 'actions', action_dir, action_path, 'action.yaml')
        else:
            GitHubBuilder.raise_error('Predefined action in step {} is invalid'.format(step_number), 1)
            return

        with open(action_file_path, 'r') as f:
            action_file = yaml.safe_load(f)
            runs_using = action_file['runs']['using']

            env_str = process_input_env(github_builder, is_setup, step, action_file, env_str)

            if runs_using == 'node12' or runs_using == 'node16':
                # https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runs-for-javascript-actions
                runs_main = action_file['runs']['main']
                runs_pre = action_file['runs'].get('pre', None)
                runs_pre_if = action_file['runs'].get('pre-if', None)

                # TODO: evaluate runs_pre_if using contexts and expression
                if runs_pre:
                    setup_command = 'node {}'.format(os.path.join(action_path_abs, runs_pre))

                run_command = 'node {}'.format(os.path.join(action_path_abs, runs_main))
                log.debug('Run node using command: {}'.format(run_command))
            elif runs_using == 'composite':
                # https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runs-for-composite-actions
                # step is None or (Step number: str, Step name: str, Custom command: bool, Command to set up: str,
                # Command to run: str, Step environment variables: str, Step workflow data: dict)
                from . import custom_action, generate_build_script

                runs_steps = action_file['runs']['steps']

                sub_steps = []
                for sub_step_number, sub_step in enumerate(runs_steps):
                    github_builder.update_contexts(sub_step_number, sub_step, parent_step=step, update_composite=False,
                                                   reset_input=False)

                    if 'uses' in sub_step:
                        sub_steps.append(parse(github_builder, '{}.{}'.format(step_number, sub_step_number), sub_step,
                                               envs))
                    elif 'run' in sub_step:
                        sub_steps.append(custom_action.parse(
                            github_builder, '{}.{}'.format(step_number, sub_step_number), sub_step, envs, None
                        ))

                log.debug('Generating build script for composite action... ({} steps)'.format(len(sub_steps)))

                output_path = os.path.join(
                    github_builder.location, 'steps', 'bugswarm_{}_composite.sh'.format(step_number)
                )
                generate_build_script.generate(github_builder, sub_steps, output_path=output_path, setup=False)
                run_command = 'bugswarm_{}_composite.sh'.format(step_number)
                filename = 'bugswarm_{}.sh'.format(step_number)
            else:
                log.error('The \'using\' attribute has invalid value: {}'.format(runs_using))
                GitHubBuilder.raise_error('Predefined action in step {} is invalid'.format(step_number), 1)
                return

    except Exception as e:
        GitHubBuilder.raise_error(repr(e), 1)

    step_name = 'Run {}'.format(name)

    return Step(step_name, step_number, False, setup_command, run_command, env_str, step, filename=filename)


def process_input_env(github_builder, is_setup, step, action_file, env_str):
    action_inputs = {}
    # Turn workflow step's 'with' into environment variable string
    if 'with' in step:
        for key, value in step['with'].items():
            if is_setup and key == 'cache':
                # TODO: Need to ignore cache key, find out why.
                continue
            var_key = 'INPUT_{}'.format(key.upper().replace(' ', '_'))
            subbed_value = Utils.substitute_expressions(github_builder.contexts, str(value))
            action_inputs[var_key] = subbed_value
            env_str += '{}={} '.format(var_key, subbed_value)

    # Set default env.
    if 'inputs' in action_file:
        for key, value in action_file['inputs'].items():
            var_key = 'INPUT_{}'.format(key.upper().replace(' ', '_'))
            if var_key not in action_inputs and 'default' in value:
                subbed_value = Utils.substitute_expressions(github_builder.contexts, str(value['default']))
                action_inputs[var_key] = subbed_value
                env_str += '{}={} '.format(var_key, subbed_value)

    github_builder.contexts.inputs.update_inputs(action_inputs, merge=True)
    return env_str


def clone_action_repo_if_not_exists(github_builder: GitHubBuilder, action_name, repo, branch):
    # TODO: Clone the entire repo, then checkout based on branch, so we don't need to clone multiple time.
    # Example: https://github.com/guan-kevin/hunting-ground/runs/7925245589?check_suite_focus=true
    log.debug('Download action to {} '.format(os.path.join(github_builder.location, 'actions', action_name)))

    try:
        if not os.path.isdir(os.path.join(github_builder.location, 'actions', action_name)):
            if repo == github_builder.job.repo:
                github_builder.utils.copy_reproducing_repo_dir(
                    github_builder.job, os.path.join(github_builder.location, 'actions', action_name)
                )
            else:
                os.makedirs(os.path.join(github_builder.location, 'actions', action_name), exist_ok=True)
                if len(branch) == 40:
                    # input is SHA, not branch/tag
                    repo = git.Repo.clone_from(
                        github_builder.utils.construct_github_repo_url(repo),
                        os.path.join(github_builder.location, 'actions', action_name)
                    )
                    repo.git.checkout(branch)
                else:
                    git.Repo.clone_from(
                        github_builder.utils.construct_github_repo_url(repo),
                        os.path.join(github_builder.location, 'actions', action_name),
                        branch=branch
                    )
    except Exception as e:
        GitHubBuilder.raise_error(repr(e), 1)
