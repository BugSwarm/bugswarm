import os
import yaml
import shlex
from bugswarm.common import log
from reproducer.model.job import Job
from bugswarm.common.credentials import GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper
from reproducer.reproduce_exception import ReproduceError


class GitHubBuilder:

    def __init__(self, job: Job, location: str, utils):
        self.job = job
        self.location = location
        self.build_path = '/home/github/build/{}'.format(self.job.repo)
        self.utils = utils
        self.JOB_NAME = 'build'  # Set this to the correct value.
        self.WORKFLOW_NAME = ''
        self.WORKFLOW_PATH = None
        self.ENVS = {}  # Workflow's ENV
        self.SHELL = None  # Workflow's default shell
        self.WORKING_DIR = None  # Workflow's default working-directory
        self.GITHUB_BASE_REF = ''
        self.GITHUB_HEAD_REF = ''

        # Not used. PR num always = -1
        pr_num = self.job.build.buildpair.pr_num
        self.GITHUB_REF = 'refs/pull/{}/merge'.format(pr_num) if pr_num > 0 else 'refs/heads/{}'.format(self.job.branch)
        self.GITHUB_REF_NAME = 'refs/pull/{}/merge'.format(pr_num) if pr_num > 0 else self.job.branch

        self.get_workflow_data()

        # predefined actions directory
        os.makedirs(os.path.join(location, 'actions'), exist_ok=True)
        os.makedirs(os.path.join(location, 'steps'), exist_ok=True)

    def __str__(self):
        return 'GitHubBuilder({} @ {})'.format(self.job.job_id, self.location)

    def __repr__(self):
        return str(self)

    def build(self):
        # Defer import to prevent circular dependencies
        from . import custom_action
        from . import predefined_action
        from . import generate_build_script

        log.debug('Building build script with {}'.format(self))

        # Create build script for GitHub job
        if 'steps' not in self.job.config or not isinstance(self.job.config['steps'], list):
            GitHubBuilder.raise_error(
                'Encountered an error while generating the build script: steps attribute is missing from config.', 1)

        # Merge job envs to workflow envs
        if 'env' in self.job.config and isinstance(self.job.config['env'], dict):
            job_envs = self.job.config['env']
            self.ENVS = {**self.ENVS, **job_envs}

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
            if 'uses' in step:
                steps.append(predefined_action.parse(self, str(step_number), step, self.ENVS))
            elif 'run' in step:
                steps.append(custom_action.parse(self, str(step_number), step, self.ENVS, self.WORKING_DIR))

        log.debug('Generating build script... ({} steps)'.format(len(steps)))
        generate_build_script.generate(self, steps, output_path=os.path.join(self.location, 'run.sh'))

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
            if 'event' in json_data and json_data['event'] == 'pull_request':
                self.GITHUB_HEAD_REF = json_data['head_branch']

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
