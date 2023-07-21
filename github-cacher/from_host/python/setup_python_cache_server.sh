#!/bin/bash

cd /home/github

if [[ $1 == "run" ]]; then
    # During the test phase
    # CachePython will run this script twice, in a different container

    # create new directory `cacher`
    # put cache server into this directory
    # create a virtual environment for cache server
    # install requests and flask
    # create directory `cache` for our cache server

    mkdir cacher
    mv /home/github/python_cache_server.py cacher
    cd cacher
    python -m venv env
    source env/bin/activate
    pip install requests flask
    mkdir cache
    echo "Starting cache server" > output.log
    nohup python -u ./python_cache_server.py >> output.log &

    echo "poetry() {
        command /usr/bin/poetry.sh \"\$@\"
    }
    " >> /etc/reproducer-environment
else
    # During the pack phase
    # CachePython will run this script twice, in the same container

    # create the `cacher` directory in /home/github/build/<failed_or_pass>/
    # create a virtual environment for cache server
    # install requests and flask

    # Note: We cannot re-use the env directory from the test phase becasue we have to move the
    # cacher directory from /home/github/cacher to /home/github/build/<failed_or_pass>/cacher

    mkdir build/$1/cacher
    cd build/$1/cacher
    python -m venv env
    source env/bin/activate
    pip install requests flask
    deactivate
fi
