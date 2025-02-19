#!/bin/bash

# $1: Job ID
# $2: failed or passed

if [[ -z "$2" ]]; then
    exit 1
fi

# Untar caches
if [[ -f /actions-toolcache-$2.tgz ]]; then
    tar -xzf /actions-toolcache-$2.tgz -C /
    sudo rm -rf /actions-toolcache-$2.tgz
fi

if [[ -f /node-modules-$2.tgz ]]; then
    tar -xzf /node-modules-$2.tgz -C /
    sudo rm -rf /node-modules-$2.tgz
fi

if [[ -f /cacher-$2.tgz ]]; then
    tar -xzf /cacher-$2.tgz -C /
    sudo rm -rf /cacher-$2.tgz
fi

if [[ -f /apt-$2.tgz ]]; then
    tar -xzf /apt-$2.tgz -C /
    sudo rm -f /apt-$2.tgz
fi

GHDIR=/home/github
if [[ -d $GHDIR/cacher ]]; then
    rm -f $GHDIR/cacher/*.log
    # Use cp instead of mv so we won't override the env directory
    cp -rn $GHDIR/cacher/* $GHDIR/build/$2/cacher/
    rm -rf $GHDIR/cacher
fi

# Start cache servers
cd /home/github/build/$2/cacher
source env/bin/activate
echo "Starting cache server for $2" > pypi-cacher.log
nohup python -u ./python_cache_server.py &>> pypi-cacher.log &
nohup python -u ./apt_cache_server.py &>> apt-cacher.log &
deactivate

# Add config to apt conf dir
cat <<EOF | sudo tee /etc/apt/apt.conf.d/bugswarm-proxy > /dev/null
Acquire::http::proxy "http://127.0.0.1:56766/";
EOF

# Set up wrapper scripts
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

# Set up environment
echo "PIP_INDEX_URL=http://localhost:56765/simple/" >> /etc/reproducer-environment
echo "PIP_DEFAULT_TIMEOUT=120" >> /etc/reproducer-environment
echo "UV_DEFAULT_INDEX=http://localhost:56765/simple/" >> /etc/reproducer-environment
echo "BUGSWARM_CACHER_PATH=/home/github/build/$2/cacher" >> /etc/reproducer-environment
echo "BUGSWARM_GIT_CACHER=stop" >> /etc/reproducer-environment

echo "poetry() {
        command /usr/bin/poetry.sh \"\$@\"
}
" >> /etc/reproducer-environment
