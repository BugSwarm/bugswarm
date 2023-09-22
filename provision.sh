#!/usr/bin/env bash
# Provision the environment for the BugSwarm reproducing pipeline.
# Tested on Ubuntu 18.04 & 20.04.

# Assumptions:
# 1. The user running this script has sudo privileges.
# 2. The host system uses apt-get to manage packages (e.g. Debian, Ubuntu)
# 3. sudo is installed in the host system.

# Get the absolute path to the directory containing this script. Source: https://stackoverflow.com/a/246128.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Include common functions and constants.
source "${SCRIPT_DIR}"/common.sh

# Function that prints a help message and exits.
print_usage() {
    echo "Usage: $0 [--github-actions-only]"
    echo "Options:"
    echo " --github-actions-only    Only install components necessary for mining and"
    echo "                          reproducing GitHub Actions artifacts."
    echo " -h, --help               Display this help and exit."

    exit "${1:-2}"
}

# Default settings, modified by command line arguments.
TRAVIS_INSTALL=1
GHA_INSTALL=1

# Get command line arguments.
OPTS=$(getopt -o 'h' -l 'github-actions-only,help' -n "$(basename "$0")" -- "$@")
[[ $? -ne 0 ]] && print_usage
eval set -- "$OPTS"

while true; do
    case "$1" in
        --github-actions-only ) unset TRAVIS_INSTALL ;;
        -h | --help           ) print_usage 0 ;;

        --) shift; break ;;
        *)  print_usage  ;;
    esac
    shift
done

# Set the packages to be installed by apt.
APT_PACKAGES=(
    git python3-pip curl software-properties-common
    # Required for docker-ce
    apt-transport-https ca-certificates
    # Required for nodesource installer
    gnupg
    # Required for puppeteer
    libgconf-2-4 libatk1.0-0 libatk-bridge2.0-0 libgdk-pixbuf2.0-0 libgtk-3-0 libgbm-dev libnss3-dev libxss-dev
)

# Hack to make the script ask for sudo password before printing any steps.
sudo printf ''

print_green 'Provisioning the environment...'

print_green 'Update the apt package index'
sudo apt-get --assume-yes update
exit_if_failed 'Updating the apt package index failed.'

print_green 'Install required apt packages'
sudo apt-get --assume-yes install "${APT_PACKAGES[@]}"
exit_if_failed 'Installing required apt packages failed.'

# Install the components.
print_green "Install BugSwarm components"
pip3 install --upgrade --force-reinstall .
exit_if_failed 'Installing BugSwarm components failed.'

# print_green 'Install system packages'
# sudo apt-get --assume-yes install libffi-dev gcc make
# exit_if_failed 'Installing system packages failed.'

# Install Docker.
print_green 'Install Docker'
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
exit_if_failed 'Adding apt key for docker failed.'
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
exit_if_failed 'Adding apt repository for docker failed.'
sudo apt-get --assume-yes update
exit_if_failed 'Updating the apt package index failed.'
sudo apt-get --assume-yes install docker-ce
exit_if_failed 'Installing docker failed.'
sudo usermod -aG docker "$(whoami)"
exit_if_failed 'Adding user to docker group failed.'

# Install puppeteer and its dependencies via npm, for web scraping functionality used by pair-classifier.
print_green 'Install NodeJS 20'
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
exit_if_failed 'Adding nodesource GPG key failed.'
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | sudo tee /etc/apt/sources.list.d/nodesource.list
exit_if_failed 'Adding apt repository for nodesource failed.'
sudo apt-get --assume-yes update
exit_if_failed 'Updating the apt package index failed.'
sudo apt-get --assume-yes install nodejs
exit_if_failed 'Installing NodeJS failed.'

print_green 'Install puppeteer'
npm install puppeteer@19.4.0
exit_if_failed 'Installing puppeteer failed.'

if [[ $TRAVIS_INSTALL ]]; then
    # Installation of RVM through their Ubuntu Doc: https://github.com/rvm/ubuntu_rvm
    print_green 'Install RVM'
    sudo apt-add-repository -y ppa:rael-gc/rvm
    exit_if_failed 'Adding apt repository for rvm failed.'
    sudo apt-get --assume-yes update
    exit_if_failed 'Updating the apt package index failed.'
    sudo apt-get --assume-yes install rvm
    exit_if_failed 'Installing rvm failed.'
    source /etc/profile.d/rvm.sh
    exit_if_failed 'Sourcing rvm.sh failed.'
    sudo usermod -aG rvm "$(whoami)"
    exit_if_failed 'Adding user to rvm group failed.'

    print_green 'Install Ruby 2.5.9'
    rvm fix-permissions system
    rvm fix-permissions "$(whoami)"
    rvm install ruby-2.5.9
    exit_if_failed 'Installing Ruby 2.5.9 failed.'
    rvm use ruby-2.5.9

    print_green 'Install Travis'
    # Pin public_suffix to 4.0.7, otherwise install travis will throw error because public_suffix requires Ruby version >= 2.6
    gem install public_suffix -v 4.0.7 --no-document
    gem install travis -v 1.8.8 --no-document
    exit_if_failed 'Installing Travis failed.'

    print_green 'Install travis-build'
    mkdir -p ~/.travis
    if [ ! -d ~/.travis/travis-build ]; then
        git clone -q https://github.com/travis-ci/travis-build.git ~/.travis/travis-build
        exit_if_failed 'Cloning travis-build failed.'
    fi

    # Pin travis-build to a version that forces all maven repos to use https instead of http, which aids reproducibility.
    # See https://github.com/travis-ci/travis-build/pull/1842
    print_green 'Reset travis-build'
    # commit sha of MASTER branch 8/14/2020
    travis_build_sha=bf094c42837ceb4e02e68c79e1355b786a4d1333
    cd ~/.travis/travis-build && git reset --hard ${travis_build_sha}
    exit_if_failed 'Resetting travis-build failed.'
    yes | gem install bundler -v 2.3.26
    exit_if_failed 'Installing bundler failed.'
    yes | bundle install --gemfile ~/.travis/travis-build/Gemfile
    exit_if_failed 'Installing travis-build failed.'
    bundler binstubs travis
    exit_if_failed 'Installing binstubs for travis-build failed.'
    cd ~
    yes | travis
    exit_if_failed 'Installing travis-build failed.'
fi

# Done!
print_done_message 'Provisioning succeeded.'
