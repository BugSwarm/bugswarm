import sys

# Define credentials below

# DockerHub
# The DockerHub repository that will hold Docker Images pushed by the BugSwarm
# Reproducer. For example `bugswarm/images`.
DOCKER_HUB_REPO = ''
# The DockerHub repository that will hold Docker Images pushed by the
# CacheDependencies step in the BugSwarm Reproducer. Leave this blank to skip
# caching dependencies. For example `bugswarm/cached-images`.
DOCKER_HUB_CACHED_REPO = ''
# This is the username credential being used by the DockerHub API to access the
# DOCKER_HUB_REPO. For example `bugswarm`.
DOCKER_HUB_USERNAME = ''
# This is the password credential being used by the DockerHub API to access the
# DOCKER_HUB_REPO. You can also use an access token instead.
DOCKER_HUB_PASSWORD = ''

# Docker Private Registry
DOCKER_REGISTRY_REPO = ''
DOCKER_REGISTRY_USERNAME = ''
DOCKER_REGISTRY_PASSWORD = ''

# GitHub
# A GitHub Access Token to perform Git Operations over HTTPS via the Git API.
# (used for Mining projects)
# These GitHub tokens are hard-coded and can be used for token switching to
# minimize the time spent waiting for our GitHub quota to reset.
GITHUB_TOKENS = []

# Travis
# A Travis CI Access Token to send authenticated requests to Travis CI.
# (used for gathering builds)
# Travis CI Access Token for sending authenticated requests up to 2000/min
# Unauthenticated requests are up to 500/min
TRAVIS_TOKENS = []

# Database authentication tokens
# The token of a user's account used to access MongoDB.
# ('testDBPassword' if using Docker image of Mongo)
DATABASE_PIPELINE_TOKEN = ''

# This hostname is used to integrate the API usage with your local database.
# It should be `<LOCAL-IPADDRESS>:5000`, for example `127.0.0.1:5000`.
COMMON_HOSTNAME = ''

# Check validity of credentials

# DockerHub check
if not DOCKER_HUB_REPO:
    print('[ERROR]: DOCKER_HUB_REPO has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
    sys.exit(1)
if not DOCKER_HUB_CACHED_REPO:
    print('[WARNING]: DOCKER_HUB_CACHED_REPO has not been found. Skip caching dependencies in reproducing stage.')
if not DOCKER_HUB_USERNAME:
    print('[ERROR]: DOCKER_HUB_USERNAME has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
    sys.exit(1)
if not DOCKER_HUB_PASSWORD:
    print('[ERROR]: DOCKER_HUB_PASSWORD has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
    sys.exit(1)

# Docker Private Registry check
if not DOCKER_REGISTRY_REPO:
    print('[WARNING]: DOCKER_REGISTRY_REPO has not been found. Skip pushing to docker private registry '
          'in reproducing stage')
if not DOCKER_REGISTRY_USERNAME:
    print('[WARNING]: DOCKER_REGISTRY_USERNAME has not been found. Skip pushing to docker private registry '
          'in reproducing stage')
if not DOCKER_REGISTRY_PASSWORD:
    print('[WARNING]: DOCKER_REGISTRY_PASSWORD has not been found. Skip pushing to docker private registry '
          'in reproducing stage')

# GitHub check
if not GITHUB_TOKENS:
    print('[ERROR]: GITHUB_TOKENS has not been set. Please input your credentials under common/credentials.py and '
          'rerun the bugswarm/provision.sh script.')
    sys.exit(1)

# Database authentication tokens check
if not DATABASE_PIPELINE_TOKEN:
    print('[ERROR]: DATABASE_PIPELINE_TOKEN has not been found. Please input your credentials under '
          'common/credentials.py and rerun the bugswarm/provision.sh script.')
    sys.exit(1)
