#!/bin/bash

cd /home/github

if [[ $1 == "run" ]]; then
    # During the test phase
    # CachePython will run this script twice, in a different container

    # create new directory `cacher`
    mkdir cacher
    # put cache servers into this directory
    mv /home/github/python_cache_server.py cacher
    mv /home/github/apt_cache_server.py cacher
    # create a virtual environment for cache server
    cd cacher
    python -m venv env
    source env/bin/activate
    # install requests and flask
    pip install requests flask
    # create storage dirs for our cache servers
    mkdir cache apt-cache

    echo "Starting cache server" > pypi-cacher.log
    nohup python -u ./python_cache_server.py &>> pypi-cacher.log &
    nohup python -u ./apt_cache_server.py &>> apt-cacher.log &

    # Add config to apt conf dir
    cat <<EOF | sudo tee /etc/apt/apt.conf.d/bugswarm-proxy > /dev/null
Acquire::http::proxy "http://127.0.0.1:56766/";
EOF

    echo "poetry() {
        command /usr/bin/poetry.sh \"\$@\"
    }
    " >> /etc/reproducer-environment
else
    # During the pack phase
    # CachePython will run this script twice, in the same container

    # Note: We cannot re-use the env directory from the test phase becasue we have to move the
    # cacher directory from /home/github/cacher to /home/github/build/<failed_or_pass>/cacher

    # create the `cacher` directory in /home/github/build/<failed_or_pass>/
    mkdir build/$1/cacher
    cd build/$1/cacher
    # create a virtual environment for cache server
    python -m venv env
    source env/bin/activate
    # install requests and flask
    pip install requests flask
    deactivate
fi
