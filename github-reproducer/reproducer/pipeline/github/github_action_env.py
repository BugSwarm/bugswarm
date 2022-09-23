from .github_builder import GitHubBuilder


def get_all(github_builder: GitHubBuilder, step_number, action_repo):
    # https://docs.github.com/en/actions/learn-github-actions/environment-variables
    return {
        # Always set to true.
        'CI': True,
        # A token to authenticate on behalf of the GitHub App installed on your repository.
        # TODO: add option to input a read only token (set in bugswarm/common/credentials.py).
        'GITHUB_TOKEN': 'DUMMY',
        # The name of the action currently running, or the id of a step. Ex: actionscheckout, __run
        'GITHUB_ACTION': step_number,  # TODO: Fix this
        # The path where an action is located. (composite actions)
        'GITHUB_ACTION_PATH': '',
        # For a step executing an action, this is the owner and repository name of the action.
        'GITHUB_ACTION_REPOSITORY': action_repo,
        # Always set to true when GitHub Actions is running the workflow.
        'GITHUB_ACTIONS': True,
        # The name of the person or app that initiated the workflow.
        'GITHUB_ACTOR': github_builder.ACTOR,
        'GITHUB_API_URL': 'https://api.github.com',
        # The name of the base ref or target branch of the pull request in a workflow run. (PR only)
        'GITHUB_BASE_REF': github_builder.GITHUB_BASE_REF,  # TODO: Still need to fix this.
        # The path on the runner to the file that sets environment variables from workflow commands.
        'GITHUB_ENV': '/home/github/workflow/envs.txt',
        # The name of the event that triggered the workflow.
        'GITHUB_EVENT_NAME': 'pull_request' if github_builder.job.is_pr else 'push',
        # The path to the file on the runner that contains the full event webhook payload.
        'GITHUB_EVENT_PATH': '/home/github/workflow/event.json',
        # https://api.github.com/graphql
        'GITHUB_GRAPHQL_URL': 'https://api.github.com/graphql',
        # The head ref or source branch of the pull request in a workflow run. (PR only)
        'GITHUB_HEAD_REF': github_builder.GITHUB_HEAD_REF,
        # The job_id of the current job.
        'GITHUB_JOB': github_builder.JOB_NAME,
        # The path on the runner to the file that sets system PATH variables from workflow commands.
        'GITHUB_PATH': '/home/github/workflow/paths.txt',
        # The branch or tag ref that triggered the workflow run.
        # Push: refs/heads/<branch>, PR: refs/pull/<pr_number>/merge
        'GITHUB_REF': github_builder.GITHUB_REF,
        # The branch or tag name that triggered the workflow run.
        # Push: <branch>, PR: <pr_number>/merge
        'GITHUB_REF_NAME': github_builder.GITHUB_REF_NAME,
        # The type of ref that triggered the workflow run.
        'GITHUB_REF_TYPE': 'branch',
        # The owner and repository name.
        'GITHUB_REPOSITORY': github_builder.job.repo,
        # The repository owner's name.
        'GITHUB_REPOSITORY_OWNER': github_builder.job.repo.split('/')[0],
        'GITHUB_RETENTION_DAYS': 0,
        'GITHUB_RUN_ATTEMPT': 1,
        'GITHUB_RUN_ID': 1,
        'GITHUB_RUN_NUMBER': 1,
        'GITHUB_SERVER_URL': 'https://github.com',
        # The commit SHA that triggered the workflow.
        'GITHUB_SHA': github_builder.job.sha,
        # The path on the runner to the file that contains job summaries from workflow commands.
        'GITHUB_STEP_SUMMARY': '',  # TODO: Fix this
        # The name of the workflow.
        'GITHUB_WORKFLOW': github_builder.WORKFLOW_NAME,
        # GITHUB_WORKSPACE: Set in generate_build_script
        'RUNNER_ARCH': 'X64',
        'RUNNER_NAME': 'Bugswarm GitHub Actions Runner',  # Don't know which name to use.
        'RUNNER_OS': 'Linux',
        'RUNNER_TEMP': '/tmp',
        'RUNNER_TOOL_CACHE': '/opt/hostedtoolcache',
        'RUNNER_DEBUG': 1
    }
