from ..job import Job
from .context import Context
from typing import Any, Tuple


class GitHubContext(Context):

    # TODO: Can get most of the info from API
    def __init__(self, job_object: Job):
        super().__init__()
        # A token to authenticate on behalf of the GitHub App installed on your repository.
        # TODO: add option to input a read only token (set in bugswarm/common/credentials.py).
        self.token = 'DUMMY'
        # The job_id of the current job.
        self.job = job_object.config.get('id-in-workflow', '')
        # For push, this is the branch or tag ref that was pushed. For pull_request, this is the PR merge branch.
        self.ref = ''
        # The commit SHA that triggered the workflow run.
        self.sha = job_object.sha
        # The owner and repository name.
        self.repository = job_object.repo
        # The repository owner's name
        self.repository_owner = self.repository.partition('/')[0]
        # The Git URL to the repository (i.e. git://github.com/<owner>/<name>.git)
        self.repositoryUrl = 'git://github.com/{}.git'.format(self.repository)
        # A unique number for each workflow run within a repository.
        self.run_id = job_object.job_id
        # A unique number for each run of a particular workflow in a repository.
        self.run_number = job_object.build.build_id
        # The number of days that workflow run logs and artifacts are kept.
        self.retention_days = '0'
        # A unique number for each attempt of a particular workflow run in a repository.
        self.run_attempt = '1'
        # The username of the user that triggered the initial workflow run.
        self.actor = ''
        self.triggering_actor = ''
        # The name of the workflow. If the workflow file doesn't specify a name,
        # the value of this property is the full path of the workflow file in the repository.
        self.workflow = ''
        # The head_ref or source branch of the pull request in a workflow run.
        self.head_ref = ''
        # The base_ref or target branch of the pull request in a workflow run.
        self.base_ref = ''
        # The name of the event that triggered the workflow run. (i.e. push/pull_request)
        self.event_name = ''
        # The full event webhook payload.
        self.event = {}
        # The URL of the GitHub server.
        self.server_url = 'https://github.com'
        # The URL of the GitHub REST API.
        self.api_url = 'https://api.github.com'
        # The URL of the GitHub GraphQL API.
        self.graphql_url = 'https://api.github.com/graphql'
        # The branch or tag name that triggered the workflow run.
        self.ref_name = ''
        # true if branch protections are configured for the ref that triggered the workflow run.
        self.ref_protected = 'false'
        # The type of ref that triggered the workflow run. Valid values are branch or tag.
        self.ref_type = 'branch'
        # !No explanation from GitHub docs.
        self.secret_source = ''
        # (Dynamic) The default working directory on the runner for steps.
        # This value depends on $GITHUB_WORKSPACE, $GITHUB_WORKSPACE depends on package/non-package mode.
        self.workspace = ''
        # (Dynamic) The name of the action currently running, or the id of a step. (Check GitHub docs for details)
        self.action = ''
        # The path to the file on the runner that contains the full event webhook payload.
        self.event_path = '/home/github/workflow/event.json'
        # (Dynamic) For a step executing an action, this is the owner and repository name of the action.
        self.action_repository = ''
        # (Dynamic) For a step executing an action, this is the ref of the action being executed.
        self.action_status = ''
        # (Dynamic) The path where an action is located. This property is only supported in composite actions.
        self.action_path = ''
        # (Dynamic) For a step executing an action, this is the ref of the action being executed.
        self.action_ref = ''
        # Path on the runner to the file that sets system PATH variables from workflow commands.
        self.path = '/home/github/workflow/paths.txt'
        # Path on the runner to the file that sets environment variables from workflow commands.
        self.env = '/home/github/workflow/envs.txt'

    def as_dict(self):
        return vars(self)

    def is_dynamic(self, key) -> bool:
        return key == 'workspace'

    def get(self, path: str, err_if_not_present=False, make_string=False) -> Tuple[Any, bool]:
        if path == 'workspace':
            return '${GITHUB_WORKSPACE}', True
        return super().get(path, err_if_not_present, make_string)
