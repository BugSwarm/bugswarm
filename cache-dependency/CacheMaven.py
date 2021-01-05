import logging
import os
import sys
import time
import argparse
from builtins import Exception
from pathlib import Path

from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN, DOCKER_HUB_REPO, DOCKER_HUB_CACHED_REPO

from bugswarm.analyzer.analyzer import Analyzer
from bugswarm.common import log
from bugswarm.common.artifact_processing import utils as procutils
from bugswarm.common.artifact_processing.runners import ParallelArtifactRunner
from bugswarm.common.log_downloader import download_log
from bugswarm.common.rest_api.database_api import DatabaseAPI
from utils import copy_file_to_container, copy_file_out_of_container, copy_log_out_of_container, \
    change_container_file_owner, create_container, pull_image, create_work_space, remove_file_from_container, \
    pack_push_container, run_command, print_error, remove_container, mkdir, validate_input

_COPY_DIR = 'from_host'
_PROCESS_SCRIPT = 'patch_and_cache_maven.py'
_FAILED_BUILD_SCRIPT = '/usr/local/bin/run_failed.sh'
_PASSED_BUILD_SCRIPT = '/usr/local/bin/run_passed.sh'
_TRAVIS_DIR = '/home/travis'
_HOME_DIR = str(Path.home())
_SANDBOX_DIR = '{}/bugswarm-sandbox'.format(_HOME_DIR)
_TMP_DIR = '{}/tmp'.format(_SANDBOX_DIR)

bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)


class PatchArtifactRunner(ParallelArtifactRunner):
    def __init__(self, image_tags_file: str, copy_dir: str, output_file: str, args: argparse.Namespace,
                 workers: int = 1):
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
        self.args = args

    def pre_run(self):
        create_work_space(_TMP_DIR, _SANDBOX_DIR)

    def process_artifact(self, image_tag: str):
        _cache_artifact_dependency(image_tag.strip(), self.output_file, self.args)

    def post_run(self):
        pass


def _run_cache_script_and_build(container_id, f_or_p, repo, option, package_mode=False):
    _, stdout, stderr, ok = run_command('docker exec -td {} sudo chmod -R o+w /usr/local/bin'.format(container_id))
    if not ok:
        print_error('Error changing permissions in container {}'.format(container_id), stdout, stderr)
        sys.exit(1)

    _, stdout, stderr, ok = run_command(
        'docker exec {} python {}/patch_and_cache_maven.py {} {} {} {}'.format(container_id, _TRAVIS_DIR, repo,
                                                                               f_or_p, option, package_mode))
    if ok:
        log.info('Apply {} on container {} for {}'.format(option, container_id, f_or_p))
    else:
        print_error('Apply {} on container {} for {}'.format(option, container_id, f_or_p), stdout,
                    stderr)


def _cache_artifact_dependency(image_tag, output_file, args):
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
    original_size = pull_image(image_tag, docker_image_tag)
    for option in ['build', 'offline']:
        for fail_or_pass in ['failed', 'passed']:
            container_id = create_container(args.task_name, image_tag, docker_image_tag, option, fail_or_pass)
            src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT)
            des = os.path.join(_TRAVIS_DIR, _PROCESS_SCRIPT)
            copy_file_to_container(container_id, src, des)
            if args.copy_m2 or args.copy_m2_aggressive:
                _run_cache_script_and_build(container_id, fail_or_pass, repo, option, True)
                mkdir('{}/{}'.format(_TMP_DIR, image_tag))
                if args.copy_m2_aggressive:
                    cont_path = '/home/travis/.m2/'
                    cont_tar = '/tmp/m2-{}-{}.tar'.format(fail_or_pass, option)
                    host_path = '{}/{}/m2-{}-{}.tar'.format(_TMP_DIR, image_tag, fail_or_pass, option)
                    _, stdout, stderr, ok = run_command(
                        'docker exec {} tar -cvf {} {}'.format(container_id, cont_tar, cont_path))
                    if ok:
                        log.info('Tar cvf succeed')
                    else:
                        print_error('Tar cvf failed', stdout, stderr)
                        remove_container(container_id)
                        continue
                    copy_file_out_of_container(container_id, cont_tar, host_path)
                    container2_id = create_container(args.task_name, image_tag, docker_image_tag, option,
                                                     fail_or_pass, 'check')
                    copy_file_to_container(container2_id, src, des)
                    copy_file_to_container(container2_id, host_path, cont_tar)
                    _, stdout, stderr, ok = run_command(
                        'docker exec {} tar --directory / -xkvf {}'.format(container_id, cont_tar))
                    if ok:
                        log.info('Tar xkvf succeed')
                    else:
                        print_error('Tar xkvf failed', stdout, stderr)
                        remove_container(container_id)
                        remove_container(container2_id)
                        continue
                else:
                    cont_path = '/home/travis/.m2/{}/'.format(fail_or_pass)
                    host_path = '{}/{}/m2-{}-{}/'.format(_TMP_DIR, image_tag, fail_or_pass, option)
                    copy_file_out_of_container(container_id, cont_path, host_path)
                    container2_id = create_container(args.task_name, image_tag, docker_image_tag, option,
                                                     fail_or_pass, 'check')
                    copy_file_to_container(container2_id, src, des)
                    copy_file_to_container(container2_id, host_path, cont_path)
                change_container_file_owner(container2_id, cont_path, 'travis', 'travis')
                _run_cache_script_and_build(container2_id, fail_or_pass, repo, 'none', False)
                copy_log_out_of_container(image_tag, container2_id, fail_or_pass, _TMP_DIR, _TRAVIS_DIR, _SANDBOX_DIR)
                remove_container(container2_id)
            else:
                _run_cache_script_and_build(container_id, fail_or_pass, repo, option, False)
                copy_log_out_of_container(image_tag, container_id, fail_or_pass, _TMP_DIR, _TRAVIS_DIR, _SANDBOX_DIR)
            remove_container(container_id)
        if _verify_cache(image_tag, repo, option, original_size, output_file, args):
            break


def _pack_artifact(image_tag, repo, option, args):
    docker_image_tag = '{}:{}'.format(DOCKER_HUB_REPO, image_tag)
    container_id = create_container(args.task_name, image_tag, docker_image_tag, option)
    src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT)
    des = os.path.join(_TRAVIS_DIR, _PROCESS_SCRIPT)
    copy_file_to_container(container_id, src, des)

    if args.copy_m2:
        for fail_or_pass in ['failed', 'passed']:
            cont_path = '/home/travis/.m2/{}/'.format(fail_or_pass)
            host_path = '{}/{}/m2-{}-{}/'.format(_TMP_DIR, image_tag, fail_or_pass, option)
            copy_file_to_container(container_id, host_path, cont_path)
            change_container_file_owner(container_id, cont_path, 'travis', 'travis')
        option = 'none'
    elif args.copy_m2_aggressive:
        for fail_or_pass in ['failed', 'passed']:
            cont_tar = '/tmp/m2-{}-{}.tar'.format(fail_or_pass, option)
            host_path = '{}/{}/m2-{}-{}.tar'.format(_TMP_DIR, image_tag, fail_or_pass, option)
            copy_file_to_container(container_id, host_path, cont_tar)
            _, stdout, stderr, ok = run_command(
                'docker exec {} tar --directory / -xkvf {}'.format(container_id, cont_tar))
            if ok:
                log.info('Tar xkvf succeed')
            else:
                print_error('Tar xkvf failed', stdout, stderr)
                remove_container(container_id)
                return None
        option = 'none'

    for fail_or_pass in ['failed', 'passed']:
        _run_cache_script_and_build(container_id, fail_or_pass, repo, option, True)

    patch_script_path = '{}/{}'.format(_TRAVIS_DIR, _PROCESS_SCRIPT)
    remove_file_from_container(container_id, patch_script_path)
    log.info('Successfully packaged image {}'.format(image_tag))
    return container_id


def _verify_cache(image_tag, repo, option, original_size, output_file, args):
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
            container_id = _pack_artifact(image_tag, repo, option, args)
            if container_id:
                latest_layer_size = pack_push_container(container_id, image_tag)
                remove_container(container_id)
                status = 'succeed'
            else:
                status = 'failed'

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
    image_tags_file, output_file, args = validate_input(argv, 'maven')

    t_start = time.time()
    PatchArtifactRunner(image_tags_file, _COPY_DIR, output_file, args, workers=4).run()
    t_end = time.time()
    log.info('Running patch took {}s'.format(t_end - t_start))


if __name__ == '__main__':
    sys.exit(main())
