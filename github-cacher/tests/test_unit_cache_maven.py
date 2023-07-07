import filecmp
import logging
import os
import shutil
import sys
import tarfile
import threading
import unittest
from os.path import dirname, join
from unittest.mock import patch

import docker

import bugswarm.common.artifact_processing.utils as procutils

DATA_DIR = join(dirname(__file__), 'data')
SANDBOX_DIR = join(dirname(__file__), 'test-sandbox')
FROM_HOST = join(dirname(__file__), '..', 'from_host')
IN_CONTAINER = os.environ.get('IN_CONTAINER', False)
procutils.HOST_SANDBOX = SANDBOX_DIR

sys.path.append('..')
import CacheMaven  # noqa: E402


class ArgsStub:
    def __init__(self):
        self.task_name = 'testing'
        self.no_copy_actions_toolcache = False


class ArtifactRunnerShim:
    def __init__(self):
        self.repr_metadata = {}
        self.copy_dir = ''
        self.output_file = '/dev/null'
        self.output_lock = threading.Lock()
        self.args = ArgsStub()
        self.tmp_dir = SANDBOX_DIR


class PatchArtifactNoDockerTask(CacheMaven.PatchArtifactMavenTask):
    """Class that runs Docker commands on the host if the IN_CONTAINER
    environment variable is set. If IN_CONTAINER is not set, then this
    passes all commands to `super().run_command()` like normal.
    - `docker run` --> no-op, but stdout has a fake container ID
    - `docker cp` --> shutil.copy or shutil.copytree
    - `docker exec` --> run the command on the host
    - other --> no-op.
    """

    def run_command(self, command, *args, **kwargs):
        if not IN_CONTAINER or not command.startswith('docker'):
            return super().run_command(command, *args, **kwargs)

        if command.startswith('docker run'):
            return None, 'dummy-container-id', '', True
        if command.startswith('docker exec'):
            new_command = ' '.join(command.split()[3:])
            return super().run_command(new_command, *args, **kwargs)
        if command.startswith('docker cp'):
            src, dest = command.split()[2:4]
            src = src.rpartition(':')[2]
            dest = dest.rpartition(':')[2]
            if os.path.isfile(src):
                shutil.copy(src, dest)
            else:
                shutil.copytree(src, dest, dirs_exist_ok=True)
        return None, '', '', True


def no_op(*args, **kwargs):
    pass


class CacheMavenUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(SANDBOX_DIR, ignore_errors=True)
        os.makedirs(SANDBOX_DIR)
        shutil.copytree(FROM_HOST, join(SANDBOX_DIR, 'from_host'))
        logging.disable(logging.CRITICAL)

    def assertFilesEqual(self, first, second):
        self.assertTrue(filecmp.cmp(first, second), f'Files "{first}" and "{second}" are not identical')

    @patch('CacheMaven.PatchArtifactMavenTask.copy_file_out_of_container', new=no_op)
    @patch('CacheMaven.PatchArtifactMavenTask.copy_file_to_container', new=no_op)
    @patch('CacheMaven.PatchArtifactMavenTask.run_command', new=no_op)
    def test_add_untar_to_build_script(self):
        subdir = 'add-untar-to-build-script'
        os.makedirs(join(SANDBOX_DIR, subdir), exist_ok=True)
        shutil.copy2(join(DATA_DIR, subdir, 'run_failed_old.sh'), join(SANDBOX_DIR, subdir))

        task = CacheMaven.PatchArtifactMavenTask(ArtifactRunnerShim(), subdir)
        task._add_untar_to_build_script('container-id', 'failed',
                                        ['/home/github/home-m2-failed.tgz', '/home/github/home-gradle-failed.tgz'])
        self.assertFilesEqual(join(SANDBOX_DIR, subdir, 'run_failed_new.sh'),
                              join(DATA_DIR, subdir, 'run_failed_new.sh'))

    def test_cache_toolcache(self):
        subdir = 'cache-toolcache'
        os.makedirs(join(SANDBOX_DIR, subdir), exist_ok=True)

        # Docker setup
        if IN_CONTAINER:
            os.makedirs('/home/github')
            container_id = 'dummy-container-id'
        else:
            client = docker.from_env()
            container = client.containers.run('bugswarm/githubactionsjobrunners:ubuntu-20.04',
                                              tty=True, detach=True, remove=True)
            container.exec_run(['mkdir', '-p', '/home/github'])
            container_id = container.id

        try:
            # Run pre-cache
            task = PatchArtifactNoDockerTask(ArtifactRunnerShim(), subdir)
            task.pre_cache_toolcache(container_id)

            # Simulate a run by adding a directory to the toolcache
            if IN_CONTAINER:
                with tarfile.open(join(DATA_DIR, subdir, 'dummy-toolcache-tool.tar')) as f:
                    f.extractall('/opt/hostedtoolcache')
            else:
                with open(join(DATA_DIR, subdir, 'dummy-toolcache-tool.tar'), 'rb') as f:
                    tar_data = f.read()
                container.put_archive('/opt/hostedtoolcache', tar_data)

            # Run cache
            task.cache_toolcache(container_id, 'failed')
        finally:
            if not IN_CONTAINER:
                container.stop()

        # Compare with expected value
        with tarfile.open(join(SANDBOX_DIR, subdir, 'actions-toolcache-failed.tgz')) as f:
            cached_filenames = set(f.getnames())
        expected_filenames = {'opt/hostedtoolcache/NewToolInCache/Version1/file1',
                              'opt/hostedtoolcache/NewToolInCache/Version1/file2',
                              'opt/hostedtoolcache/NewToolInCache/Version1/file3',
                              'opt/hostedtoolcache/NewToolInCache/Version2/file1',
                              'opt/hostedtoolcache/NewToolInCache/Version2/file2',
                              'opt/hostedtoolcache/NewToolInCache/Version2/file3'}
        self.assertEqual(cached_filenames, expected_filenames)
