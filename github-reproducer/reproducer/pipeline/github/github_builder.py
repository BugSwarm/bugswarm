import os
import re
import shlex

import git
import yaml
from bugswarm.common import log
from bugswarm.common.credentials import GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper
from reproducer.model.context.root_context import RootContext
from reproducer.model.job import Job
from reproducer.reproduce_exception import ReproduceError
from reproducer.utils import Utils


class GitHubBuilder:

    def __init__(self, job: Job, location: str, utils: Utils):
        self.job = job
        self.location = location
        self.build_path = '/home/github/build/{}'.format(self.job.repo)
        self.utils = utils

        self.contexts = RootContext(job)
        self.action_name_counts = {}

        self.JOB_NAME = job.config.get('id-in-workflow', '')
        self.WORKFLOW_NAME = ''
        self.WORKFLOW_PATH = None
        self.ENVS = {}  # Workflow's ENV
        self.SHELL = None  # Workflow's default shell
        self.WORKING_DIR = None  # Workflow's default working-directory
        self.GITHUB_BASE_REF = ''
        self.GITHUB_HEAD_REF = ''
        self.ACTOR = {}
        self.TRIGGERING_ACTOR = {}
        self.REPOSITORY = {}
        self.HEAD_REPOSITORY = {}
        self.HEAD_COMMIT = {}
        self.PR = False
        self.first_checkout = True
        self.checkout_sha = utils.get_sha_from_original_log(job)  # List of SHA from actions/checkout action.
        self.PR_DATA = {}
        # Not used. PR num always = -1
        pr_num = self.utils.get_pr_from_original_log(job)
        self.PR = int(pr_num) if pr_num else -1

        self.GITHUB_REF = 'refs/pull/{}/merge'.format(self.PR) if self.PR else 'refs/heads/{}'.format(self.job.branch)
        self.GITHUB_REF_NAME = 'refs/pull/{}/merge'.format(self.PR) if self.PR else self.job.branch

        self.get_workflow_data()
        self.get_pr_data()

        from . import event_builder
        self.event_builder = event_builder.EventBuilder(self, self.PR > 0)

        self.init_contexts()

        # predefined actions directory
        os.makedirs(os.path.join(location, 'actions'), exist_ok=True)
        os.makedirs(os.path.join(location, 'steps'), exist_ok=True)
        os.makedirs(os.path.join(location, 'helpers'), exist_ok=True)

    def __str__(self):
        return 'GitHubBuilder({} @ {})'.format(self.job.job_id, self.location)

    def __repr__(self):
        return str(self)

    def build(self):
        # Defer import to prevent circular dependencies
        from . import (custom_action, generate_build_script,
                       generate_helper_scripts, predefined_action)

        log.debug('Building build script with {}'.format(self))

        # Create build script for GitHub job
        if 'steps' not in self.job.config or not isinstance(self.job.config['steps'], list):
            GitHubBuilder.raise_error(
                'Encountered an error while generating the build script: steps attribute is missing from config.', 1)

        # Set job's shell and working directory based on job['defaults']['run']
        if 'defaults' in self.job.config and 'run' in self.job.config['defaults']:
            if 'shell' in self.job.config['defaults']['run']:
                self.SHELL = self.job.config['defaults']['run']['shell']
            if 'working-directory' in self.job.config['defaults']['run']:
                self.WORKING_DIR = self.job.config['defaults']['run']['working-directory']

        # step is None or (Step number: str, Step name: str, Custom command: bool, Command to set up: str,
        # Command to run: str, Step environment variables: str, Step workflow data: dict)
        steps = []
        for step_number, step in enumerate(self.job.config['steps']):
            self.update_contexts(step_number, step)
            if 'uses' in step:
                steps.append(predefined_action.parse(self, str(step_number), step, self.ENVS))
            elif 'run' in step:
                steps.append(custom_action.parse(self, str(step_number), step, self.ENVS, self.WORKING_DIR))

        log.debug('Generating build script... ({} steps)'.format(len(steps)))
        generate_build_script.generate(self, steps, output_path=os.path.join(self.location, 'run.sh'))

        log.debug('Generating helper scripts...')
        generate_helper_scripts.generate(os.path.join(self.location, 'helpers'))

        log.debug('Generating event.json')
        self.event_builder.generate_json(os.path.join(self.location, 'event.json'))

    # TODO: Update PairFinder & get workflow file from BugSwarm's database.
    def get_workflow_data(self):
        # Use github_builder.job to fetch workflow data from GitHub API
        log.debug('Getting info for job {}'.format(self.job.job_id))

        github_wrapper = GitHubWrapper(GITHUB_TOKENS)
        run_url = 'https://api.github.com/repos/{}/actions/runs/{}'.format(
            self.job.repo, self.job.build.build_id
        )
        status, json_data = github_wrapper.get(run_url)

        try:
            if json_data is None:
                log.error('Failed to get job info from GitHub API invalid response.')
                return

            if 'actor' in json_data and 'login' in json_data['actor']:
                self.ACTOR = json_data['actor']

            if 'triggering_actor' in json_data:
                self.TRIGGERING_ACTOR = json_data['triggering_actor']

            if 'event' in json_data and json_data['event'] == 'pull_request':
                self.GITHUB_HEAD_REF = json_data['head_branch']

            if 'repository' in json_data:
                self.REPOSITORY = json_data['repository']

            if 'head_repository' in json_data:
                self.HEAD_REPOSITORY = json_data['head_repository']

            if 'head_commit' in json_data:
                self.HEAD_COMMIT = json_data['head_commit']

                try:
                    # pull_request is empty if base repo != head repo. Use the first one for now.
                    self.GITHUB_BASE_REF = json_data['pull_request'][0]['base']['ref']
                except TypeError:
                    pass
                except KeyError:
                    pass

            workflow_url = json_data['workflow_url']
            status, json_data = github_wrapper.get(workflow_url)

            self.WORKFLOW_NAME = json_data['name']
            self.WORKFLOW_PATH = json_data['path']

            reproducing_dir = self.utils.get_reproducing_repo_dir(self.job)
            with open(os.path.join(reproducing_dir, self.WORKFLOW_PATH), 'r') as f:
                workflow_file = yaml.safe_load(f)

                if 'env' in workflow_file and isinstance(workflow_file['env'], dict):
                    self.ENVS = workflow_file['env']

                if 'defaults' in workflow_file and 'run' in workflow_file['defaults']:
                    if 'shell' in workflow_file['defaults']['run']:
                        self.SHELL = workflow_file['defaults']['run']['shell']
                    if 'working-directory' in workflow_file['defaults']['run']:
                        self.WORKING_DIR = workflow_file['defaults']['run']['working-directory']
        except FileNotFoundError:
            log.error('Failed to open workflow file')
        except KeyError:
            log.error('Failed to get job info from GitHub API due to invalid response.')
        except Exception as e:
            log.error('Failed to get job info from GitHub API due to {}'.format(repr(e)))

    def get_pr_data(self):
        if self.PR > 0:
            github_wrapper = GitHubWrapper(GITHUB_TOKENS)
            pr_url = 'https://api.github.com/repos/{}/pulls/{}'.format(
                self.job.repo, self.PR
            )
            status, json_data = github_wrapper.get(pr_url)
            if json_data is not None and 'number' in json_data:
                self.PR_DATA = json_data
            else:
                log.error('Failed to get PR info from GitHub API due to invalid response.')

    def init_contexts(self):
        # Init github_context
        self.contexts.github.actor = self.ACTOR.get('login', '')
        self.contexts.github.ref = self.GITHUB_REF
        self.contexts.github.triggering_actor = self.TRIGGERING_ACTOR.get('login', '')
        self.contexts.github.workflow = self.WORKFLOW_NAME  # Workflow name = workflow path if we don't give it a name.
        self.contexts.github.head_ref = self.GITHUB_HEAD_REF
        self.contexts.github.base_ref = self.GITHUB_BASE_REF
        self.contexts.github.event_name = 'pull_request' if self.PR > 0 else 'push'
        self.contexts.github.event = self.event_builder.event

    def update_contexts(self, step_number, step, parent_step=None, update_composite=True, reset_input=True):
        # We set update_composite to False when we call update_contexts in composite action parser.
        # Update github.action
        if 'id' in step:
            self.contexts.github.action = step['id']
        elif 'uses' in step:
            name = re.sub(r'\W+', '', step['uses'])
            if name in self.action_name_counts:
                self.action_name_counts[name] += 1
                self.contexts.github.action = '{}{}'.format(name, self.action_name_counts[name])
            else:
                self.contexts.github.action = name
                self.action_name_counts[name] = 1
        else:
            name = '__run'
            if name in self.action_name_counts:
                self.action_name_counts[name] += 1
                self.contexts.github.action = '{}_{}'.format(name, self.action_name_counts[name])
            else:
                self.contexts.github.action = name
                self.action_name_counts[name] = 1

        self.contexts.github.action_repository = ''
        self.contexts.github.action_ref = ''
        if update_composite:
            self.contexts.github.action_path = ''

        if 'uses' in step:
            from . import predefined_action
            action_repo, action_ref, _, action_path_abs, _ = predefined_action.get_action_data(self, step)

            if action_repo is not None:
                self.contexts.github.action_repository = action_repo
                self.contexts.github.action_ref = action_ref
                if update_composite:
                    # action_path only supported in composite actions. However, we don't know if a predefined action is
                    # a composite action unless we run parse first. So we set this context to all predefined action.
                    self.contexts.github.action_path = action_path_abs

        # Update remaining github contexts
        self.contexts.github.action_status = ''  # TODO status of composite action (Dynamic)

        if reset_input:
            # Reset input when we are not in composite action
            self.contexts.inputs.update_inputs({})

        # Update env context
        self.contexts.env.update_env(self.ENVS, self.job, parent_step, step, self.contexts)

    @staticmethod
    def raise_error(message, return_code):
        if return_code:
            raise ReproduceError(message)

    @staticmethod
    def get_env_str(github_envs, envs):
        env_str = ''
        for key, value in github_envs.items():
            if value != '':
                env_str += '{}={} '.format(key, shlex.quote(str(value)))

        for key, value in envs.items():
            if value != '':
                env_str += '{}={} '.format(key, shlex.quote(str(value)))
        return env_str
