import os
import subprocess
from bugswarm.common import log
from bugswarm.common.credentials import DOCKER_HUB_REPO, DOCKER_HUB_CACHED_REPO
import sys


def validate_input(argv, print_usage):
    if len(argv) != 3:
        print_usage()
        exit(1)

    image_tags_file = argv[1]

    if not os.path.isfile(image_tags_file):
        print_error('{} is not a file or does not exist. Exiting.'.format(image_tags_file))
        print_usage()
        exit(1)

    output_file = 'output/{}.csv'.format(argv[2])
    if not os.path.isdir('output'):
        os.mkdir('output')

    return image_tags_file, output_file


def pack_push_container(container_id, image_tag):
    latest_layer_size = -1
    run_command('docker commit {} {}:{}'.format(container_id, DOCKER_HUB_CACHED_REPO, image_tag))

    _, stdout, stderr, ok = run_command('docker image history %s:%s --format "{{.Size}}"'
                                        % (DOCKER_HUB_CACHED_REPO, image_tag))

    if ok:
        latest_layer_size = stdout.split('\n')[0]

    _, _, stderr, ok = run_command('docker push {}:{}'.format(DOCKER_HUB_CACHED_REPO, image_tag))

    if ok:
        log.info("Successfully push cached {} to DockerHub".format(image_tag))
    else:
        print_error(stderr)

    return latest_layer_size


def mkdir(dir_path):
    _, stdout, stderr, _ = run_command('mkdir -p -m 777 {}'.format(dir_path))
    if stderr != '':
        log.error(stderr)


def create_work_space(tmp_dir, sandbox_dir):
    mkdir(tmp_dir)
    _, stdout, stderr, _ = run_command('cp -r from_host/ {}'.format(sandbox_dir))
    if stderr != '':
        log.error(stderr)


def print_error(msg, stdout=None, stderr=None):
    log.error(msg)
    if stdout:
        log.error('stdout:\n{}'.format(stdout))
    if stderr:
        log.error('stderr:\n{}'.format(stderr))


def copy_log_out_of_container(image_tag, container_id, f_or_p, tmp_dir, travis_dir, sandbox_path):
    mkdir('{}/{}'.format(tmp_dir, image_tag))

    # if cache pinned artifacts, make sure the log file name match existing logs
    if f_or_p == 'failed':
        src = '{}/log-failed.log'.format(travis_dir)
        des = '{}/tmp/{}/log-failed.log'.format(sandbox_path, image_tag)
    else:
        src = '{}/log-passed.log'.format(travis_dir)
        des = '{}/tmp/{}/log-passed.log'.format(sandbox_path, image_tag)
    copy_file_out_of_container(container_id, src, des)


def copy_file_to_container(container_id, src, des):
    _, stdout, stderr, ok = run_command(
        'docker cp {} {}:{}'.format(src, container_id, des))
    if ok:
        log.info('Copied {} into container'.format(src))
    else:
        print_error('Error copying {} into container for {}'.format(src, container_id), stdout, stderr)
        sys.exit(1)


def copy_file_out_of_container(container_id, src, des):
    _, stdout, stderr, ok = run_command('docker cp {}:{} {}'.format(container_id, src, des))
    if ok:
        log.info('Successfully copied {}'.format(src))
    else:
        print_error('Error copying files', stdout, stderr)


def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    return process, stdout, stderr, ok


def remove_container(container_id):
    _, stdout, stderr, ok = run_command('docker rm -f {}'.format(container_id))
    if ok:
        log.info('Successfully removed docker container {}'.format(container_id))
    else:
        print_error('Error removing docker container {}'.format(container_id), stdout, stderr)


def pull_image(image_tag, docker_image_tag):
    _, stdout, stderr, ok = run_command('docker pull {}'.format(docker_image_tag))
    if ok:
        log.info('Successfully pulled {}'.format(image_tag))
        _, stdout, stderr, ok = run_command('docker images %s:%s --format "{{.Size}}"' % (DOCKER_HUB_REPO, image_tag))
        if ok:
            original_size = stdout
    else:
        print_error('Error pulling {}'.format(image_tag), stdout, stderr)
        sys.exit(1)
    return original_size


def create_container(image_tag, docker_image_tag, f_or_p=None):
    if f_or_p is not None:
        container_name = '{}-{}'.format(image_tag, f_or_p)
    else:
        container_name = image_tag
    _, stdout, stderr, ok = run_command(
        'docker run -t -d  --name {} {} /bin/bash'.format(container_name, docker_image_tag))
    if ok:
        log.info('Created Docker container for {}'.format(image_tag))
        return stdout.strip()   # Container id
    else:
        print_error('Error creating Docker container for {}'.format(image_tag), stdout, stderr)
        sys.exit(1)


def remove_file_from_container(container_id, file_path):
    _, stdout, stderr, ok = run_command(
        'docker exec {} sudo rm {}'.format(container_id, file_path))
    if ok:
        log.info('Successfully removed {} from {}'.format(file_path, container_id))
    else:
        print_error('Error removing {} from {}'.format(file_path, container_id), stdout, stderr)
