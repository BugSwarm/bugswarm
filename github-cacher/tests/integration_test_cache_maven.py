import logging
import os
import shutil
import sys
import threading
import unittest
from multiprocessing.pool import ThreadPool
from os.path import dirname, join
from unittest.mock import patch

import docker
import docker.errors

from bugswarm.common.artifact_processing import utils as procutils

DATA_DIR = join(dirname(__file__), 'data')
SANDBOX_DIR = join(dirname(__file__), 'test-sandbox')
FROM_HOST = join(dirname(__file__), '..', 'from_host')
SOURCE_DOCKER_REPO = 'bugswarm/test-uncached-images'
DEST_DOCKER_REPO = 'bugswarm/test-cached-images'
procutils.HOST_SANDBOX = SANDBOX_DIR

sys.path.append('..')
import CacheMaven  # noqa: E402
import utils  # noqa: E402


def log_paths(cacher):
    return {
        'failed': join(DATA_DIR, 'integration-test', 'orig-logs', f'{cacher.job_id["failed"]}.log'),
        'passed': join(DATA_DIR, 'integration-test', 'orig-logs', f'{cacher.job_id["passed"]}.log'),
    }


def no_op(*args, **kwargs):
    pass


class ArtifactRunnerShim:
    def __init__(self, task_json_path):
        self.repr_metadata = utils.get_repr_metadata_dict(task_json_path, {})
        self.copy_dir = ''
        self.output_file = '/dev/null'
        self.output_lock = threading.Lock()
        _, _, self.args = utils.validate_input(
            [
                'CacheMaven.py',
                '--task_json', task_json_path,
                '--no-push',
                '--src-repo', SOURCE_DOCKER_REPO,
                '--dst-repo', DEST_DOCKER_REPO,
                '--disconnect-network-during-test',
                __file__,  # It doesn't matter what file it is, as long as it's a real file
                'integration-test-task',
            ],
            'maven'
        )
        self.tmp_dir = SANDBOX_DIR


class CacheMavenIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(SANDBOX_DIR, ignore_errors=True)
        os.makedirs(SANDBOX_DIR)
        shutil.copytree(FROM_HOST, join(SANDBOX_DIR, 'from_host'))
#       logging.disable(logging.CRITICAL)

    def run_subtest(self, test_args):
        image_tag, test_targets, runner = test_args
        print('Testing', image_tag)
        with self.subTest(msg=f'{image_tag} -- {", ".join(test_targets)}'):
            cacher = CacheMaven.PatchArtifactMavenTask(runner, image_tag)
            try:
                cacher.cache_artifact_dependency()
            except utils.CachingScriptError as e:
                self.fail(e.args[0])
            finally:
                client = docker.from_env()
                for container_id in cacher.containers:
                    container = client.containers.get(container_id)
                    container.stop()
                    container.remove()
                client.images.remove(f'{cacher.args.task_name}:{image_tag}')
                client.api.close()

    @patch('CacheMaven.PatchArtifactMavenTask._get_orig_logs', new=log_paths)
    @patch('CacheMaven.PatchArtifactMavenTask.tag_and_push_cached_image', new=no_op)
    def test_integration(self):
        task_json_path = join(DATA_DIR, 'integration-test', 'reproducer-result.json')
        runner = ArtifactRunnerShim(task_json_path)

        tests = [
            # (image tag, what it tests)
            ('alibaba-transmittable-thread-local-8267344544', ['maven', 'toolcache']),
            ('alibaba-transmittable-thread-local-8267344708', ['maven', 'toolcache']),
            ('Grasscutters-Grasscutter-7801445827',           ['gradle']),
            ('Grasscutters-Grasscutter-7825239642',           ['gradle']),
            ('marcwrobel-jbanking-8761138559',                ['maven']),
            ('marcwrobel-jbanking-8761138892',                ['maven', 'toolcache']),
            ('Netflix-spectator-8295325184',                  ['gradle', 'toolcache']),
            ('QuickCarpet-QuickCarpet-7830074046',            ['gradle']),
        ]

        with ThreadPool(processes=4) as pool:
            args = [(*test, runner) for test in tests]
            pool.map(self.run_subtest, args)
        pool.join()
