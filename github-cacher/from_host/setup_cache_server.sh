#!/bin/bash

# Set up the apt cache server for the caching stage.
# CacheMaven will tar the `cacher-env` and `cacher` folders after running the
# build script.

cd /home/github

# create a virtual environment for cache server
python -m venv cacher-env
source cacher-env/bin/activate
# install requests and flask
pip install requests flask

# create new directories for cacher
mkdir cacher cacher/apt-cache
# put cache server into this directory
mv /home/github/apt_cache_server.py cacher

# Start cache server
cd cacher
nohup python -u ./apt_cache_server.py &>> apt-cacher.log &

# Add config to apt conf dir
cat <<EOF | sudo tee /etc/apt/apt.conf.d/bugswarm-proxy > /dev/null
Acquire::http::proxy "http://127.0.0.1:56766/";
EOF
