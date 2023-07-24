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

# Remove cache server
pid=$(ps -f | grep "python_cache_server.py" | grep -v "grep" | awk '{print $2}')
if [[ ! -z "$pid" ]]; then
    kill -9 $pid
fi

# Clean environment variables
echo -n "" > /etc/reproducer-environment
