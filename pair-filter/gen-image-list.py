import json
import os
from os import path
import sys

from bugswarm.common import log

from pair_filter import utils
from pair_filter.constants import DOCKERHUB_REPO_NAME, DOCKERHUB_IMAGES_JSON


def generate_image_file():
    image_list = dict()
    for repo_name in DOCKERHUB_REPO_NAME:
        image_list[repo_name] = utils._registry_tags_list(repo_name)
    with open(DOCKERHUB_IMAGES_JSON, 'w+') as file:
        json.dump(image_list, file)


def main():
    if not path.exists(os.path.expanduser('~/.docker/config.json')):
        log.info('docker login file not found run `docker login` before filtering pairs')
        exit(0)
    generate_image_file()


if __name__ == '__main__':
    sys.exit(main())
