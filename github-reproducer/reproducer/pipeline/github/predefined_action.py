import copy
import os
import re
import shlex
import importlib.resources

import git
import yaml
from bugswarm.common import log
from reproducer.model.step import Step
from reproducer.utils import Utils
from reproducer.reproduce_exception import ReproduceError, UnsupportedWorkflowError, InvalidPredefinedActionError
import reproducer.resources as resources

from . import expressions, github_action_env
from .github_builder import GitHubBuilder

IGNORE_ACTIONS = {'codecov/codecov-action', 'actions/upload-artifact', 'actions/download-artifact',
                  'actions/cache', 'gradle/wrapper-validation-action', 'styfle/cancel-workflow-action',
                  'github/codeql-action/init', 'peaceiris/actions-gh-pages', 's0/git-publish-subdir-action'}
SPECIAL_ACTIONS = {'actions/checkout'}


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
            action_dir (str): Name of the action directory (Replaced / with -)
            name (str): Name of the action (defined in the workflow file)
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
        log.error("The 'uses' attribute has invalid value: {}".format(name))
        return None, None, None, None, None

    action_dir = '@'.join((action_repo.replace('/', '-'), tag)) if tag != '' else action_repo.replace('/', '-')

    if action_path:
        action_path_abs = os.path.join(os.sep, 'home', 'github', github_builder.job.job_id, 'actions', action_dir,
                                       action_path)
    else:
        action_path_abs = os.path.join(os.sep, 'home', 'github', github_builder.job.job_id, 'actions', action_dir)

    return action_repo, tag, action_path, action_path_abs, action_dir, name


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
    job_id = github_builder.job.job_id
    contexts = github_builder.contexts
    action_repo_path, _, tag = name.partition('@')

    # Throw error if we have:
    # Docker actions
    # Action in the same repository as the workflow

    if action_repo_path.startswith('docker'):
        log.error("The 'uses' attribute has invalid value: {}".format(name))
        raise UnsupportedWorkflowError('Workflow file contains unsupported action in step {}'.format(step_number))

    if action_repo_path.lower() in IGNORE_ACTIONS:
        return

    if action_repo_path == 'actions/checkout' and github_builder.first_checkout:
        if 'with' in step and ('repository' in step['with'] or 'path' in step['with']):
            raise UnsupportedWorkflowError('First checkout action uses unsupported parameters repository/path')

        # Ignore the first checkout action (we will set up repo ourselves).
        github_builder.first_checkout = False
        return

    log.debug('Setting up build code for predefined_action {}(#{})'.format(name, step_number))

    action_repo, action_ref, action_path, action_path_abs, action_dir, action_name = get_action_data(github_builder,
                                                                                                     step)
    if action_repo is None:
        raise UnsupportedWorkflowError('Workflow file contains unsupported action in step {}'.format(step_number))

    # Download action source code
    clone_action_repo_if_not_exists(github_builder, action_dir, action_repo, tag, action_name)

    github_envs = github_action_env.get_all(github_builder, step_number, action_repo)
    log.debug('Got GitHub {} envs.'.format(len(github_envs)))

    envs = copy.deepcopy(envs)
    run_command = None

    env_str = ''.join('{}={} '.format(k, shlex.quote(str(v))) for k, v in github_envs.items())
    env_str += contexts.env.to_env_str()

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
        step_if, _ = expressions.parse_expression(step_if, job_id, contexts, quote_result=True)

    step_name = 'Run {}'.format(name)

    timeout_minutes = 360
    if 'timeout-minutes' in step:
        timeout_minutes = expressions.substitute_expressions(step['timeout-minutes'], job_id, contexts)

    setup_command = None
    filename = 'bugswarm_cmd.sh'

    if os.path.exists(os.path.join(github_builder.location, 'actions', action_dir, action_path, 'action.yml')):
        action_file_path = os.path.join(github_builder.location, 'actions', action_dir, action_path, 'action.yml')
    elif os.path.exists(os.path.join(github_builder.location, 'actions', action_dir, action_path, 'action.yaml')):
        action_file_path = os.path.join(github_builder.location, 'actions', action_dir, action_path, 'action.yaml')
    else:
        raise InvalidPredefinedActionError(
            'Predefined action in step {} does not contain action.y(a)ml'.format(step_number))

    with open(action_file_path, 'r') as f:
        action_file = yaml.safe_load(f)
        runs_using = action_file['runs']['using']

        env_str = process_input_env(github_builder, action_repo, step, action_file, env_str)

        if runs_using in ['node12', 'node16', 'node20']:
            # https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runs-for-javascript-actions
            runs_main = action_file['runs']['main']
            runs_pre = action_file['runs'].get('pre', None)

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

            outputs = {}  # outputs dict
            if 'outputs' in action_file and isinstance(action_file['outputs'], dict):
                log.debug('Checking composite action outputs:')
                for key, content in action_file['outputs'].items():
                    if 'value' in content:
                        outputs[key] = expressions.substitute_expressions(
                            content['value'], job_id, contexts).strip("'")
                        log.debug('Key {}: {}'.format(key, outputs[key]))

            log.debug('Generating build script for composite action... ({} steps)'.format(len(sub_steps)))

            output_path = os.path.join(
                github_builder.location, 'steps', 'bugswarm_{}_composite.sh'.format(step_number)
            )
            generate_build_script.generate(github_builder, sub_steps, output_path=output_path, setup=False,
                                           outputs=outputs)
            run_command = '{}/bugswarm_{}_composite.sh'.format(github_builder.steps_dir, step_number)
            filename = 'bugswarm_{}.sh'.format(step_number)
        else:
            log.error("The 'using' attribute has invalid value: {}".format(runs_using))
            raise InvalidPredefinedActionError(
                "Predefined action in step {} uses invalid 'using' attribute '{}'".format(step_number, runs_using))

    return Step(step_name, step_number, False, setup_command, run_command, env_str, step, filename=filename,
                continue_on_error=continue_on_error, timeout_minutes=timeout_minutes, step_if=step_if)


def process_input_env(github_builder, action_repo, step, action_file, env_str):
    action_inputs = {}
    job_id = github_builder.job.job_id
    contexts = github_builder.contexts
    # Turn workflow step's 'with' into environment variable string
    if 'with' in step:
        for key, value in step['with'].items():
            # actions/setup-<lang> needs to ignore cache key to avoid @actions/cache. Also need to ignore token key.
            if 'actions/setup-' in action_repo and key in {'cache', 'token', 'overwrite-settings'}:
                continue
            # actions/checkout needs to ignore the ref key to avoid incorrect commit reset
            if action_repo == 'actions/checkout' and key == 'ref':
                continue

            var_key = 'INPUT_{}'.format(key.upper().replace(' ', '_'))
            subbed_value = expressions.substitute_expressions(value, job_id, contexts)
            action_inputs[var_key] = subbed_value
            env_str += '{}={} '.format(var_key, subbed_value)

    # Tell actions/setup-java not to override settings.xml
    if action_repo == 'actions/setup-java':
        var_key = 'INPUT_OVERWRITE-SETTINGS'
        value = False
        action_inputs[var_key] = value
        env_str += '{}={} '.format(var_key, value)

    # If the action is actions/checkout, add the ref key based on our checkout_sha array.
    if action_repo == 'actions/checkout':
        if github_builder.checkout_sha:
            sha = github_builder.checkout_sha.pop(0)
            log.debug("Use sha {} for actions/checkout's ref".format(sha))

            action_inputs['INPUT_REF'] = sha
            env_str += '{}={} '.format('INPUT_REF', sha)

    # If the action is actions/setup-<lang>, add empty string to token key (Issue #39)
    if 'actions/setup-' in action_repo:
        action_inputs['INPUT_TOKEN'] = ''
        env_str += '{}={} '.format('INPUT_TOKEN', '')

    # Set default env.
    if 'inputs' in action_file:
        for key, value in action_file['inputs'].items():
            var_key = 'INPUT_{}'.format(key.upper().replace(' ', '_'))
            if var_key not in action_inputs and 'default' in value:
                subbed_value = expressions.substitute_expressions(value['default'], job_id, contexts)
                action_inputs[var_key] = subbed_value
                env_str += '{}={} '.format(var_key, subbed_value)

    github_builder.contexts.inputs.update_inputs(action_inputs, merge=True)
    return env_str


def clone_action_repo_if_not_exists(github_builder: GitHubBuilder, action_dir, repo, tag, action_name):
    """
        Download predefined action

        Parameters:
            github_builder (GitHubBuilder): The GitHubBuilder object
            action_dir (str): Name of the action directory (Replaced / with -)
            repo (str): Repo name
            tag (str): Repo tag/sha/branch
            action_name (str): Name of the action (defined in the workflow file)
    """
    # TODO: Clone the entire repo, then checkout based on branch, so we don't need to clone multiple time.
    # Example: https://github.com/guan-kevin/hunting-ground/runs/7925245589?check_suite_focus=true
    log.debug('Download action to {} '.format(os.path.join(github_builder.location, 'actions', action_dir)))

    if not os.path.isdir(os.path.join(github_builder.location, 'actions', action_dir)):
        if repo == github_builder.job.repo:
            github_builder.utils.copy_reproducing_repo_dir(
                github_builder.job, os.path.join(github_builder.location, 'actions', action_dir)
            )
        elif repo in SPECIAL_ACTIONS:
            log.info('Getting {} action from resource directory.'.format(repo))
            os.makedirs(os.path.join(github_builder.location, 'actions', action_dir), exist_ok=True)

            # Get the action from resources directory
            file = importlib.resources.read_text(resources, repo.replace('/', '-') + '.yml')
            with open(os.path.join(github_builder.location, 'actions', action_dir, 'action.yml'), 'w') as f:
                f.write(file)
        else:
            os.makedirs(os.path.join(github_builder.location, 'actions', action_dir), exist_ok=True)
            action_repo_sha = None if len(tag) != 40 else tag
            if not action_repo_sha:
                action_repo_sha = github_builder.predefined_actions_sha.get(repo + '@' + tag, None)
                log.debug('Reset predefined action {} to {}.'.format(action_name, action_repo_sha))

            if action_repo_sha:
                # If we have action repo sha, use the sha to reset predefined action to original commit
                try:
                    r = git.Repo.clone_from(
                        github_builder.utils.construct_github_repo_url(repo),
                        os.path.join(github_builder.location, 'actions', action_dir)
                    )
                    r.git.checkout(action_repo_sha)
                    return
                except git.GitCommandError:
                    log.warning('Failed to reset predefined action {} to {}.'.format(action_name, action_repo_sha))
                    Utils.remove_predefined_action_dir(github_builder.location, action_dir)
                    pass

            if len(tag) == 40:
                raise ReproduceError('Failed to download predefined action {}'.format(action_name))

            # Otherwise, use the latest branch/tag
            log.warning('Using latest branch/tag {} for {}'.format(tag, action_name))
            git.Repo.clone_from(
                github_builder.utils.construct_github_repo_url(repo),
                os.path.join(github_builder.location, 'actions', action_dir),
                branch=tag
            )
