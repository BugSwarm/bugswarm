#!/bin/bash

if [[ $GITHUB_ACTION_REPOSITORY == "actions/setup-python" ]]; then
    if [[ -f "/tmp/pre-setup.txt" ]]; then
        # Create a direcotry to store all the initial site-packages
        mkdir -p /tmp/site-packages

        find /opt/hostedtoolcache -type d -name "site-packages" | sort > /tmp/post-setup.txt
        echo "Generated post-setup.txt" >> /tmp/toolcache.log
        cat /tmp/post-setup.txt

        comm /tmp/pre-setup.txt /tmp/post-setup.txt -13 > /tmp/diff-setup.txt
        echo "Generated diff-setup.txt" >> /tmp/toolcache.log
        cat /tmp/diff-setup.txt

        while read line; do
            # Generate a unique folder name
            site_packages_id=0
            if [[ ! -z "$(ls -A /tmp/site-packages)" ]]; then
                site_packages_id=$(find /tmp/site-packages/* -maxdepth 0 -type d | wc -l)
            fi

            echo "Copy $line -> /tmp/site-packages/$site_packages_id" >> /tmp/toolcache.log

            cp -rp $line /tmp/site-packages/$site_packages_id
            echo $line >> /tmp/site-packages-list.txt
        done < /tmp/diff-setup.txt

        rm /tmp/pre-setup.txt /tmp/post-setup.txt /tmp/diff-setup.txt
    else
        find /opt/hostedtoolcache -type d -name "site-packages" | sort > /tmp/pre-setup.txt
        echo "Generated pre-setup.txt" >> /tmp/toolcache.log
        cat /tmp/pre-setup.txt
    fi
fi
