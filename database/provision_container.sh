#!/bin/bash
# Note: this script assumes it's being run as root in the current directory.

set -eo pipefail

APT_PACKAGES=(
    apt-transport-https
    apt-utils
    build-essential
    ca-certificates
    curl
    git-core
    gnupg
    gnupg-agent
    locales
    locales-all
    lsb-release
    python3.8
    python3.8-dev
    python3-pip
    python3.8-venv
    software-properties-common
    sudo
    ufw
    vim
    wget
)

# Install base packages
apt-get update
apt-get install -y "${APT_PACKAGES[@]}"

# Set timezone
ln -snf /usr/share/zoneinfo/"$TZ" /etc/localtime
printf '%s\n' "$TZ" > /etc/timezone

# Add MongoDB key & sources
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc |
    gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ]" \
    "https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" \
    > /etc/apt/sources.list.d/mongodb-org-6.0.list

# Install MongoDB
apt-get update
apt-get install -y mongodb-org

# Set default Python version
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# Install DB and API requirements
pip3 install --upgrade pip wheel
pip3 install -r requirements.txt

# Set config permissions
chmod 000 database/config.py

# Create MongoDB data dir
mkdir -p /data/db
