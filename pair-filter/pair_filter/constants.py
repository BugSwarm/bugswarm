TRAVIS_IMAGES_JSON = 'travis_images.json'

FILTERED_REASON_KEY = 'filtered_reason'
IS_FILTERED_KEY = 'is_filtered'
PARSED_IMAGE_TAG_KEY = 'heuristically_parsed_image_tag'

# These paths are output by PairFinder, but have no entry in the database schema. They should be ignored when uploading
# BPs to the database.
IGNORED_BUILDPAIR_KEYS = ['failed_build.has_submodules', 'passed_build.has_submodules']

# Please update .gitignore to reflect any changes to these directory constants.
ORIGINAL_LOG_DIR = 'original-logs'
OUTPUT_FILE_DIR = 'output-json'
DOCKERHUB_REPO_NAME = ['travisci/ci-sardonyx', 'travisci/ci-garnet']
DOCKERHUB_IMAGES_JSON = 'dockerhub_images.json'
