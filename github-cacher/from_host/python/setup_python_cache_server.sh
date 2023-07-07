#!/bin/bash

# create new directory `cacher`
# put cache server into this directory
# create a virtual environment for cache server
# install requests and flask
# create directory `cache` for our cache server

cd /home/github

if [[ $1 == "run" ]]; then
    mkdir cacher
    mv /home/github/python_cache_server.py cacher
    cd cacher
    python -m venv env
    source env/bin/activate
    pip install requests flask
    mkdir cache
    echo "Starting cache server" > output.log
    nohup python -u ./python_cache_server.py >> output.log &
else
    rm -rf cacher/output.log cacher/git-output.log cacher/wget-output.log
    

    if [[ $1 == "failed" ]]; then
        mv cacher build/failed
        cd build/failed/cacher
    elif [[ $1 == "passed" ]]; then
        mv cacher build/passed
        cd build/passed/cacher
    fi

    source env/bin/activate
    pip install requests flask
    deactivate
fi
