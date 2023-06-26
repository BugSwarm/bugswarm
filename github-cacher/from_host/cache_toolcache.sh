#!/bin/bash
set -xeo pipefail

target_directory="$1"
output_file="$2"
old_output_file="$3"
output_tar="$4"

# Output all normal files and empty directories, along with their modification times.
# I don't just output all files & directories because tar will happily archive the same file/folder
# multiple times, making the archive much bigger than necessary.
# Assumes the setup-* scripts only add or touch files and directories (no removal, no symlinks).
if [ -d "$target_directory" ]; then
  find "$target_directory" \( -type f -o -type d -empty \) -printf "%p %T@\n" | sort > "$output_file"
else
  # If the target dir doesn't exist (e.g. in non-github base images), just create an empty file
  touch "$output_file"
fi

# If we don't have an output tar, exit.
[ -z "$output_tar"] && exit 0

comm -13 "$old_output_file" "$output_file" | # Get files added/modified after the build script ran
  sed 's/ \S*$//' |                          # Remove timestamps
  tar --no-wildcards --verbatim-files-from --files-from - -czf "$output_tar"
