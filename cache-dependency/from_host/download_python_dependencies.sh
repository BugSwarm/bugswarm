#!/bin/bash
# Show all commands
set -o xtrace
DEP_FOLDER=$HOME/pypkg
mkdir -p $DEP_FOLDER

function find_and_download_deps () {
    # Print current environment
    which python
    
    # Find pip version
    PIP_MAJOR_VERSION=$(pip -V | cut -d' ' -f 2 | cut -d. -f 1)
    DISABLE_CHECK='--disable-pip-version-check'
    if [[ $PIP_MAJOR_VERSION -lt 8 ]]; then
        DISABLE_CHECK=''
    fi

    # Get a list of all the currently installed packages, only use lines with == to 
    # avoid including any extra lines from input and any local packages
    DEP_LIST_FILE=$HOME/download_dependencies.txt
    FREEZE_OPTIONS=''
    if [[ $PIP_MAJOR_VERSION -gt 7 ]]; then
        FREEZE_OPTIONS='--all'
    fi
    pip freeze $FREEZE_OPTIONS $DISABLE_CHECK | grep "==" > $DEP_LIST_FILE
    cat $DEP_LIST_FILE

    # Download the dependencies 
    PIP_DOWNLOAD="pip download -d $DEP_FOLDER $DISABLE_CHECK"
    if [[ $PIP_MAJOR_VERSION -lt 8 ]]; then
        PIP_DOWNLOAD="pip install --download=$DEP_FOLDER $DISABLE_CHECK"
    fi
    xargs -n 1 -a $DEP_LIST_FILE $PIP_DOWNLOAD
}

# Find and activate the virtualenv used in the script
VENV=$HOME/$(grep -o -m 1 "/virtualenv/.*/bin/activate" $(which run_$1.sh))
shift 1
source $VENV
find_and_download_deps
deactivate

# Download any dependencies that may be hiding in conda environments
for dir in $HOME/miniconda*/ ; do
    source ${dir}bin/activate
    find_and_download_deps

    # Get a list of the environments, only get the names and do not include currently selected one
    CONDA_ENVS=$(conda info --env | grep $HOME | grep -v '\*' | cut -d' ' -f1)
    for env in $CONDA_ENVS ; do
        source activate $env
        find_and_download_deps
    done
done

# Copy any downloaded python virtualenv
for pyenv_download in $HOME/build/py*.tar.bz2 ; do
    cp "$pyenv_download" "$DEP_FOLDER"
done


# Tar up requirements to allow them to be easily copied out
REQUIREMENTS_TAR=$HOME/requirements.tar
tar -cvf $REQUIREMENTS_TAR -C $DEP_FOLDER .
