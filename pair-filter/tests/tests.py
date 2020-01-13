import unittest
import json
import sys

from bugswarm.common.json import read_json

sys.path.append("../")
from pair_filter.image_chooser import ExactImageChooserByCommitSHA  # noqa: E402
from pair_filter.constants import DOCKERHUB_IMAGES_JSON  # noqa: E402


class Test(unittest.TestCase):
    def test_match_object_1(self):
        log = "566084454-orig.log"
        file_path = "logs/" + log
        dockerhub_images = read_json(DOCKERHUB_IMAGES_JSON)
        chooser = ExactImageChooserByCommitSHA(file_path, dockerhub_images)
        image = chooser.get_image_tag()
        assert image == 'travisci/ci-sardonyx:packer-1558623664-f909ac5'

    def test_match_object_2(self):
        log = "520562883-orig.log"
        file_path = "logs/" + log
        dockerhub_images = read_json(DOCKERHUB_IMAGES_JSON)
        chooser = ExactImageChooserByCommitSHA(file_path, dockerhub_images)
        image = chooser.get_image_tag()
        assert image == 'travisci/ci-sardonyx:packer-1558623664-f909ac5'

    def test_match_object_3(self):
        log = "100252761-orig.log"
        file_path = "logs/" + log
        dockerhub_images = read_json(DOCKERHUB_IMAGES_JSON)
        chooser = ExactImageChooserByCommitSHA(file_path, dockerhub_images)
        image = chooser.get_image_tag()
        assert image is None

    def test_match_object_4(self):
        log = "309746090-orig.log"
        file_path = "logs/" + log
        dockerhub_images = read_json(DOCKERHUB_IMAGES_JSON)
        chooser = ExactImageChooserByCommitSHA(file_path, dockerhub_images)
        image = chooser.get_image_tag()
        assert image == 'travisci/ci-garnet:packer-1503972846'

    def test_match_object_5(self):
        log = "438981744-orig.log"
        file_path = "logs/" + log
        dockerhub_images = read_json(DOCKERHUB_IMAGES_JSON)
        chooser = ExactImageChooserByCommitSHA(file_path, dockerhub_images)
        image = chooser.get_image_tag()
        assert image is None
