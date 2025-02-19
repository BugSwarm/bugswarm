#!/bin/bash

# Move git and wget back after running the build script
if [[ -f /usr/bin/git_original ]]; then
    sudo mv /usr/bin/git /usr/bin/git.py
    sudo mv /usr/bin/git_original /usr/bin/git
fi

if [[ -f /usr/bin/wget_original ]]; then
    sudo mv /usr/bin/wget /usr/bin/wget.py
    sudo mv /usr/bin/wget_original /usr/bin/wget
fi

# Remove apt config that sets up our proxy
if [[ -f /etc/apt/apt.conf.d/bugswarm-proxy ]]; then
    sudo rm -f /etc/apt/apt.conf.d/bugswarm-proxy
fi

# Terminate cache servers
pkill -f '\bpython_cache_server\.py\b' || true
pkill -f '\bapt_cache_server\.py\b' || true

# Clean environment variables
echo -n "" > /etc/reproducer-environment
