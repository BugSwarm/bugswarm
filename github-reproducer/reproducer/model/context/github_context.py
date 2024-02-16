from ..job import Job
from .context import Context
from typing import Any, Tuple


class GitHubContext(Context):

    # TODO: Can get most of the info from API
    def __init__(self, job_object: Job):
        super().__init__()

        repository = job_object.repo
        self.static_vals = {
            # A token to authenticate on behalf of the GitHub App installed on your repository.
            # TODO: add option to input a read only token (set in bugswarm/common/credentials.py).
            'token': 'DUMMY',
            # The job_id of the current job.
            'job': job_object.config.get('id-in-workflow', ''),
            # For push, this is the branch or tag ref that was pushed. For pull_request, this is the PR merge branch.
            'ref': '',
            # The commit SHA that triggered the workflow run.
            'sha': job_object.sha,
            # The owner and repository name.
            'repository': repository,
            # The repository owner's name
            'repository_owner': repository.partition('/')[0],
            # The Git URL to the repository (i.e. git://github.com/<owner>/<name>.git)
            'repositoryUrl': 'git://github.com/{}.git'.format(repository),
            # A unique number for each workflow run within a repository.
            'run_id': job_object.job_id,
            # A unique number for each run of a particular workflow in a repository.
            'run_number': job_object.build.build_id,
            # The number of days that workflow run logs and artifacts are kept.
            'retention_days': '0',
            # A unique number for each attempt of a particular workflow run in a repository.
            'run_attempt': '1',
            # The username of the user that triggered the initial workflow run.
            'actor': '',
            'triggering_actor': '',
            # The name of the workflow. If the workflow file doesn't specify a name,
            # the value of this property is the full path of the workflow file in the repository.
            'workflow': '',
            # The head_ref or source branch of the pull request in a workflow run.
            'head_ref': '',
            # The base_ref or target branch of the pull request in a workflow run.
            'base_ref': '',
            # The name of the event that triggered the workflow run. (i.e. push/pull_request)
            'event_name': '',
            # The full event webhook payload.
            'event': {},
            # The URL of the GitHub server.
            'server_url': 'https://github.com',
            # The URL of the GitHub REST API.
            'api_url': 'https://api.github.com',
            # The URL of the GitHub GraphQL API.
            'graphql_url': 'https://api.github.com/graphql',
            # The branch or tag name that triggered the workflow run.
            'ref_name': '',
            # true if branch protections are configured for the ref that triggered the workflow run.
            'ref_protected': 'false',
            # The type of ref that triggered the workflow run. Valid values are branch or tag.
            'ref_type': 'branch',
            # !No explanation from GitHub docs.
            'secret_source': '',
            # The path to the file on the runner that contains the full event webhook payload.
            'event_path': '/home/github/workflow/event.json',
            # Path on the runner to the file that sets system PATH variables from workflow commands.
            'path': '/home/github/workflow/paths.txt',
            # Path on the runner to the file that sets environment variables from workflow commands.
            'env': '/home/github/workflow/envs.txt',
        }

        self.dynamic_vals = {
            # (Dynamic) The default working directory on the runner for steps.
            # This value depends on $GITHUB_WORKSPACE, $GITHUB_WORKSPACE depends on package/non-package mode.
            'workspace': '',
            # (Dynamic) The name of the action currently running, or the id of a step. (Check GitHub docs for details)
            'action': '',
            # (Dynamic) For a step executing an action, this is the owner and repository name of the action.
            'action_repository': '',
            # (Dynamic) For a step executing an action, this is the ref of the action being executed.
            'action_status': '',
            # (Dynamic) The path where an action is located. This property is only supported in composite actions.
            'action_path': '',
            # (Dynamic) For a step executing an action, this is the ref of the action being executed.
            'action_ref': '',
        }

    def as_dict(self):
        return {**self.static_vals, **self.dynamic_vals}

    def set(self, name, val):
        if name in self.static_vals:
            self.static_vals[name] = val
        elif name in self.dynamic_vals:
            self.dynamic_vals[name] = val
        else:
            raise KeyError(name)

    def is_dynamic(self, key) -> bool:
        return key.lower() in self.dynamic_vals

    def get(self, path: str, err_if_not_present=False, make_string=False) -> Tuple[Any, bool]:
        if path.lower() == 'workspace':
            return '${GITHUB_WORKSPACE}', True
        return super().get(path, err_if_not_present, make_string)
