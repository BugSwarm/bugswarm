import os
import sys
import re
import logging
import subprocess
import argparse
import threading
import time
from pathlib import Path

from bugswarm.common.json import read_json
from bugswarm.analyzer.analyzer import Analyzer
from bugswarm.common import log
from bugswarm.common.artifact_processing.runners import ParallelArtifactRunner
from bugswarm.common.credentials import DOCKER_HUB_REPO, DOCKER_HUB_CACHED_REPO
from bugswarm.common import utils as bugswarmutils
import traceback

_HOME_DIR = str(Path.home())
_SANDBOX_DIR = '{}/bugswarm-sandbox'.format(_HOME_DIR)


class CachingScriptError(Exception):
    pass


class PatchArtifactRunner(ParallelArtifactRunner):
    def __init__(self, task_class: type, image_tags_file: str, copy_dir: str, output_file: str,
                 repr_metadata: dict, args: argparse.Namespace, workers: int = 1):
        """
        :param image_tags_file: Path to a file containing a newline-separated list of image tags.
        :param copy_dir: A directory to copy into the host-side sandbox before any artifacts are processed.
        :param output_file: File location for output CSV to be written to. Path is defined in validate_input.
        :param repr_metadata: Dictionary mapping build pair image_tag to relevant metadata for runs with the
        reproducer pipeline, empty if run outside the pipeline.
        :param command: A callable used to determine what command(s) to execute in each artifact container. `command` is
                        called once for each processed artifact. The only parameter is the image tag of the artifact
                        about to be processed.
        :param workers: The same as for the superclass initializer.
        """
        with open(image_tags_file) as f:
            image_tags = list(map(str.strip, f.readlines()))
        super().__init__(image_tags, workers)
        self.repr_metadata = repr_metadata
        self.task_class = task_class
        self.copy_dir = copy_dir
        self.output_file = output_file
        self.output_lock = threading.Lock()
        self.args = args
        self.tmp_dir = '{}/{}'.format(_SANDBOX_DIR, args.task_name)

    def pre_run(self):
        create_work_space(self.tmp_dir, _SANDBOX_DIR)

    def process_artifact(self, image_tag: str):
        task = self.task_class(self, image_tag)
        task.run()

    def post_run(self):
        pass


class PatchArtifactTask:
    def __init__(self, runner: PatchArtifactRunner, image_tag: str):
        self.image_tag = image_tag
        self.repr_metadata = runner.repr_metadata
        self.containers = []
        self.copy_dir = runner.copy_dir
        self.output_file = runner.output_file
        self.output_lock = runner.output_lock
        self.args = runner.args
        self.tmp_dir = runner.tmp_dir
        self.workdir = '{}/{}'.format(self.tmp_dir, self.image_tag)
        # Create workdir
        mkdir(self.workdir)
        # Config logger for this image_tag
        log_level = logging.INFO
        self.logger = logging.getLogger('PatchArtifactTask.{}.{}'.format(self.args.task_name, self.image_tag))
        self.logger.handlers = []  # Remove previously added handlers before adding new ones.
        # Config file logger
        formatter = logging.Formatter('[%(levelname)8s] --- %(message)s')
        file_handler = logging.FileHandler('{}/{}'.format(self.workdir, 'log.txt'), mode='w')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        self.logger.addHandler(file_handler)
        # Config stdout logger
        formatter2 = logging.Formatter('[%%(levelname)8s] --- %s: %%(message)s' % self.image_tag)
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setFormatter(formatter2)
        stream_handler.setLevel(log_level)
        self.logger.addHandler(stream_handler)
        self.logger.setLevel(log_level)

    def run(self):
        t_start = time.time()
        try:
            self.logger.info('Start running patch for {}'.format(self.image_tag))
            self.logger.info('Command line arguments: {}'.format(repr(vars(self.args))))
            self.cache_artifact_dependency()
        except BaseException as e:
            traceback.print_exc()
            self.logger.error('An error occurred in {}.'.format(self.image_tag))
            self.logger.exception(e)
            self.write_output(self.image_tag, '{}, -, -'.format(repr(e)))
        finally:
            self.logger.info('Start cleaning up.')
            if not self.args.keep_containers:
                for container_id in self.containers:
                    self.run_command('docker rm -f {}'.format(container_id), fail_on_error=False)
            if not self.args.keep_tmp_images:
                self.run_command('docker image rm {}:{}'.format(self.args.task_name, self.image_tag),
                                 fail_on_error=False)
            if not self.args.keep_tars:
                self.run_command('rm -f {}/*.tar'.format(self.workdir), fail_on_error=False)
        t_end = time.time()
        self.logger.info('Running patch for {} took {}s'.format(self.image_tag, t_end - t_start))

    def cache_artifact_dependency(self):
        raise NotImplementedError

    def run_command(self, command, print_on_error=True, fail_on_error=True, loglevel=logging.ERROR, timeout=None):
        self.logger.info('run_command: {}'.format(command))
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=True)
        try:
            stdout, stderr = process.communicate(None, timeout)
            stdout = stdout.decode('utf-8').strip()
            stderr = stderr.decode('utf-8').strip()
            ok = process.returncode == 0
        except subprocess.TimeoutExpired:
            stdout = ''
            stderr = 'subprocess.TimeoutExpired'
            ok = False
            pass
        if not ok:
            if print_on_error:
                self.logger.log(loglevel, '{} returns {}'.format(repr(command), process.returncode))
                if stdout:
                    self.logger.log(loglevel, 'stdout:\n{}'.format(stdout))
                if stderr:
                    self.logger.log(loglevel, 'stderr:\n{}'.format(stderr))
            if fail_on_error:
                # Most errors come from this function
                raise CachingScriptError(command)
        return process, stdout, stderr, ok

    def print_error(self, msg, stdout=None, stderr=None, loglevel=logging.ERROR):
        self.logger.log(loglevel, msg)
        if stdout:
            self.logger.log(loglevel, 'stdout:\n{}'.format(stdout))
        if stderr:
            self.logger.log(loglevel, 'stderr:\n{}'.format(stderr))

    def create_container(self, docker_image_tag, *tags, docker_args=''):
        """
        Create a container
        Containers of a image_tag will be tracked automatically and removed in the end
        docker_args is a string to provide extra arguments to docker (e.g. set up volumes)
        """
        container_name = '-'.join((self.args.task_name, self.image_tag, *tags))
        _, stdout, stderr, ok = self.run_command(
            'docker run -t -d {} --name {} {} /bin/bash'.format(docker_args, container_name, docker_image_tag))
        container_id = stdout.strip()
        self.containers.append(container_id)
        return container_id

    def remove_container(self, container_id):
        """Remove a container"""
        if self.args.keep_containers:
            return
        try:
            self.containers.remove(container_id)
            _, stdout, stderr, ok = self.run_command('docker rm -f {}'.format(container_id), fail_on_error=False)
        except ValueError:
            pass

    def write_output(self, image_tag, content):
        with self.output_lock:
            with open(self.output_file, 'a+') as file:
                file.write('{}, {}\n'.format(image_tag, content))

    def get_last_layer_size(self, image_id):
        _, stdout, stderr, ok = self.run_command('docker image history %s --format "{{.Size}}"' % image_id)
        return stdout.split('\n')[0]

    def tag_and_push_cached_image(self, image_tag, image_id):
        """Tag image from temporary repo to final repo and push"""
        self.run_command('docker tag {} {}:{}'.format(image_id, self.args.dst_repo, image_tag))
        if not self.args.no_push:
            _, _, stderr, ok = self.run_command('docker push {}:{}'.format(self.args.dst_repo, image_tag))

    def pack_push_container(self, container_id, image_tag):
        latest_layer_size = -1
        self.run_command('docker commit {} {}:{}'.format(container_id, self.args.dst_repo, image_tag))

        _, stdout, stderr, ok = self.run_command('docker image history %s:%s --format "{{.Size}}"'
                                                 % (self.args.dst_repo, image_tag),
                                                 fail_on_error=False)

        if ok:
            latest_layer_size = stdout.split('\n')[0]

        if not self.args.no_push:
            _, _, stderr, ok = self.run_command('docker push {}:{}'.format(self.args.dst_repo, image_tag),
                                                fail_on_error=False)

        return latest_layer_size

    def run_build_script(self, container_id, f_or_p, log_path, orig_log_path, orig_job_id, build_system):
        """Run build script and compare logs. Return whether log compare is passed"""
        _, stdout, stderr, ok = self.run_command(
            'docker exec {} bash /usr/local/bin/run_{}.sh 2>&1'.format(container_id, f_or_p), fail_on_error=False,
            print_on_error=False, timeout=7200)
        if stderr == 'subprocess.TimeoutExpired':
            with open(log_path, 'w') as f:
                f.write(stderr)
                self.logger.error('subprocess.TimeoutExpired when running build script for {}.'.format(f_or_p))
                return False
        with open(log_path, 'w') as f:
            f.write(stdout)
        analyzer = Analyzer()
        if build_system is None:
            # For Python
            bs = None
        else:
            # For Java
            bs = build_system.lower()
            assert bs in ['maven', 'gradle', 'ant']
        compare_result = analyzer.compare_single_log(log_path, orig_log_path, orig_job_id, bs)
        with open(log_path + '.cmp', 'w') as f:
            print(repr(compare_result), file=f)
        if not compare_result[0]:
            self.logger.error('Build script log comparision failed.')
            self.logger.error('Reproduced log: {}'.format(log_path))
            self.logger.error('Original log: {}'.format(orig_log_path))
        return compare_result[0]

    def docker_commit(self, image_tag, container_id):
        new_repo = '{}:{}'.format(self.args.task_name.lower(), image_tag)
        _, stdout, stderr, ok = self.run_command('docker commit {} {}'.format(container_id, new_repo))
        image_id = re.fullmatch('sha256:([0-9a-f]{64})', stdout.strip()).groups()
        return new_repo, image_id

    def pull_image(self, docker_image_tag):
        _, stdout, stderr, ok = self.run_command('docker pull {}'.format(docker_image_tag))
        _, stdout, stderr, ok = self.run_command('docker images %s --format "{{.Size}}"' % (docker_image_tag))
        original_size = stdout
        return original_size

    def mkdir(self, dir_path):
        _, stdout, stderr, ok = self.run_command('mkdir -p -m 777 {}'.format(dir_path))

    def copy_file_to_container(self, container_id, src, des):
        _, stdout, stderr, ok = self.run_command('docker cp {} {}:{}'.format(src, container_id, des))

    def copy_file_out_of_container(self, container_id, src, des):
        _, stdout, stderr, ok = self.run_command('docker cp {}:{} {}'.format(container_id, src, des))

    def remove_file_from_container(self, container_id, file_path):
        _, stdout, stderr, ok = self.run_command(
            'docker exec {} sudo rm -rf {}'.format(container_id, file_path))


def validate_input(argv, artifact_type):
    assert artifact_type in ['maven', 'python']
    parser = argparse.ArgumentParser()
    parser.add_argument('image_tags_file',
                        help='Path to a file containing a newline-separated list of image tags to process.')
    parser.add_argument('task_name',
                        help='Name of current task. Results will be put in ./output/<task-name>.csv.')
    parser.add_argument('--task_json', default='',
                        help='Location of task JSON from ReproducedResultsAnalyzer')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel tasks to run.')
    parser.add_argument('--no-push', action='store_true', help='Do not push the artifact to Docker Hub.')
    parser.add_argument('--src-repo', default=DOCKER_HUB_REPO, help='Which repo to pull non-cached images from.')
    parser.add_argument('--dst-repo', default=DOCKER_HUB_CACHED_REPO, help='Which repo to push cached images to.')
    parser.add_argument('--keep-tmp-images', action='store_true',
                        help='Keep temporary container images in the temporary repository.')
    parser.add_argument('--keep-containers', action='store_true',
                        help='Keep containers in order to debug.')
    parser.add_argument('--keep-tars', action='store_true',
                        help='Keep tar files in order to debug.')
    if artifact_type == 'maven':
        parser.add_argument('--no-copy-home-m2', action='store_true',
                            help='Do not copy /home/travis/.m2/ directory.')
        parser.add_argument('--no-copy-home-gradle', action='store_true',
                            help='Do not copy /home/travis/.gradle/ directory.')
        parser.add_argument('--no-copy-home-ivy2', action='store_true',
                            help='Do not copy /home/travis/.ivy2/ directory.')
        parser.add_argument('--no-copy-proj-gradle', action='store_true',
                            help='Do not copy /home/travis/build/*/*/*/.gradle/ directory.')
        parser.add_argument('--no-remove-maven-repositories', action='store_true',
                            help='Do not remove `_remote.repositories` and `_maven.repositories`.')
        parser.add_argument('--ignore-cache-error', action='store_true',
                            help='Ignore error when running build script to download cached files.')
        parser.add_argument('--no-strict-offline-test', action='store_true',
                            help='Do not apply strict offline mode when testing.')
        parser.add_argument('--separate-passed-failed', action='store_true',
                            help='Separate passed and failed cached files (will increase artifact size).')
    if artifact_type == 'python':
        parser.add_argument('--parse-original-log', action='store_true',
                            help='Parse the artifacts original log for list of packages to download')
        parser.add_argument('--parse-new-log', action='store_true',
                            help='Run build script on the artifact and parse this log for list of packages '
                            'to download')

    args = parser.parse_args(argv[1:])

    image_tags_file = args.image_tags_file
    task_name = args.task_name
    task_json_path = args.task_json

    if not os.path.isfile(image_tags_file):
        log.error('{} is not a file or does not exist. Exiting.'.format(image_tags_file))
        parser.print_usage()
        exit(1)

    if task_json_path:
        if not os.path.isfile(task_json_path):
            log.error('{} is not a file or does not exist. Exiting.'.format(task_json_path))
            parser.print_usage()
            exit(1)

    if not re.fullmatch(r'[a-zA-Z0-9\-\_]+', task_name):
        log.error('Invalid task_name: {}. Exiting.'.format(repr(task_name)))
        parser.print_usage()
        exit(1)

    output_file = 'output/{}.csv'.format(task_name)
    if not os.path.isdir('output'):
        os.mkdir('output')

    return image_tags_file, output_file, args


def _run_command(command, print_on_error=True, fail_on_error=True):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    if not ok:
        if print_on_error:
            log.error('{} returns {}'.format(repr(command), process.returncode))
            if stdout:
                log.error('stdout:\n{}'.format(stdout))
            if stderr:
                log.error('stderr:\n{}'.format(stderr))
        if fail_on_error:
            # Most errors come from this function
            raise CachingScriptError(command)
    return process, stdout, stderr, ok


def mkdir(dir_path):
    _, stdout, stderr, ok = _run_command('mkdir -p -m 777 {}'.format(dir_path))


def create_work_space(tmp_dir, sandbox_dir):
    mkdir(tmp_dir)
    _, stdout, stderr, ok = _run_command('cp -r from_host/ {}'.format(sandbox_dir))


def get_repr_metadata_dict(task_json_path, repr_metadata_dict):
    buildpairs = read_json(task_json_path)
    for bp in buildpairs:
        for jp in bp['jobpairs']:
            image_tag = bugswarmutils.get_image_tag(bp['repo'], jp['failed_job']['job_id'])
            failed_job = jp['failed_job']
            passed_job = jp['passed_job']
            jobs = [failed_job, passed_job]
            tag_metadata = dict()
            tag_metadata['repo'] = bp['repo']
            build_system = failed_job['orig_result']['tr_build_system'] if failed_job['orig_result'] else ''
            tag_metadata['build_system'] = build_system
            tag_metadata['failed_job'] = {'job_id': jobs[0]['job_id']}
            tag_metadata['passed_job'] = {'job_id': jobs[1]['job_id']}
            repr_metadata_dict[image_tag] = tag_metadata
    return repr_metadata_dict
