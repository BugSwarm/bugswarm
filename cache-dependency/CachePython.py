import logging
import os
import sys
import time
from builtins import Exception
from pathlib import Path

from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN, DOCKER_HUB_REPO, DOCKER_HUB_CACHED_REPO
from python_log_parser import parse_log

from bugswarm.analyzer.analyzer import Analyzer
from bugswarm.common import log
from bugswarm.common.artifact_processing import utils as procutils
from bugswarm.common.artifact_processing.runners import ParallelArtifactRunner
from bugswarm.common.log_downloader import download_log
from bugswarm.common.rest_api.database_api import DatabaseAPI
from utils import copy_file_to_container, copy_log_out_of_container, create_container, create_work_space, \
    remove_file_from_container, pack_push_container, find_container_id_by_image_tag, run_command, print_error, \
    remove_container, mkdir, validate_input

_COPY_DIR = 'from_host'
_PROCESS_SCRIPT = 'patch_and_cache_python.py'
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
        create_work_space(_TMP_DIR, _SANDBOX_DIR)

    def process_artifact(self, image_tag: str):
        _cache_artifact_dependency(image_tag.strip(), self.output_file)

    def post_run(self):
        pass


def _print_usage():
    print('Usage: python3 CachePython.py <image_tags_file> <task-name>')
    print('       image_tags_file: Path to a file containing a newline-separated list of image tags to process.')
    print('       task-name: Name of current task. Results will be put in ./output/<task-name>.csv.')


def get_dependencies(log_path):
    pip_install_list = parse_log(log_path)
    return pip_install_list


def download_dependencies(image_tag, f_or_p, pip_packages: dict, job_id):
    package_cache_directory_host = '{}/tmp/{}/{}/requirements'.format(procutils.HOST_SANDBOX, image_tag, f_or_p)
    package_cache_directory_container = '/pypkg'

    mkdir(package_cache_directory_host)
    for python_version, package_list in pip_packages.items():
        if len(python_version) == 6:  # python
            python_image_name = python_version
        else:  # python3.6, python2.7.1, python3, etc.
            python_image_name = python_version[:6] + ':' + python_version[6:]
        python_image_name += '-slim'  # python:3.7-slim
        py_image_name = '{}-py'.format(job_id)
        cmd = 'docker run -v {}:{} --name {} -dt {} /bin/bash'.format(package_cache_directory_host,
                                                                      package_cache_directory_container,
                                                                      py_image_name,
                                                                      python_image_name,
                                                                      )
        _, stdout, stderr, ok = run_command(cmd)

        container_id = find_container_id_by_image_tag(py_image_name)

        for package in package_list:
            cmd = 'docker exec {} pip download --no-deps {} -d {}'.format(container_id, package,
                                                                          package_cache_directory_container)
            _, stdout, _, _ = run_command(cmd)
        remove_container(container_id)


def move_dependencies_into_container(image_tag, container_id, f_or_p):
    log.info('Moving dependencies to container {} for {}-{}'.format(container_id, image_tag, f_or_p))
    package_cache_directory = '{}/tmp/{}/{}/requirements'.format(procutils.HOST_SANDBOX, image_tag, f_or_p)
    destination = '/home/travis/build/{}/requirements'.format(f_or_p)
    copy_file_to_container(container_id, package_cache_directory, destination)

    cmd = 'docker exec -td {} sudo chown -R travis:travis {}'.format(container_id, destination)
    run_command(cmd)


def _run_cache_script_and_build(container_id, f_or_p, repo, package_mode=False):
    _, stdout, stderr, ok = run_command('docker exec -td {} sudo chmod -R o+w /usr/local/bin'.format(container_id))
    if not ok:
        print_error('Error changing permissions in container {}'.format(container_id), stdout, stderr)
        sys.exit(1)

    _, stdout, stderr, ok = run_command(
        'docker exec {} python {}/patch_and_cache_python.py {} {} {}'.format(container_id, _TRAVIS_DIR, repo,
                                                                             f_or_p, package_mode))
    if ok:
        log.info('Apply on container {} for {}'.format(container_id, f_or_p))
    else:
        print_error('Apply on container {} for {}'.format(container_id, f_or_p), stdout, stderr)


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

    mkdir('{}/{}'.format(_TMP_DIR, failed_job_id))
    mkdir('{}/{}'.format(_TMP_DIR, passed_job_id))

    failed_job_orig_log_path = '{}/{}/log-failed.log'.format(_TMP_DIR, failed_job_id)
    passed_job_orig_log_path = '{}/{}/log-passed.log'.format(_TMP_DIR, passed_job_id)

    result = download_log(failed_job_id, failed_job_orig_log_path)
    if not result:
        print_error('Error downloading log for failed_job_id {}'.format(failed_job_id))

    result = download_log(passed_job_id, passed_job_orig_log_path)
    if not result:
        print_error('Error downloading log for passed_job_id {}'.format(passed_job_id))

    docker_image_tag = '{}:{}'.format(DOCKER_HUB_REPO, image_tag)

    for fail_or_pass in ['failed', 'passed']:
        original_size = create_container(image_tag, docker_image_tag, fail_or_pass)
        container_id = find_container_id_by_image_tag(image_tag, fail_or_pass)
        src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT)
        des = os.path.join(_TRAVIS_DIR, _PROCESS_SCRIPT)
        copy_file_to_container(container_id, src, des)

        # Extract Dependencies && Download Dependencies
        if fail_or_pass == 'failed':
            pip_packages = get_dependencies(failed_job_orig_log_path)
            download_dependencies(image_tag, fail_or_pass, pip_packages, failed_job_id)
        else:
            pip_packages = get_dependencies(passed_job_orig_log_path)
            download_dependencies(image_tag, fail_or_pass, pip_packages, passed_job_id)

        move_dependencies_into_container(image_tag, container_id, fail_or_pass)
        # Patch build script then test
        _run_cache_script_and_build(container_id, fail_or_pass, repo)
        copy_log_out_of_container(image_tag, container_id, fail_or_pass, _TMP_DIR, _TRAVIS_DIR, _SANDBOX_DIR)
        remove_container(container_id)
    _verify_cache(image_tag, repo, original_size, output_file)


def _pack_artifact(image_tag, repo):
    docker_image_tag = '{}:{}'.format(DOCKER_HUB_REPO, image_tag)
    create_container(image_tag, docker_image_tag, None)
    container_id = find_container_id_by_image_tag(image_tag)
    src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT)
    des = os.path.join(_TRAVIS_DIR, _PROCESS_SCRIPT)
    copy_file_to_container(container_id, src, des)

    for fail_or_pass in ['failed', 'passed']:
        move_dependencies_into_container(image_tag, container_id, fail_or_pass)
        _run_cache_script_and_build(container_id, fail_or_pass, repo, True)

    # Remove patch script and logs
    patch_script_path = '{}/patch_and_cache_python.py'.format(_TRAVIS_DIR)
    remove_file_from_container(container_id, patch_script_path)
    log.info('Successfully packaged image {}'.format(image_tag))
    return container_id


def _verify_cache(image_tag, repo, original_size, output_file):
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
            container_id = _pack_artifact(image_tag, repo)
            latest_layer_size = pack_push_container(container_id, image_tag)
            remove_container(container_id)
            status = 'succeed'

        write_line += ', {}, {}'.format(status, latest_layer_size)
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
    image_tags_file, output_file = validate_input(argv, _print_usage)

    t_start = time.time()
    PatchArtifactRunner(image_tags_file, _COPY_DIR, output_file, workers=4).run()
    t_end = time.time()
    log.info('Running patch took {}s'.format(t_end - t_start))


if __name__ == '__main__':
    sys.exit(main())
