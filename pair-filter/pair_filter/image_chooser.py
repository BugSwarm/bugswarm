import os
import re

from abc import ABC
from abc import abstractmethod
from typing import Dict
from typing import Optional

from bugswarm.analyzer.utils import get_fold_lines
from bugswarm.analyzer.utils import get_instance_line


class BaseImageChooser(ABC):
    @abstractmethod
    def get_image_tag(self) -> Optional[str]:
        """
        Subclasses should return the image tag identifying the image in which the build was executed. Returns None if
        the image could not be determined.

        Overriding is required.
        :return: The image tag identifying the image in which the build was executed.
        """
        pass


class ExactImageChooserByTime(BaseImageChooser):
    """
    ExactImageChooserByTime tries to extract a datetime from the original log for the build then see if we have an image
    for that particular datetime and language the build is using.
    """

    def __init__(self, original_log_path: str, travis_images: Dict[str, Dict[str, str]], language: str):
        if not isinstance(original_log_path, str):
            raise TypeError
        if not original_log_path:
            raise ValueError
        if not isinstance(travis_images, dict):
            raise TypeError
        if not isinstance(language, str):
            raise TypeError
        if not language:
            raise ValueError

        self.travis_images = travis_images
        self.language = language
        self.original_log_path = original_log_path

    def get_image_tag(self) -> Optional[str]:
        """
        Extracts the datetime if it can be located in the log and then checks if travis_images contains the datetime.
        """
        return self._find_exact_image()

    def find_image_datetime_from_log(self) -> str:
        if not os.path.isfile(self.original_log_path):
            raise FileNotFoundError

        with open(self.original_log_path) as f:
            for l in f:
                if 'Build image provisioning date and time' in l:
                    # The actual timestamp is on the next line.
                    return next(f).strip()

    def _find_exact_image(self) -> Optional[str]:
        if self.language not in self.travis_images:
            return None

        language_specific_images = self.travis_images[self.language]
        image_datetime_str = self.find_image_datetime_from_log()
        for name, timestamp in language_specific_images.items():
            if timestamp == image_datetime_str:
                return name


class ExactImageChooserByTag(BaseImageChooser):
    """
    ExactImageChooserByTag attempts to selectively retrieve the image tag that is used by the build. It first parses the
    worker info fold and then searches for the line that contains the instance of the image. The image tag is extracted
    and checked for availability on Docker Hub.
    """

    def __init__(self, original_log_path: str):
        if not isinstance(original_log_path, str):
            raise TypeError
        if not original_log_path:
            raise ValueError

        self.original_log_path = original_log_path

    def get_image_tag(self) -> Optional[str]:
        if not os.path.isfile(self.original_log_path):
            raise FileNotFoundError

        worker_lines = get_fold_lines(self.original_log_path,
                                      'travis_fold:start:worker_info',
                                      'travis_fold:end:worker_info')
        if worker_lines is None:
            return None
        instance = get_instance_line(worker_lines)
        if instance is None:
            return None

        # Matches 'travisci/ci-garnet:packer-1512502276-986baf0' and 'travisci/ci-garnet:packer-1503972846'.
        # Does not match 'ca10841:travis:java' and 'travis-ci-garnet-trusty-1512502259-986baf0'.
        match_obj_tag = re.search(r'(travisci/[^:]+:(\S+))', instance)
        if match_obj_tag:
            return match_obj_tag.group(1)


class ExactImageChooserByCommitSHA(BaseImageChooser):
    def __init__(self, original_log_path: str, dockerhub_images: dict):
        if not isinstance(original_log_path, str):
            raise TypeError
        if not original_log_path:
            raise ValueError

        self.original_log_path = original_log_path
        self.dockerhub_images = dockerhub_images

    def get_image_tag(self) -> Optional[str]:
        if not os.path.isfile(self.original_log_path):
            raise FileNotFoundError

        worker_lines = get_fold_lines(self.original_log_path,
                                      'travis_fold:start:worker_info',
                                      'travis_fold:end:worker_info')
        if worker_lines is None:
            return None
        instance = get_instance_line(worker_lines)
        if instance is None:
            return None

        # Matches 'travis-ci-garnet-trusty-1512502259-986baf0' and 'travis-ci-sardonyx-xenial-1553530528-f909ac5'
        # Does not match 'travis-ci-garnet-trusty-1503972833'
        match_obj_tag = re.search(r'(travis-ci(-[a-z]+)+-[0-9]+-[0-9a-z]+)', instance)
        if not match_obj_tag:
            return None

        match_list = []
        instance_tag = match_obj_tag.group(1)
        instance_tag = instance_tag.split('-')
        repo_name = 'travisci/' + '-'.join(instance_tag[1:3])
        commit_sha = instance_tag[-1]
        pattern = 'packer-[0-9]+-{}'.format(commit_sha)
        images = self.dockerhub_images.get(repo_name, '')
        if not images:
            return None
        for image in images:
            match = re.search(pattern, image)
            if match is not None:
                match_list.append(match)
        if len(match_list) == 0:
            return None
        else:
            # images are in chronological order, the last one would be latest
            # travisci/ci-garnet:packer-epoch-commitSHA
            return '{}:{}'.format(repo_name, match_list[-1].string)
