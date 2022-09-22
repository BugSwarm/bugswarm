import os
import git
import yaml
import copy
from bugswarm.common import log
from . import github_action_env
from .github_builder import GitHubBuilder


IGNORE_ACTIONS = {'codecov/codecov-action', 'actions/checkout', 'actions/upload-artifact', 'actions/download-artifact',
                  'actions/cache', 'gradle/wrapper-validation-action', 'styfle/cancel-workflow-action'}


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
        GitHubBuilder.raise_error('Workflow file contains unsupported action in step {}'.format(step_number), 1)
        return

    # Download action source code
    action_dir = '@'.join((action_repo.replace('/', '-'), tag)) if tag != '' else action_repo.replace('/', '-')
    clone_action_repo_if_not_exists(github_builder, action_dir, action_repo, tag)

    github_envs = github_action_env.get_all(github_builder, step_number, action_repo)
    log.debug('Got GitHub {} envs.'.format(len(github_envs)))

    envs = copy.deepcopy(envs)
    run_command = None
    is_setup = 'actions/setup-' in action_repo

    if 'env' in step and isinstance(step['env'], dict):
        # Merge step envs to workflow/job envs
        step_envs = step['env']
        envs = {**envs, **step_envs}

    if 'with' in step:
        for key, value in step['with'].items():
            if is_setup and key == 'cache':
                # TODO: Need to ignore cache key, find out why.
                continue
            envs['INPUT_{}'.format(key.upper().replace(' ', '_'))] = str(value).replace('\n', '\\n')

    setup_command = None

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

            if runs_using == 'node12' or runs_using == 'node16':
                # https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runs-for-javascript-actions
                runs_main = action_file['runs']['main']
                runs_pre = action_file['runs'].get('pre', None)
                runs_pre_if = action_file['runs'].get('pre-if', None)

                if action_path:
                    node_path = os.path.join(os.sep, 'home', 'github', github_builder.job.job_id, 'actions', action_dir,
                                             action_path)
                else:
                    node_path = os.path.join(os.sep, 'home', 'github', github_builder.job.job_id, 'actions', action_dir)

                # TODO: evaluate runs_pre_if using contexts and expression
                if runs_pre:
                    setup_command = 'node {}'.format(os.path.join(node_path, runs_pre))

                run_command = 'node {}'.format(os.path.join(node_path, runs_main))
                log.debug('Run node using command: {}'.format(run_command))
            elif runs_using == 'composite':
                # https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runs-for-composite-actions
                # step is None or (Step number: str, Step name: str, Custom command: bool, Command to set up: str,
                # Command to run: str, Step environment variables: str, Step workflow data: dict)
                from . import custom_action
                from . import generate_build_script

                runs_steps = action_file['runs']['steps']

                sub_steps = []
                for sub_step_number, sub_step in enumerate(runs_steps):
                    if 'uses' in sub_step:
                        sub_steps.append(parse(github_builder, '{}.{}'.format(step_number, sub_step_number), sub_step,
                                               envs))
                    elif 'run' in sub_step:
                        sub_steps.append(custom_action.parse(
                            github_builder, '{}.{}'.format(step_number, sub_step_number), sub_step, envs, None
                        ))

                log.debug('Generating build script for composite action... ({} steps)'.format(len(sub_steps)))

                output_path = os.path.join(github_builder.location, 'steps', 'bugswarm_{}.sh'.format(step_number))
                generate_build_script.generate(github_builder, sub_steps, output_path=output_path, setup=False)
                run_command = 'bash -e bugswarm_{}.sh'.format(step_number)
                setup_command = 'chmod u+x bugswarm_{}.sh'.format(step_number)
            else:
                log.error('The \'using\' attribute has invalid value: {}'.format(runs_using))
                GitHubBuilder.raise_error('Predefined action in step {} is invalid'.format(step_number), 1)
                return

            # Set default env.
            if 'inputs' in action_file:
                for key, value in action_file['inputs'].items():
                    if 'INPUT_{}'.format(key.upper().replace(' ', '_')) not in envs:
                        if 'default' in value:
                            # TODO: Evaluate expression
                            if '${{' in str(value['default']):
                                # TODO: SKIP them for now.
                                continue
                            envs['INPUT_{}'.format(key.upper().replace(' ', '_'))] = str(value['default']).replace(
                                '\n', '\\n')
    except Exception as e:
        GitHubBuilder.raise_error(repr(e), 1)

    # Convert envs dictionary into a string
    env_str = GitHubBuilder.get_env_str(github_envs, envs)
    step_name = 'Run {}'.format(name)

    return step_number, step_name, False, setup_command, run_command, env_str, None, step


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
