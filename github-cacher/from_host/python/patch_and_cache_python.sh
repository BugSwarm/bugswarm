#!/bin/bash

# $1: Job ID
# $2: failed or passed

if [[ -z "$2" ]]; then
    exit 1
fi

cd /home/github/build/$2/cacher
source env/bin/activate
echo "Starting cache server for $2" > output.log
nohup python -u ./python_cache_server.py >> output.log &
deactivate
echo "PIP_INDEX_URL=http://localhost:56765/simple/" >> /etc/reproducer-environment
echo "PIP_DEFAULT_TIMEOUT=120" >> /etc/reproducer-environment

if [[ -f /usr/bin/git.py ]]; then
    sudo mv /usr/bin/git /usr/bin/git_original
    sudo mv /usr/bin/git.py /usr/bin/git
fi

# sudo mv /usr/bin/curl /usr/bin/curl_original
# sudo mv /usr/bin/curl.py /usr/bin/curl

if [[ -f /usr/bin/wget.py ]]; then
    sudo mv /usr/bin/wget /usr/bin/wget_original
    sudo mv /usr/bin/wget.py /usr/bin/wget
fi

echo "BUGSWARM_CACHER_PATH=/home/github/build/$2/cacher" >> /etc/reproducer-environment
echo "BUGSWARM_GIT_CACHER=stop" >> /etc/reproducer-environment
