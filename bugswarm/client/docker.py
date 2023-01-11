import os
import subprocess
import sys

from bugswarm.common import log
from bugswarm.common.shell_wrapper import ShellWrapper
import bugswarm.common.credentials as credentials

SCRIPT_DEFAULT = '/bin/bash'
HOST_SANDBOX_DEFAULT = '~/bugswarm-sandbox'
CONTAINER_SANDBOX_DEFAULT = '/bugswarm-sandbox'

if hasattr(credentials, 'DOCKER_HUB_REPO') and credentials.DOCKER_HUB_REPO != '#':
    DOCKER_HUB_REPO = credentials.DOCKER_HUB_REPO
else:
    DOCKER_HUB_REPO = 'bugswarm/images'
if hasattr(credentials, 'DOCKER_HUB_CACHED_REPO') and credentials.DOCKER_HUB_CACHED_REPO != '#':
    DOCKER_HUB_CACHED_REPO = credentials.DOCKER_HUB_CACHED_REPO
else:
    DOCKER_HUB_CACHED_REPO = 'bugswarm/cached-images'


# By default, this function downloads the image, enters the container, and executes '/bin/bash' in the container.
# The executed script can be changed by passing the script argument.
def docker_run(image_tag, use_sandbox, use_pipe_stdin, use_rm):
    assert isinstance(image_tag, str) and not image_tag.isspace()
    assert isinstance(use_sandbox, bool)
    assert isinstance(use_pipe_stdin, bool)
    assert isinstance(use_rm, bool)

    # First, try to pull the image.
    ok, image_location = docker_pull(image_tag)
    if not ok:
        return False

    # Communicate progress to the user.
    host_sandbox = _default_host_sandbox()
    container_sandbox = CONTAINER_SANDBOX_DEFAULT
    if use_sandbox:
        if not os.path.exists(host_sandbox):
            log.info('Creating', host_sandbox, 'as the host sandbox.')
            os.makedirs(host_sandbox, exist_ok=True)
        log.info('Binding host sandbox', host_sandbox, 'to container directory', container_sandbox)

    # Communicate progress to the user.
    if use_pipe_stdin:
        log.info('Entering the container and executing the contents of stdin inside the container.')
    else:
        log.info('Entering the container.')

    if use_rm:
        log.info('The container will be cleaned up after use.')

    # Prepare the arguments for the docker run command.
    volume_args = ['-v', '{}:{}'.format(host_sandbox, container_sandbox)] if use_sandbox else []
    # The -t option must not be used in order to use a heredoc.
    input_args = ['-i'] if use_pipe_stdin else ['-i', '-t']
    subprocess_input = sys.stdin.read() if use_pipe_stdin else None
    subprocess_universal_newlines = use_pipe_stdin
    rm_args = ['--rm'] if use_rm else []
    # If we're using a shared directory, we need to modify the start script to change the permissions of the shared
    # directory on the container side. However, this will also change the permissions on the host side.
    script_args = [SCRIPT_DEFAULT]
    if use_sandbox:
        start_command = '"sudo chmod -R 777 {} && cd {} && umask 000 && cd .. && {}"'.format(
            container_sandbox, container_sandbox, SCRIPT_DEFAULT)
        # These arguments represent a command of the following form:
        # /bin/bash -c "sudo chmod 777 <container_sandbox> && cd <container_sandbox> && umask 000 && /bin/bash"
        # So bash will execute chmod and umask and then start a new bash shell. From the user's perspective, the chmod
        # and umask commands happen transparently. That is, the user only sees the final new bash shell.
        script_args = [SCRIPT_DEFAULT, '-c', start_command]

    # Try to run the image.
    # The tail arguments must be at the end of the command.
    tail_args = [image_location] + script_args
    args = ['sudo', 'docker', 'run', '--privileged'] + rm_args + volume_args + input_args + tail_args
    command = ' '.join(args)
    print(command)
    _, _, returncode = ShellWrapper.run_commands(command,
                                                 input=subprocess_input,
                                                 universal_newlines=subprocess_universal_newlines,
                                                 shell=True)
    return returncode == 0


def docker_pull(image_tag):
    assert image_tag
    assert isinstance(image_tag, str)

    # Exit early if the image already exists locally.
    exists, image_location = _image_exists_locally(image_tag)
    if exists:
        return True, image_location

    image_location = _image_location(image_tag)
    command = 'sudo docker pull {}'.format(image_location)
    _, _, returncode = ShellWrapper.run_commands(command, shell=True)
    if returncode != 0:
        # Image is not cached. Attempt to pull from bugswarm/images.
        image_location = '{}:{}'.format(DOCKER_HUB_REPO, image_tag)
        command = 'sudo docker pull {}'.format(image_location)
        _, _, returncode = ShellWrapper.run_commands(command, shell=True)
        if returncode != 0:
            # Image is not in bugswarm/images
            log.error('Could not download the image', image_location)
        else:
            log.info('Downloaded the image', image_location + '.')
    else:
        log.info('Downloaded the image', image_location + '.')
    return returncode == 0, image_location


# Returns True and image_location if the image already exists locally.
def _docker_image_inspect(image_tag):
    image_location = _image_location(image_tag)
    command = 'sudo docker image inspect {}'.format(image_location)
    _, _, returncode = ShellWrapper.run_commands(command,
                                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    # For a non-existent image, docker image inspect has a non-zero exit status.
    if returncode != 0:
        image_location = '{}:{}'.format(DOCKER_HUB_REPO, image_tag)
        command = 'sudo docker image inspect {}'.format(image_location)
        _, _, returncode = ShellWrapper.run_commands(command,
                                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
        if returncode == 0:
            log.info('The image', image_location, 'already exists locally and is up to date.')
    else:
        log.info('The image', image_location, 'already exists locally and is up to date.')
    return returncode == 0, image_location


# Returns True and image_location if the image already exists locally.
def _image_exists_locally(image_tag):
    return _docker_image_inspect(image_tag)


def _image_location(image_tag):
    assert image_tag
    assert isinstance(image_tag, str)
    return DOCKER_HUB_CACHED_REPO + ':' + image_tag


def _default_host_sandbox():
    return os.path.expanduser(HOST_SANDBOX_DEFAULT)
