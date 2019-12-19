import subprocess

from typing import Union

from .shell_wrapper import ShellWrapper

_CommitSHA = str


def get_image_tag(repo: str, failed_job_id: Union[str, int]) -> str:
    """
    Construct the unique image tag identifying the pair with the given repository slug and failed job ID.

    :param repo: A repository slug.
    :param failed_job_id: A failed job ID for the pair for which the image tag will represent.
    :return: An image tag.
    """
    if not isinstance(repo, str):
        raise TypeError
    if not (isinstance(failed_job_id, str) or isinstance(failed_job_id, int)):
        raise TypeError
    if repo.count('/') != 1:
        raise ValueError('The repository slug should contain exactly one slash.')
    return '{}-{}'.format(repo.replace('/', '-'), failed_job_id)


def get_current_component_version_message(component_name: str) -> str:
    """
    Get a message that can be logged to indicate the version of the currently executing BugSwarm component.

    :param component_name: The name of the component. This name is not used to obtain the version. Instead, it is merely
                           used to compose the returned message.
    :return: A string that can be logged to indicate the version of the currently executing BugSwarm component.
    """
    if not isinstance(component_name, str):
        raise TypeError
    version = _get_current_component_version()[:7]
    return 'Using version {} of {}.'.format(version, component_name)


def _get_current_component_version() -> _CommitSHA:
    stdout, _, _ = ShellWrapper.run_commands('git rev-parse HEAD', stdout=subprocess.PIPE, shell=True)
    return stdout


def get_diff_stats(repo, sha_fail, sha_pass, gh_wrapper) -> (int, int, int):
    """
    Get the diff size between two commits by using Github API
    :param repo: repo slug e.g. bugswarm/common
    :param sha_fail: Github failed commit sha
    :param sha_pass: Github passed commit sha
    :param gh_wrapper: Github_wrapper
    :return: additions, deletions, changes
    """

    url = 'https://api.github.com/repos/{}/compare/{}...{}'.format(repo, sha_fail, sha_pass)

    # Try to make github api request
    response, response_json = gh_wrapper.get(url)

    if response is None or response_json is None:
        return -1, -1, -1

    # Initialize additions, etc to 0.
    additions = 0
    deletions = 0
    changes = 0

    # For every file changed, get the additions, etc
    for f in response_json['files']:
        additions += f['additions']
        deletions += f['deletions']
        changes += f['changes']

    return additions, deletions, changes
