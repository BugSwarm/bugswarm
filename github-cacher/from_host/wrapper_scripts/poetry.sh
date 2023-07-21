#!/bin/bash

set -o allexport
source /etc/reproducer-environment
set +o allexport

if [[ ! $POETRY_ADDED_REPOSITORY ]]; then
    version=$(command poetry --version)
    regex="\(version ([0-9]+)\.([0-9]+)(.*)\)"

    if [[ "$version" =~ $regex ]]; then
        MAJOR=${BASH_REMATCH[1]}
        MINOR=${BASH_REMATCH[2]}
        if [[ $MAJOR > 1 ]] || [[ $MAJOR == 1 && $MINOR > 4 ]]; then
            # >=1.5, use --priority
            command poetry source add --priority=default cacher http://localhost:56765/simple/
        else
            # <1.5, use --default
            command poetry source add --default cacher http://localhost:56765/simple/
        fi
    else
        # Don't know which version, try both
        command poetry source add --priority=default cacher http://localhost:56765/simple/ || true
        command poetry source add --default cacher http://localhost:56765/simple/ || true
    fi
    echo "POETRY_ADDED_REPOSITORY=1" >> /etc/reproducer-environment
fi

command poetry "$@"
