class GitHubContext(object):

    # TODO: Can get most of the info from API
    def __init__(self):
        # A token to authenticate on behalf of the GitHub App installed on your repository.
        self.token = ''
        # (Dynamic) The job_id of the current job.
        self.job = ''
        # For push, this is the branch or tag ref that was pushed. For pull_request, this is the PR merge branch.
        self.ref = ''
        # The commit SHA that triggered the workflow run.
        self.sha = ''
        # The owner and repository name.
        self.repository = ''
        # The repository owner's name
        self.repository_owner = ''
        # The Git URL to the repository (i.e. git://github.com/<owner>/<name>.git)
        self.repositoryUrl = ''
        # A unique number for each workflow run within a repository.
        self.run_id = '1'
        # A unique number for each run of a particular workflow in a repository.
        self.run_number = '1'
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
        self.ref_type = ''
        # !No explanation from GitHub docs.
        self.secret_source = ''
        # The default working directory on the runner for steps.
        self.workspace = '/home/github/build'
        # (Dynamic) The name of the action currently running, or the id of a step. (Check GitHub docs for details)
        self.action = ''
        # The path to the file on the runner that contains the full event webhook payload.
        self.event_path = '/home/github/workflow/event.json'
        # (Dynamic) For a step executing an action, this is the owner and repository name of the action.
        self.action_repository = ''
        # (Dynamic) For a step executing an action, this is the ref of the action being executed.
        self.action_status = ''
        # (Dynamic)The path where an action is located. This property is only supported in composite actions.
        self.action_path = ''
        # (Dynamic)For a step executing an action, this is the ref of the action being executed.
        self.action_ref = ''
        # Path on the runner to the file that sets system PATH variables from workflow commands.
        self.path = '/home/github/workflow/paths.txt'
        # Path on the runner to the file that sets environment variables from workflow commands.
        self.env = '/home/github/workflow/envs.txt'
