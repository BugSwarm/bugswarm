import logging
import os
import subprocess
import sys
import time
from builtins import Exception
from pathlib import Path

from bugswarm.analyzer.analyzer import Analyzer
from bugswarm.common import log
from bugswarm.common.artifact_processing import utils as procutils
from bugswarm.common.artifact_processing.runners import ParallelArtifactRunner
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN, DOCKER_HUB_REPO, DOCKER_HUB_CACHED_REPO
from bugswarm.common.log_downloader import download_log
from bugswarm.common.rest_api.database_api import DatabaseAPI

_COPY_DIR = 'from_host'
_PROCESS_SCRIPT = 'patch_artifact_and_cache.py'
_FAILED_BUILD_SCRIPT = '/usr/local/bin/run_failed.sh'
_PASSED_BUILD_SCRIPT = '/usr/local/bin/run_passed.sh'
_TRAVIS_DIR = '/home/travis'
_HOME_DIR = str(Path.home())
_SANDBOX_DIR = '{}/bugswarm-sandbox'.format(_HOME_DIR)
_TMP_DIR = '{}/tmp'.format(_SANDBOX_DIR)

bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)


class PatchArtifactRunner(ParallelArtifactRunner):
    def __init__(self, image_tags_file: str, copy_dir: str, output_file: str, workers: int = 1):
        """
        :param image_tags_file: Path to a file containing a newline-separated list of image tags.
        :param copy_dir: A directory to copy into the host-side sandbox before any artifacts are processed.
        :param command: A callable used to determine what command(s) to execute in each artifact container. `command` is
                        called once for each processed artifact. The only parameter is the image tag of the artifact
                        about to be processed.
        :param workers: The same as for the superclass initializer.
        """
        with open(image_tags_file) as f:
            image_tags = list(map(str.strip, f.readlines()))
        super().__init__(image_tags, workers)
        self.copy_dir = copy_dir
        self.output_file = output_file

    def pre_run(self):
        _create_work_space()

    def process_artifact(self, image_tag: str):
        _cache_artifact_dependency(image_tag.strip(), self.output_file)

    def post_run(self):
        pass


def _create_work_space():
    _, stdout, stderr, _ = _run_command('mkdir -p {} && chmod 777 {}'.format(_TMP_DIR, _TMP_DIR))
    if stderr != '':
        log.error(stderr)
    _, stdout, stderr, _ = _run_command('cp -r from_host/ {}'.format(_SANDBOX_DIR))
    if stderr != '':
        log.error(stderr)


def _run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    return process, stdout, stderr, ok


def _print_error(msg, stdout=None, stderr=None):
    log.error(msg)
    if stdout != '':
        log.error('stdout:\n{}'.format(stdout))
    if stderr != '':
        log.error('stderr:\n{}'.format(stderr))


def _print_usage():
    log.info('Usage: python3 CacheMaven.py <image_tags_file> <task-name>')
    log.info('image_tags_file: Path to a file containing a newline-separated list of image tags to process.')
    log.info('task-name: Name of current task. Results will be put in ./output/<task-name>.csv.')


def _validate_input(argv):
    image_tags_file = argv[1]
    if not os.path.isfile(image_tags_file):
        log.error('The image_tags_file argument is not a file or does not exist. Exiting.')
        _print_usage()
        sys.exit(1)

    output_file = 'output/{}.csv'.format(argv[2])
    if not os.path.isdir('output'):
        os.mkdir('output')
    if os.path.isfile(output_file):
        os.remove(output_file)

    return image_tags_file, output_file


def _create_container(image_tag, docker_image_tag, f_or_p):
    """
    Creates a contaniner from the image on dockerhub repo DOCKER_HUB_REPO
    :param image_tag: The image tag associated with the artifact on DockerHub
    :param docker_image_tag: The full image tag for the image on DockerHub. E.g. bugswarm/images:image-tag
    :param f_or_p: Create the failed or passed container
    :return: Size of the image pulled from dockerhub
    """
    original_size = -1
    _, stdout, stderr, ok = _run_command('docker pull {}'.format(docker_image_tag))
    if ok:
        log.info('Successfully pulled {}'.format(image_tag))
        _, stdout, stderr, ok = _run_command('docker images %s:%s --format "{{.Size}}"' % (DOCKER_HUB_REPO, image_tag))
        if ok:
            original_size = stdout
    else:
        _print_error('Error pulling {}'.format(image_tag), stdout, stderr)
    if f_or_p is not None:
        _, stdout, stderr, ok = _run_command(
            'docker run -t -d  --name {}-{} {} /bin/bash'.format(image_tag, f_or_p, docker_image_tag))
        if ok:
            log.info('Created Docker container for {}'.format(image_tag))
        else:
            _print_error('Error creating Docker container for {}'.format(image_tag), stdout, stderr)
            sys.exit(1)
    else:
        _, stdout, stderr, ok = _run_command(
            'docker run -t -d  --name {} {} /bin/bash'.format(image_tag, docker_image_tag))
        if ok:
            log.info('Created Docker container for {}'.format(image_tag))
        else:
            _print_error('Error creating Docker container for {}'.format(image_tag), stdout, stderr)
            sys.exit(1)

    return original_size


def _copy_files_to_container(image_tag, f_or_p):
    """
    Copy patch_artifact_and_cache.py into container.
    :param image_tag: The image tag associated with the artifact on DockerHub
    :param f_or_p: Copying files to the failed or passed container
    :return: container_id
    """
    if f_or_p is not None:
        _, container_id, _, _ = _run_command(
            'docker ps -a --format "{{.ID}}" --filter "name=%s-%s"' % (image_tag, f_or_p))
        _, stdout, stderr, ok = _run_command(
            'docker cp {}/{}/{} {}:{}/{}'.format(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT, container_id,
                                                 _TRAVIS_DIR, _PROCESS_SCRIPT))
        if ok:
            log.info('Copied {} into container'.format(_PROCESS_SCRIPT))
        else:
            _print_error('Error copying {} into container for {}'.format(_PROCESS_SCRIPT, image_tag), stdout, stderr)
            sys.exit(1)

    else:
        _, container_id, _, _ = _run_command('docker ps -a --format "{{.ID}}" --filter "name=%s"' % image_tag)
        _, stdout, stderr, ok = _run_command(
            'docker cp {}/{}/{} {}:{}/{}'.format(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT, container_id,
                                                 _TRAVIS_DIR, _PROCESS_SCRIPT))
        if ok:
            log.info('Copied {} into container'.format(_PROCESS_SCRIPT))
        else:
            _print_error('Error copying {} into container for {}'.format(_PROCESS_SCRIPT, image_tag), stdout, stderr)
            sys.exit(1)

    return container_id


def _run_cache_script_and_build(container_id, f_or_p, repo, option, package_mode=False):
    """
    Run patch_artifact_and_cache.py inside the container. Adds write permissions to /usr/local/bin because the user
    travis needs to write to the run_failed/passed.sh scripts.
    :param container_id: id associated with the container for the artifact
    :param f_or_p: run patch and build for the failed or passed container
    :return: None
    """
    _, stdout, stderr, ok = _run_command('docker exec -td {} sudo chmod -R o+w /usr/local/bin'.format(container_id))
    if not ok:
        _print_error('Error changing permissions in container {}'.format(container_id), stdout, stderr)
        sys.exit(1)

    log.info('docker exec {} python {}/patch_artifact_and_cache.py {} {} {} {}'.format(container_id, _TRAVIS_DIR, repo,
                                                                                       f_or_p, option, package_mode))

    _, stdout, stderr, ok = _run_command(
        'docker exec {} python {}/patch_artifact_and_cache.py {} {} {} {}'.format(container_id, _TRAVIS_DIR, repo,
                                                                                  f_or_p, option, package_mode))
    if ok:
        log.info('Apply {} on container {} for {}'.format(option, container_id, f_or_p))
    else:
        _print_error('Apply {} on container {} for {}'.format(option, container_id, f_or_p), stdout,
                     stderr)


def _copy_files_out_of_container(image_tag, container_id, f_or_p):
    """
    Copies logs out of the container into a
    :param image_tag: The image tag associated with the artifact on DockerHub
    :param container_id: id associated with the container for the artifact
    :param f_or_p: Copying the log from the failed or passed container
    :return: None
    """
    _, stdout, stderr, ok = _run_command('cd $HOME')
    _, stdout, stderr, ok = _run_command('mkdir -p -m 777 {}/{}'.format(_TMP_DIR, image_tag))
    if ok:
        log.info('Successfully created directory for {}'.format(image_tag))
    else:
        _print_error('Error with mkdir', stdout, stderr)
    if f_or_p == 'failed':
        _, stdout, stderr, ok = _run_command(
            'docker cp {}:{}/log-failed.log {}/tmp/{}/log-failed.log'.format(container_id, _TRAVIS_DIR,
                                                                             procutils.HOST_SANDBOX, image_tag))
        if ok:
            log.info('Successfully copied failed files')
        else:
            _print_error('Error copying failed files', stdout, stderr)
    elif f_or_p == 'passed':
        _, stdout, stderr, ok = _run_command(
            'docker cp {}:{}/log-passed.log {}/tmp/{}/log-passed.log'.format(container_id, _TRAVIS_DIR,
                                                                             procutils.HOST_SANDBOX, image_tag))
        if ok:
            log.info('Successfully copied passed files')
        else:
            _print_error('Error copying passed files', stdout, stderr)


def _remove_files(container_id, f_or_p):
    """
    Remove logs and patch_artifact_and_cache.py from the container.
    :param container_id: id associated with the container for the artifact
    :return: None
    """
    if f_or_p in ['failed', 'passed']:
        _, stdout, stderr, ok = _run_command(
            'docker exec {} sudo rm {}/patch_artifact_and_cache.py {}/log-failed.log'.format(container_id, _TRAVIS_DIR,
                                                                                             _TRAVIS_DIR))
        if ok:
            log.info('Successfully removed files from {}-{}'.format(container_id, f_or_p))
        else:
            _print_error('Error removing files from {}-{}'.format(container_id, f_or_p), stdout, stderr)
    else:
        _, stdout, stderr, ok = _run_command(
            'docker exec {} sudo rm {}/patch_artifact_and_cache.py'.format(container_id, _TRAVIS_DIR))
        if ok:
            log.info('Successfully removed files from {}-{}'.format(container_id, f_or_p))
        else:
            _print_error('Error removing files from {}-{}'.format(container_id, f_or_p), stdout, stderr)


def _cache_artifact_dependency(image_tag, output_file):

    response = bugswarmapi.find_artifact(image_tag)
    if not response.ok:
        log.error('Unable to get artifact data for {}. Skipping this artifact.'.format(image_tag))
        with open(output_file, 'a+') as file:
            file.write('{}, API error\n'.format(image_tag))
        return

    artifact = response.json()
    failed_job_id = artifact['failed_job']['job_id']
    passed_job_id = artifact['passed_job']['job_id']
    repo = artifact['repo']

    _, stdout, _, _ = _run_command(
        'mkdir -m 777 {}/{}'.format(_TMP_DIR, failed_job_id))
    _, stdout, _, _ = _run_command(
        'mkdir -m 777 {}/{}'.format(_TMP_DIR, passed_job_id))

    failed_job_orig_log_path = '{}/{}/log-failed.log'.format(_TMP_DIR, failed_job_id)
    passed_job_orig_log_path = '{}/{}/log-passed.log'.format(_TMP_DIR, passed_job_id)

    result = download_log(failed_job_id, failed_job_orig_log_path)
    if not result:
        _print_error('Error downloading log for failed_job_id {}'.format(failed_job_id))

    result = download_log(passed_job_id, passed_job_orig_log_path)
    if not result:
        _print_error('Error downloading log for passed_job_id {}'.format(passed_job_id))

    docker_image_tag = '{}:{}'.format(DOCKER_HUB_REPO, image_tag)
    for option in ['offline', 'build']:
        for fail_or_pass in ['failed', 'passed']:
            # Create Docker container
            original_size = _create_container(image_tag, docker_image_tag, fail_or_pass)
            # Copy files into container
            container_id = _copy_files_to_container(image_tag, fail_or_pass)
            # Cache dependency
            _run_cache_script_and_build(container_id, fail_or_pass, repo, option)
            _copy_files_out_of_container(image_tag, container_id, fail_or_pass)
            # Remove docker container
            _, stdout, stderr, ok = _run_command('docker rm -f {}'.format(container_id))
            if ok:
                log.info('Successfully removed docker container {}'.format(container_id))
            else:
                _print_error('Error removing docker container {}'.format(container_id), stdout, stderr)
        if _verify_cache(image_tag, repo, option, original_size, output_file):
            break


def _pack_artifact(image_tag, repo, option):
    docker_image_tag = '{}:{}'.format(DOCKER_HUB_REPO, image_tag)
    # Create Docker container
    _create_container(image_tag, docker_image_tag, None)
    # Copy files into container
    container_id = _copy_files_to_container(image_tag, None)

    for fail_or_pass in ['failed', 'passed']:
        # Cache dependency
        _run_cache_script_and_build(container_id, fail_or_pass, repo, option, True)

    # Remove files
    _remove_files(container_id, None)
    log.info('Successfully packaged image {}'.format(image_tag))
    return container_id


def _verify_cache(image_tag, repo, option, original_size, output_file):
    # Commit, push and delete all the patched containers to DockerHub
    write_line = '{}, {}'.format(image_tag, original_size)
    status = 'failed'
    try:
        artifact = bugswarmapi.find_artifact(image_tag).json()
        failed_job_id = artifact['failed_job']['job_id']
        passed_job_id = artifact['passed_job']['job_id']

        failed_job_orig_log_path = '{}/{}/log-failed.log'.format(_TMP_DIR, failed_job_id)
        failed_job_repr_log_path = '{}/{}/log-failed.log'.format(_TMP_DIR, image_tag)
        passed_job_orig_log_path = '{}/{}/log-passed.log'.format(_TMP_DIR, passed_job_id)
        passed_job_repr_log_path = '{}/{}/log-passed.log'.format(_TMP_DIR, image_tag)

        analyzer = Analyzer()
        failed_job_reproduced_result = analyzer.compare_single_log(failed_job_repr_log_path, failed_job_orig_log_path,
                                                                   failed_job_id, build_system='maven')
        passed_job_reproduced_result = analyzer.compare_single_log(passed_job_repr_log_path, passed_job_orig_log_path,
                                                                   passed_job_id, build_system='maven')
        latest_layer_size = -1

        if failed_job_reproduced_result[0] and passed_job_reproduced_result[0]:
            log.info('Both failed and passed are reproduced for {}.'.format(image_tag))
            log.info('Packaging Docker image for {}.'.format(image_tag))
            container_id = _pack_artifact(image_tag, repo, option)
            _run_command('docker commit {} {}:{}'.format(container_id, DOCKER_HUB_CACHED_REPO, image_tag))

            _, stdout, stderr, ok = _run_command('docker image history %s:%s --format "{{.Size}}"'
                                                 % (DOCKER_HUB_CACHED_REPO, image_tag))

            if ok:
                latest_layer_size = stdout.split('\n')[0]

            _run_command('docker push {}:{}'.format(DOCKER_HUB_CACHED_REPO, image_tag))
            _run_command('docker rm -f {}'.format(container_id))
            status = 'succeed'

        write_line += ', {}, {}, {}'.format(status, latest_layer_size, option)
        with open(output_file, 'a+') as file:
            file.write(write_line + '\n')
    except (Exception, BaseException, TypeError):
        log.error('An error occurred while attempting to verify & cache {}.'.format(image_tag))
        with open(output_file, 'a+') as file:
            file.write(write_line + ', error' + '\n')

    return status == 'succeed'


def main(argv=None):
    log.config_logging(getattr(logging, 'INFO', None))
    if not DOCKER_HUB_CACHED_REPO:
        log.warning('DOCKER_HUB_CACHED_REPO not set. Skipping CacheDependency.')
        return

    argv = argv or sys.argv
    image_tags_file, output_file = _validate_input(argv)

    t_start = time.time()
    PatchArtifactRunner(image_tags_file, _COPY_DIR, output_file, workers=4).run()
    t_end = time.time()
    log.info('Running patch took {}s'.format(t_end - t_start))


if __name__ == '__main__':
    sys.exit(main())
