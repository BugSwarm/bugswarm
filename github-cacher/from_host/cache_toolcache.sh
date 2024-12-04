#!/bin/bash
set -xeo pipefail

target_directory="$1"
output_file="$2"
old_output_file="$3"
output_tar="$4"

if [[ ! -z "$output_tar" ]]; then
  # Having output_tar means it is the second run
  # If we have site-packages-list, then we have to restore site-packages back to their original location
  if [[ -f "/tmp/site-packages-list.txt" ]]; then
    # directories in site-packages start from 0
    site_packages_id=0
    while read line; do
      echo "Checking $line vs /tmp/site-packages/$site_packages_id" >> /tmp/toolcache.log
      # Only move site-packages back to their original location if the last modified date changed
      if [[ "$(stat -c %Y $line)" != "$(stat -c %Y /tmp/site-packages/$site_packages_id)" ]]; then
        echo "Restore /tmp/site-packages/$site_packages_id -> $line" >> /tmp/toolcache.log
        rm -rf $line
        mv /tmp/site-packages/$site_packages_id $line
      fi
      site_packages_id=$((site_packages_id + 1))
    done < /tmp/site-packages-list.txt
  fi
elif [[ -d "$target_directory" ]]; then
  # This is the first run, save a copy of all the site-packages directories
  mkdir -p /tmp/site-packages

  while read line; do
      # Generate a unique folder name
      site_packages_id=0
      if [[ ! -z "$(ls -A /tmp/site-packages)" ]]; then
        # if /tmp/site-packages is not empty
        site_packages_id=$(find /tmp/site-packages/* -maxdepth 0 -type d | wc -l)
      fi
      echo "Copy $line -> /tmp/site-packages/$site_packages_id" >> /tmp/toolcache.log
      cp -rp $line /tmp/site-packages/$site_packages_id
      echo $line >> /tmp/site-packages-list.txt
  done <<< "$(find /opt/hostedtoolcache -type d -name "site-packages")"
fi

# Output all normal files and empty directories, along with their modification times.
# I don't just output all files & directories because tar will happily archive the same file/folder
# multiple times, making the archive much bigger than necessary.
# Assumes the setup-* scripts only add or touch files and directories (no removal, no symlinks).
if [ -d "$target_directory" ]; then
  find "$target_directory" \( -type f -o -type l -o -type d -empty \) -printf "%p %T@\n" | sort > "$output_file"
else
  # If the target dir doesn't exist (e.g. in non-github base images), just create an empty file
  touch "$output_file"
fi

# If we don't have an output tar, exit.
[ -z "$output_tar" ] && exit 0

comm -13 "$old_output_file" "$output_file" | # Get files added/modified after the build script ran
  sed 's/ \S*$//' |                          # Remove timestamps
  tar --no-wildcards --verbatim-files-from --files-from - -czf "$output_tar"
