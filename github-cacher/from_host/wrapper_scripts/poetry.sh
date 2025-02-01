#!/bin/bash

set -o allexport
source /etc/reproducer-environment
set +o allexport

if [[ ! $POETRY_ADDED_REPOSITORY ]]; then
    version=$(command poetry --version)
    regex='\(version ([0-9]+)\.([0-9]+)(.*)\)'

    if [[ "$version" =~ $regex ]]; then
        MAJOR=${BASH_REMATCH[1]}
        MINOR=${BASH_REMATCH[2]}
        if [[ $MAJOR -gt 1 ]]; then
            # >=2.0, use --priorty=primary (since "default" is no longer supported)
            command poetry source add --priority=primary cacher http://localhost:56765/simple/
        elif [[ $MAJOR -eq 1 && $MINOR -gt 4 ]]; then
            # >=1.5, use --priority=default
            command poetry source add --priority=default cacher http://localhost:56765/simple/
        else
            # <1.5, use --default
            command poetry source add --default cacher http://localhost:56765/simple/
        fi
    else
        # Don't know which version, try all 3
        command poetry source add --priority=primary cacher http://localhost:56765/simple/ ||
            command poetry source add --priority=default cacher http://localhost:56765/simple/ ||
            command poetry source add --default cacher http://localhost:56765/simple/
    fi

    # If poetry.lock exists, regenerate it so poetry doesn't complain
    if [[ -f poetry.lock ]]; then
        if [[ $MAJOR -gt 1 ]]; then
            # Change in poetry v2.0 removed the --no-update flag, and made plain `poetry lock`
            # behave how `poetry lock --no-update` used to
            command poetry lock
        else
            command poetry lock --no-update
        fi
    fi
    echo "POETRY_ADDED_REPOSITORY=1" >> /etc/reproducer-environment
fi

command poetry "$@"
