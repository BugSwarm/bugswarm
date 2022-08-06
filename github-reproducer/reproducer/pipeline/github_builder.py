import os
import git
import yaml
import copy
from bugswarm.common.shell_wrapper import ShellWrapper
from bugswarm.common import log
from reproducer.model.job import Job
from reproducer.reproduce_exception import ReproduceError

IGNORE_ACTIONS = {'codecov/codecov-action', 'actions/checkout', 'actions/upload-artifact', 'actions/download-artifact',
                  'actions/cache', 'gradle/wrapper-validation-action'}


class GitHubBuilder:

    def __init__(self, job: Job, location: str, utils):
        self.job = job
        self.location = location
        self.utils = utils
        # TODO: set them to correct values
        self.JOB_NAME = 'build'
        self.WORKFLOW_NAME = 'CI'
        self.ENV = {}

    def __str__(self):
        return 'GitHubBuilder({} @ {})'.format(self.job.job_id, self.location)

    def __repr__(self):
        return str(self)

    def build(self):
        # Create build script for GitHub job
        if 'steps' not in self.job.config or not isinstance(self.job.config['steps'], list):
            GitHubBuilder.raise_error(
                'Encountered an error while generating the build script: steps attribute is missing from config.', 1)

        steps = []  # (Step Number: str, Step Name: str, Step Commands: [str])
        for step_number, step in enumerate(self.job.config['steps']):
            if 'uses' in step:
                steps.append(self.predefined_action(step_number, step))
            elif 'run' in step:
                steps.append(self.custom_action(step_number, step))
        # TODO: Create build script based on steps.

    def clone_action_repo_if_not_exists(self, action_name, repo, branch):
        log.debug('Download action to {} '.format(os.path.join(self.location, action_name)))

        if not os.path.isdir(os.path.join(self.location, action_name)):
            os.makedirs(os.path.join(self.location, action_name), exist_ok=True)
            git.Repo.clone_from(
                self.utils.construct_github_repo_url(repo), os.path.join(self.location, action_name), branch=branch
            )

    def predefined_action_env(self, step_number, action_repo):
        return {
            'CI': True,
            'GITHUB_ACTION': step_number,
            'GITHUB_ACTION_PATH': '',
            'GITHUB_ACTION_REPOSITORY': action_repo,
            'GITHUB_ACTIONS': True,
            'GITHUB_ACTOR': 'bugswarm/bugswarm',
            'GITHUB_API_URL': 'https://api.github.com',
            'GITHUB_BASE_REF': '',
            'GITHUB_ENV': '/var/run/bugswarm/workflow/envs.txt',
            'GITHUB_EVENT_NAME': 'push',
            'GITHUB_EVENT_PATH': '/var/run/bugswarm/workflow/event.json',
            'GITHUB_GRAPHQL_URL': 'https://api.github.com/graphql',
            'GITHUB_HEAD_REF': '',
            'GITHUB_JOB': self.JOB_NAME,
            'GITHUB_PATH': '/var/run/bugswarm/workflow/paths.txt',
            'GITHUB_REF': 'master',
            'GITHUB_REF_NAME': '',
            'GITHUB_REF_TYPE': '',
            'GITHUB_REPOSITORY': self.job.repo,
            'GITHUB_REPOSITORY_OWNER': self.job.repo.split('/')[0],
            'GITHUB_RETENTION_DAYS': 0,
            'GITHUB_RUN_ATTEMPT': 1,
            'GITHUB_RUN_ID': 1,
            'GITHUB_RUN_NUMBER': 1,
            'GITHUB_SERVER_URL': 'https://github.com',
            'GITHUB_SHA': self.job.sha,
            'GITHUB_STEP_SUMMARY': '',
            'GITHUB_WORKFLOW': self.WORKFLOW_NAME,
            'GITHUB_WORKSPACE': '/home/github/{}'.format('failed' if self.job.is_failed else 'passed'),
            'RUNNER_ARCH': '',
            'RUNNER_NAME': '',
            'RUNNER_OS': 'Linux',
            'RUNNER_TEMP': '/tmp',
            'RUNNER_TOOL_CACHE': '/opt/hostedtoolcache'
        }

    def predefined_action(self, step_number, step):
        name = step['uses']
        action_repo, _, tag = name.partition('@')

        log.debug('Setting up build code for predefined_action {}(#{})'.format(name, step_number))

        if action_repo.lower() in IGNORE_ACTIONS:
            return

        # Download action source code
        self.clone_action_repo_if_not_exists(name, action_repo, tag)

        github_envs = self.predefined_action_env()

        envs = copy.deepcopy(self.ENV)
        cmd = ''
        is_setup = 'actions/setup-' in action_repo

        if 'with' in step:
            for key, value in step['with'].items():
                if is_setup and key == 'cache':
                    # TODO: Need to ignore cache key, find out why.
                    continue

                envs['INPUT_{}'.format(key.upper().replace(' ', '_'))] = str(value).replace('\n', '\\n')
        try:
            # TODO: Change action.yml based on 'uses'
            action_file = 'action.yml'
            with open(os.path.join(name.replace('/', '-'), action_file), 'r') as f:
                action_file = yaml.safe_load(f)
                # TODO: Handle non-nodejs predefined workflow.
                cmd = 'node /home/github/actions/' + name.replace('/', '-') + '/' + action_file['runs']['main']

                if 'inputs' in action_file:
                    for key, value in action_file['inputs'].items():
                        if 'INPUT_{}'.format(key.upper().replace(' ', '_')) not in envs:
                            if 'default' in value:
                                # TODO: Evaluate expression
                                envs['INPUT_{}'.format(key.upper().replace(' ', '_'))] = str(value['default']).replace(
                                    '\n', '\\n')
        except Exception as e:
            GitHubBuilder.raise_error(repr(e), 1)

        with open(os.path.join(self.location, 'step_{}.env'.format(step_number)), 'w') as f:
            for key, value in github_envs.items():
                if value != '':
                    f.write('{}="{}" '.format(key, value) if ' ' in str(value) else '{}={} '.format(key, value))

            for key, value in envs.items():
                if value != '':
                    f.write('{}="{}" '.format(key, value) if ' ' in str(value) else '{}={} '.format(key, value))

        return step_number, 'Run {}'.format(name), [cmd]

    def custom_action(self, step_number, step):
        commands = [line for line in step['run'].split('\n') if line]
        envs = copy.deepcopy(self.ENV)

        log.debug('Setting up build code for custom commands action #{}'.format(step_number))

        if 'env' in step:
            for key, value in step['env'].items():
                envs[key] = value

        with open(os.path.join(self.location, 'step_{}.env'.format(step_number)), 'w') as f:
            for key, value in envs.items():
                if value != '':
                    f.write('{}="{}" '.format(key, value) if ' ' in str(value) else '{}={} '.format(key, value))

        return step_number, 'Run {}'.format(commands[0]), commands

    @staticmethod
    def raise_error(message, return_code):
        if return_code:
            raise ReproduceError(message)
