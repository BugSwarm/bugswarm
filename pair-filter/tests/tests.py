import os
import sys
import unittest
from unittest.mock import patch

from bugswarm.common.json import read_json

sys.path.append('../')
from pair_filter import utils  # noqa: E402
from pair_filter.constants import DOCKERHUB_IMAGES_JSON, TRAVIS_IMAGES_JSON  # noqa: E402
from pair_filter.image_chooser import (ExactImageChooserByCommitSHA, ExactImageChooserByTag,  # noqa: E402
                                       ExactImageChooserByTime)  # noqa: E402


_TESTDIR = os.path.dirname(__file__)
_DOCKERHUB_IMAGES = read_json(os.path.join(_TESTDIR, DOCKERHUB_IMAGES_JSON))
_TRAVIS_IMAGES = read_json(os.path.join(_TESTDIR, '..', TRAVIS_IMAGES_JSON))


class Test(unittest.TestCase):

    def test_match_object_by_commit_sha_1(self):
        log = '566084454-orig.log'
        file_path = os.path.join(_TESTDIR, 'logs', log)
        chooser = ExactImageChooserByCommitSHA(file_path, _DOCKERHUB_IMAGES)
        image = chooser.get_image_tag()
        assert image == 'travisci/ci-sardonyx:packer-1558623664-f909ac5'

    def test_match_object_by_commit_sha_2(self):
        log = '520562883-orig.log'
        file_path = os.path.join(_TESTDIR, 'logs', log)
        chooser = ExactImageChooserByCommitSHA(file_path, _DOCKERHUB_IMAGES)
        image = chooser.get_image_tag()
        assert image == 'travisci/ci-sardonyx:packer-1558623664-f909ac5'

    def test_match_object_by_commit_sha_3(self):
        log = '100252761-orig.log'
        file_path = os.path.join(_TESTDIR, 'logs', log)
        chooser = ExactImageChooserByCommitSHA(file_path, _DOCKERHUB_IMAGES)
        image = chooser.get_image_tag()
        assert image is None

    def test_match_object_by_commit_sha_4(self):
        log = '438981744-orig.log'
        file_path = os.path.join(_TESTDIR, 'logs', log)
        chooser = ExactImageChooserByCommitSHA(file_path, _DOCKERHUB_IMAGES)
        image = chooser.get_image_tag()
        assert image is None

    def test_match_object_by_tag_1(self):
        log = '309746090-orig.log'
        file_path = os.path.join(_TESTDIR, 'logs', log)
        chooser = ExactImageChooserByTag(file_path)
        image = chooser.get_image_tag()
        assert image == 'travisci/ci-garnet:packer-1503972846'

    def test_match_object_by_time_1(self):
        log = '122972925-orig.log'
        file_path = os.path.join(_TESTDIR, 'logs', log)
        language = 'node_js'
        chooser = ExactImageChooserByTime(file_path, _TRAVIS_IMAGES, language)
        image = chooser.get_image_tag()
        assert image == 'quay.io/travisci/travis-node-js:latest-2015-04-28_13-54-26'


class TestUtils(unittest.TestCase):
    @patch('pair_filter.utils.get_orig_log_path', lambda id: os.path.join(_TESTDIR, f'logs/{id}-orig.log'))
    def test_get_pr_data_1(self):
        pr_num, base_sha, head_sha, merge_sha = utils.get_github_actions_pr_data(31343776564)
        self.assertEqual(pr_num, 2182)
        self.assertEqual(base_sha, '419791695c1cb0006a923b69092be0c61caa9f82')
        self.assertEqual(head_sha, '265c7ed23859e4df234924f401e40470c79ce190')
        self.assertEqual(merge_sha, '663f05ca0c78eb8a67266d6c8df3840bea16d7c3')

    @patch('pair_filter.utils.get_orig_log_path', lambda id: os.path.join(_TESTDIR, f'logs/{id}-orig.log'))
    def test_get_pr_data_2(self):
        pr_num, base_sha, head_sha, merge_sha = utils.get_github_actions_pr_data(30160126651)
        self.assertEqual(pr_num, 378)
        self.assertEqual(base_sha, '2fc0dd03aa8eb7d2f348490a11b70db04b437ddb')
        self.assertEqual(head_sha, '9b72f23b1b14b45bd8ccb3f1889ef20c1227c65a')
        self.assertEqual(merge_sha, '29375ef141ef1aa540994dfc1b4025c0715108d2')

    @patch('pair_filter.utils.get_orig_log_path', lambda id: os.path.join(_TESTDIR, f'logs/{id}-orig.log'))
    def test_get_pr_data_3(self):
        tup = utils.get_github_actions_pr_data(30817092298)
        self.assertEqual(tup, (None, None, None, None))
