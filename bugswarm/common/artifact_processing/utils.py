"""
Convenience methods and constants to facilitate a processing workflow involving BugSwarm artifact images.
"""
import os
import shutil

from ..shell_wrapper import ShellWrapper
from ..rest_api.database_api import DatabaseAPI

REPOS_DIR = '/home/travis/build'
_SANDBOX = 'bugswarm-sandbox'
HOST_SANDBOX = os.path.join(os.path.expanduser('~'), _SANDBOX)
CONTAINER_SANDBOX = os.path.join(os.sep, _SANDBOX)


def copy_to_host_sandbox(filepath: str):
    """
    Copy a file into the host-side sandbox.
    :param filepath: Path to the file to be copied.
    """
    if not filepath:
        raise ValueError
    if not os.path.isfile(filepath):
        raise FileNotFoundError
    shutil.copy(filepath, HOST_SANDBOX)


def get_repo(image_tag: str, token: str):
    """
    Get the repository slug for the artifact represented by `image_tag`.
    """
    if not image_tag:
        raise ValueError
    bugswarmapi = DatabaseAPI(token=token)
    resp = bugswarmapi.find_artifact(image_tag)
    resp.raise_for_status()
    return resp.json()['repo']


def get_failed_repo_dir(image_tag: str, token: str):
    """
    Get the path to the failed repository in the container.
    """
    if not image_tag:
        raise ValueError
    return os.path.join(REPOS_DIR, 'failed', *get_repo(image_tag, token).split('/'))


def get_passed_repo_dir(image_tag: str, token: str):
    """
    Get the path to the passed repository in the container.
    """
    if not image_tag:
        raise ValueError
    return os.path.join(REPOS_DIR, 'passed', *get_repo(image_tag, token).split('/'))


def run_artifact(image_tag: str, command: str):
    """
    Assumes that the caller wants to use the sandbox and stdin piping features of the BugSwarm client since this
    function will likely be called in the context of an artifact processing workflow.

    :param image_tag: The image tag representing the artifact image to run.
    :param command: A string containing command(s) to execute in the artifact container. Will be piped to the container
                    process' standard input stream.
    :return: A 2-tuple of
             - the combined output of stdout and stderr
             - the return code of the subprocess that ran the artifact container.
    """
    if not image_tag:
        raise ValueError
    if not command:
        raise ValueError
    combined, _, returncode = ShellWrapper.run_commands(
        'bugswarm run --image-tag {} --use-sandbox --pipe-stdin'.format(image_tag),
        input=command,
        universal_newlines=True,
        shell=True)
    return combined, returncode
