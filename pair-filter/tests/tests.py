import os
import sys
import unittest

from bugswarm.common.json import read_json

sys.path.append('../')
from pair_filter.constants import DOCKERHUB_IMAGES_JSON, TRAVIS_IMAGES_JSON  # noqa: E402
from pair_filter.image_chooser import (ExactImageChooserByCommitSHA, ExactImageChooserByTag,
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
