#!/bin/bash

# $1: Job ID
# $2: failed or passed

if [[ -z "$2" ]]; then
    exit 1
fi

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

if [[ -f /home/github/cacher-$2.tgz ]]; then
    tar -xzf /home/github/cacher-$2.tgz -C /
    rm -rf /home/github/cacher/output.log /home/github/cacher/git-output.log /home/github/cacher/wget-output.log
    mv /home/github/cacher /home/github/build/$2/cacher
fi

echo "BUGSWARM_CACHER_PATH=/home/github/build/$2/cacher" >> /etc/reproducer-environment
echo "BUGSWARM_GIT_CACHER=stop" >> /etc/reproducer-environment
