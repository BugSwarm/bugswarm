import sys

# DockerHub
DOCKER_HUB_REPO = ''
DOCKER_HUB_USERNAME = ''
DOCKER_HUB_PASSWORD = ''
if not DOCKER_HUB_REPO:
    print('[ERROR]: DOCKER_HUB_REPO has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
if not DOCKER_HUB_USERNAME:
    print('[ERROR]: DOCKER_HUB_USERNAME has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
if not DOCKER_HUB_PASSWORD:
    print('[ERROR]: DOCKER_HUB_PASSWORD has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')

# GitHub
# These GitHub tokens are hard-coded and can be used for token switching to minimize the time spent waiting for our
# GitHub quota to reset.
GITHUB_TOKENS = []
if not GITHUB_TOKENS:
    print('[ERROR]: GITHUB_TOKENS has not been set. Please input your credentials under common/credentials.py and '
          'rerun the bugswarm/provision.sh script.')
    sys.exit(1)

# Authentication tokens for the database.
DATABASE_PIPELINE_TOKEN = ''
if not DATABASE_PIPELINE_TOKEN:
    print('[ERROR]: DATABASE_PIPELINE_TOKEN has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
    sys.exit(1)

COMMON_HOSTNAME = ''
