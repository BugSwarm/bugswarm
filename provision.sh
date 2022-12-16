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

USAGE='Usage: bash provision.sh [github-credential]'

# Extract command line arguments.
# At this time, the script accepts one optional argument: a GitHub credential in the form '<username>:<token>'.
GITHUB_CREDENTIAL=$1

# Hack to make the script ask for sudo password before printing any steps.
sudo printf ''

# Cache Git credentials for convenience.
git config --global credential.helper "cache --timeout=86400"

print_green 'Provisioning the environment...'

print_green 'Update the apt package index'
sudo apt-get --assume-yes update
exit_if_failed 'Updating the apt package index failed.'

print_green 'Install git'
sudo apt-get --assume-yes install git
exit_if_failed 'Installing git failed.'

# Install pip3. This must be done before using pip3 to install the BugSwarm components.
print_green 'Install pip3'
sudo apt-get --assume-yes install python3-pip
exit_if_failed 'Installing pip3 failed.'

# Preapre to clone BugSwarm components. Perform this step as early as possible so the user waits the minimal time for
# the git credential prompt to appear.
mkdir -p ~/bugswarm
# Tell git to use the credential memory cache.
git config --global credential.helper cache
git config --global credential.helper 'cache --timeout=86400'

# Install the components.
print_green "Install BugSwarm components"
pip3 install --upgrade --force-reinstall . --user
exit_if_failed 'Installing BugSwarm components failed.'

# We need curl to install rvm and software-properties-common to install rvm
print_green 'Install curl'
sudo apt-get --assume-yes install curl
exit_if_failed 'Installing curl failed.'

print_green 'Install software-properties-common'
sudo apt-get --assume-yes install software-properties-common
exit_if_failed 'Installing software-properties-common failed.'

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
sudo usermod -aG rvm $(whoami)
exit_if_failed 'Adding user to rvm group failed.'

print_green 'Install Ruby 2.5.8'
rvm install ruby-2.5.8
exit_if_failed 'Installing Ruby 2.5.8 failed.'

print_green 'Install system packages'
sudo apt-get --assume-yes install libffi-dev gcc make
exit_if_failed 'Installing system packages failed.'

# Install Docker.
print_green 'Install Docker'
sudo apt-get --assume-yes install apt-transport-https ca-certificates curl software-properties-common
exit_if_failed 'Installing prerequisites for docker failed.'
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
exit_if_failed 'Adding apt key for docker failed.'
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
exit_if_failed 'Adding apt repository for docker failed.'
sudo apt-get --assume-yes update
exit_if_failed 'Updating the apt package index failed.'
sudo apt-get --assume-yes install docker-ce
exit_if_failed 'Installing docker failed.'
sudo usermod -aG docker $(whoami)
exit_if_failed 'Adding user to docker group failed.'

# Install Travis.
print_green 'Install Travis'
# Pin public_suffix to 4.0.7, otherwise install travis will throw error because public_suffix requires Ruby version >= 2.6
gem install public_suffix -v 4.0.7 --no-document
gem install travis -v 1.8.8 --no-document
exit_if_failed 'Installing Travis failed.'

# Install travis-build.
print_green 'Install travis-build'
mkdir -p ~/.travis
if [ ! -d ~/.travis/travis-build ]; then
    git clone -q https://github.com/travis-ci/travis-build.git ~/.travis/travis-build
    exit_if_failed 'Cloning travis-build failed.'
fi

# Install puppeteer and its dependencies via npm, for web scraping functionality used by pair-classifier.
print_green 'Install npm'
curl -fsSL https://deb.nodesource.com/setup_19.x | sudo -E bash - &&\
sudo apt-get install -y nodejs
exit_if_failed 'Installing npm failed.'
print_green 'Install puppeteer'
npm i puppeteer
exit_if_failed 'Installing puppeteer failed.'
print_green 'Install puppeteer dependencies'
sudo apt update
sudo apt install -y libgconf-2-4 libatk1.0-0 libatk-bridge2.0-0 libgdk-pixbuf2.0-0 libgtk-3-0 libgbm-dev libnss3-dev libxss-dev
exit_if_failed 'Installing puppeteer dependencies failed.'

# Pin travis-build to a version that forces all maven repos to use https instead of http, which aids reproducibility.
# See https://github.com/travis-ci/travis-build/pull/1842
print_green 'Reset travis-build'
# commit sha of MASTER branch 8/14/2020
travis_build_sha=bf094c42837ceb4e02e68c79e1355b786a4d1333
cd ~/.travis/travis-build && git reset --hard ${travis_build_sha}
exit_if_failed 'Resetting travis-build failed.'
yes | gem install bundler
exit_if_failed 'Installing bundler failed.'
yes | bundle install --gemfile ~/.travis/travis-build/Gemfile
exit_if_failed 'Installing travis-build failed.'
bundler binstubs travis
exit_if_failed 'Installing binstubs for travis-build failed.'
cd ~
yes | travis
exit_if_failed 'Installing travis-build failed.'

# Done!
print_done_message 'Provisioning succeeded.'
