import os
import shutil
import sys
import unittest
from unittest.mock import patch

import requests_mock
from bugswarm.common import filter_reasons as reasons
from bugswarm.common import log
from bugswarm.common.json import read_json

sys.path.append('..')

import pair_filter.filters as filters  # noqa: E402
from pair_filter.constants import FILTERED_REASON_KEY, PARSED_IMAGE_TAG_KEY  # noqa: E402

TESTDIR = os.path.dirname(__file__)
DATADIR = os.path.join(TESTDIR, 'pairfinder-output')
LOGSDIR = os.path.join(TESTDIR, 'test-original-logs')


def setUpModule():
    log.config_logging('CRITICAL')
    os.makedirs(LOGSDIR, exist_ok=True)


def tearDownModule():
    shutil.rmtree(LOGSDIR)


def set_attribute_defaults(buildpairs):
    for bp in buildpairs:
        for jp in bp['jobpairs']:
            jp[FILTERED_REASON_KEY] = None
            jobs = [jp['failed_job'], jp['passed_job']]
            for j in jobs:
                j[PARSED_IMAGE_TAG_KEY] = None


class TestFilters(unittest.TestCase):

    def test_filter_no_sha(self):
        pairs = read_json(os.path.join(DATADIR, 'alibaba-fastjson2.json'))

        # Every other should have failed, passed, or both have no head sha
        for i, pair in enumerate(pairs):
            if i % 6 in [0, 4]:
                pair['failed_build']['head_sha'] = ''
            if i % 6 in [2, 4]:
                pair['passed_build']['head_sha'] = ''

        num_filtered = filters.filter_no_sha(pairs)
        self.assertEqual(num_filtered, 18)

        for i, pair in enumerate(pairs):
            if i % 2 == 0:
                for jp in pair['jobpairs']:
                    self.assertEqual(jp[FILTERED_REASON_KEY], reasons.NO_HEAD_SHA)
            else:
                for jp in pair['jobpairs']:
                    self.assertIsNone(jp[FILTERED_REASON_KEY])

    def test_filter_unavailable(self):
        pairs = read_json(os.path.join(DATADIR, 'alibaba-fastjson2.json'))

        for i, pair in enumerate(pairs):
            if i % 8 < 4:
                build = pair['failed_build']
            else:
                build = pair['passed_build']

            build['resettable'] = i % 2 == 0
            build['github_archived'] = i % 4 < 2

        num_filtered = filters.filter_unavailable(pairs)
        self.assertEqual(num_filtered, 9)

        for i, pair in enumerate(pairs):
            if i % 4 == 3:
                for jp in pair['jobpairs']:
                    self.assertEqual(jp[FILTERED_REASON_KEY], reasons.NOT_AVAILABLE)
            else:
                for jp in pair['jobpairs']:
                    self.assertIsNone(jp[FILTERED_REASON_KEY])

    def test_filter_same_commit(self):
        pairs = read_json(os.path.join(DATADIR, 'alibaba-fastjson2.json'))

        for pair in pairs[::2]:
            pair['failed_build']['head_sha'] = pair['passed_build']['head_sha']

        num_filtered = filters.filter_same_commit(pairs)
        self.assertEqual(num_filtered, 18)

        for i, pair in enumerate(pairs):
            if i % 2 == 0:
                for jp in pair['jobpairs']:
                    self.assertEqual(jp[FILTERED_REASON_KEY], reasons.SAME_COMMIT_PAIR)
            else:
                for jp in pair['jobpairs']:
                    self.assertIsNone(jp[FILTERED_REASON_KEY])

    @patch('pair_filter.utils.get_orig_log_path', lambda id: os.path.join(LOGSDIR, f'{id}-orig.log'))
    @requests_mock.Mocker()
    def test_filter_expired_logs(self, mock: requests_mock.Mocker):
        pairs = read_json(os.path.join(DATADIR, 'alibaba-fastjson2.json'))

        template_url = 'https://api.github.com/repos/alibaba/fastjson2/actions/jobs/{}/logs'

        for i, pair in enumerate(pairs):
            for jp in pair['jobpairs']:
                failed_id = jp['failed_job']['job_id']
                passed_id = jp['passed_job']['job_id']

                if i % 4 == 0:
                    mock.get(template_url.format(failed_id), status_code=410)
                    mock.get(template_url.format(passed_id), content=b'foo')
                elif i % 4 == 2:
                    mock.get(template_url.format(failed_id), content=b'foo')
                    mock.get(template_url.format(passed_id), status_code=410)
                else:
                    mock.get(template_url.format(failed_id), content=b'foo')
                    mock.get(template_url.format(passed_id), content=b'foo')

        num_filtered = filters.filter_expired_logs(pairs)
        self.assertEqual(num_filtered, 18)

        for i, pair in enumerate(pairs):
            if i % 2 == 0:
                for jp in pair['jobpairs']:
                    self.assertEqual(jp[FILTERED_REASON_KEY], reasons.NO_ORIGINAL_LOG)
            else:
                for jp in pair['jobpairs']:
                    self.assertIsNone(jp[FILTERED_REASON_KEY])

    @patch('pair_filter.utils.get_orig_log_path', lambda id: os.path.join(TESTDIR, f'logs/{id}-orig.log'))
    @patch('pair_filter.constants.DOCKERHUB_IMAGES_JSON', os.path.join(TESTDIR, '../dockerhub_images.json'))
    @patch('pair_filter.constants.TRAVIS_IMAGES_JSON', os.path.join(TESTDIR, '../travis_images.json'))
    def test_filter_non_exact_images(self):
        pairs = read_json(os.path.join(DATADIR, 'fake-output.json'))

        no_log, read_error, filtered_no_timestamp, filtered_non_exact = filters.filter_non_exact_images(pairs)

        jps = pairs[0]['jobpairs']

        # first: chosen by time
        self.assertEqual(jps[0]['failed_job'][PARSED_IMAGE_TAG_KEY],
                         'quay.io/travisci/travis-jvm:latest-2015-02-11_15-09-23')
        self.assertNotIn(PARSED_IMAGE_TAG_KEY, jps[0]['passed_job'])
        # second: filtered - no timestamp
        self.assertEqual(jps[0][FILTERED_REASON_KEY], reasons.NO_IMAGE_PROVISION_TIMESTAMP)

        # third: chosen by tag
        self.assertEqual(jps[1]['failed_job'][PARSED_IMAGE_TAG_KEY], 'travisci/ci-garnet:packer-1503972846')
        # fourth: chosen by sha
        self.assertEqual(jps[1]['passed_job'][PARSED_IMAGE_TAG_KEY], 'travisci/ci-sardonyx:packer-1558623664-f909ac5')
        self.assertEqual(jps[1][FILTERED_REASON_KEY], None)

        # fifth/sixth: inaccesible
        self.assertEqual(jps[2][FILTERED_REASON_KEY], reasons.INACCESSIBLE_IMAGE)

        self.assertEqual(no_log, 0)
        self.assertEqual(read_error, 0)
        self.assertEqual(filtered_no_timestamp, 1)
        self.assertEqual(filtered_non_exact, 1)

    def test_filter_unvavailable_github_runner(self):
        pairs = read_json(os.path.join(DATADIR, 'fake-test-runner-os.json'))
        num_filtered = filters.filter_unavailable_github_runner(pairs)

        for i, jp in enumerate(pairs[0]['jobpairs']):
            if i in [4, 6, 7, 9]:
                self.assertEqual(jp['filtered_reason'],
                                 reasons.UNAVAILABLE_RUNNER,
                                 'job {}'.format(jp['failed_job']['job_id']))
            else:
                self.assertIsNone(jp['filtered_reason'], 'job {}'.format(jp['failed_job']['job_id']))
        self.assertEqual(num_filtered, 4)

    def test_filter_unavailable_github_runner_2(self):
        """
        Handle cases like
        ```json
        {
            "runs-on": "${{ matrix.runner }}",
            "strategy": {"matrix": {"runner": ["self-hosted", "linux", "amd64"]}}
        }
        ```
        """
        pairs = read_json(os.path.join(DATADIR, 'camunda-zeebe.json'))
        num_filtered = filters.filter_unavailable_github_runner(pairs)

        self.assertEqual(pairs[0]['jobpairs'][0]['filtered_reason'], reasons.UNAVAILABLE_RUNNER)
        self.assertEqual(num_filtered, 1)

    def test_filter_unresettable_with_submodules(self):
        pairs = read_json(os.path.join(DATADIR, 'SkriptLang-Skript.json'))
        set_attribute_defaults(pairs)
        num_filtered = filters.filter_unresettable_with_submodules(pairs)

        self.assertTrue(all(jp['filtered_reason'] == reasons.UNRESETTABLE_WITH_SUBMODULES
                            for jp in pairs[0]['jobpairs']))
        self.assertTrue(all(jp['filtered_reason'] is None for jp in pairs[1]['jobpairs']))
        self.assertEqual(num_filtered, 1)

    def test_filter_cleartext_tokens(self):
        pairs = read_json(os.path.join(DATADIR, 'fake-test-cleartext-tokens.json'))
        set_attribute_defaults(pairs)
        num_filtered = filters.filter_unredacted_tokens(pairs)

        # Organize results in a way that's easier to iterate
        jobpairs = [jp for bp in pairs for jp in bp['jobpairs']]
        jobs = {job['job_id']: job
                for bp in pairs
                for build in (bp['failed_build'], bp['passed_build'])
                for job in build['jobs']}

        # Jobs and keys to test
        filtered_job_ids = {9564558775, 9415526453, 9597106472}
        filtered_keys = {'MY_TOKEN', 'MY_PASSWORD', 'some-passwd'}

        def check_redacted(job_id, dictionary, msg=None):
            for k, v in dictionary.items():
                if job_id in filtered_job_ids and k in filtered_keys:
                    self.assertEqual(v, '**REDACTED**', msg)
                else:
                    self.assertNotEqual(v, '**REDACTED**', msg)

        for jp in jobpairs:
            fail_message = 'failed job id {}'.format(jp['failed_job']['job_id'])
            job_id = jp['failed_job']['job_id']

            # Check filter reason
            if job_id in filtered_job_ids:
                self.assertEqual(jp['filtered_reason'], reasons.UNREDACTED_TOKEN, fail_message)
            else:
                self.assertIsNone(jp['filtered_reason'], fail_message)

            job_config = jobs[job_id]['config']
            check_redacted(job_id, job_config.get('env', {}), fail_message)
            for step in job_config['steps']:
                check_redacted(job_id, step.get('env', {}), fail_message)
                check_redacted(job_id, step.get('with', {}), fail_message)

        self.assertEqual(num_filtered, 3)

    def test_filter_unsupported_workflow(self):
        pairs = read_json(os.path.join(DATADIR, 'fake-test-unsupported-workflows.json'))
        set_attribute_defaults(pairs)
        num_filtered = filters.filter_unsupported_workflow(pairs)

        for i, jp in enumerate(pairs[0]['jobpairs']):
            if i == 0:
                self.assertEqual(jp['filtered_reason'],
                                 reasons.UNSUPPORTED_WORKFLOW,
                                 'job {}'.format(jp['failed_job']['job_id']))
            else:
                self.assertIsNone(jp['filtered_reason'], 'job {}'.format(jp['failed_job']['job_id']))
        self.assertEqual(num_filtered, 1)

    @patch('pair_filter.utils.get_orig_log_path', lambda id: f'/tmp/{id}-orig.log')
    def test_filter_logs_too_large(self):
        pairs = read_json(os.path.join(DATADIR, 'fake-output.json'))
        set_attribute_defaults(pairs)
        jobpairs = pairs[0]['jobpairs']

        too_large_size = 16 * 2 ** 20  # 16 MiB
        small_enough_size = 15 * 2 ** 20  # 15 MiB
        log_file_paths = []

        def write_dummy_log(job_id, size):
            filepath = f'/tmp/{job_id}-orig.log'
            contents = ' ' * size  # Fill the file with {size} space chars
            with open(filepath, 'w') as f:
                f.write(contents)
            log_file_paths.append(filepath)

        try:
            # 1. failed log too large
            write_dummy_log(jobpairs[0]['failed_job']['job_id'], too_large_size)
            write_dummy_log(jobpairs[0]['passed_job']['job_id'], small_enough_size)

            # 2. passed log too large
            write_dummy_log(jobpairs[1]['failed_job']['job_id'], small_enough_size)
            write_dummy_log(jobpairs[1]['passed_job']['job_id'], too_large_size)

            # 3. neither too large
            write_dummy_log(jobpairs[2]['failed_job']['job_id'], small_enough_size)
            write_dummy_log(jobpairs[2]['passed_job']['job_id'], small_enough_size)

            filters.filter_logs_too_large(pairs)

            self.assertEqual(jobpairs[0][FILTERED_REASON_KEY], reasons.ORIGINAL_LOG_TOO_LARGE)
            self.assertEqual(jobpairs[1][FILTERED_REASON_KEY], reasons.ORIGINAL_LOG_TOO_LARGE)
            self.assertIsNone(jobpairs[2][FILTERED_REASON_KEY])
        finally:
            for filepath in log_file_paths:
                try:
                    os.remove(filepath)
                except FileNotFoundError:
                    pass
