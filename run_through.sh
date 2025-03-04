#!/usr/bin/env bash

# Get the absolute path to the directory containing this script. Source: https://stackoverflow.com/a/246128.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Include common functions and constants.
source "${SCRIPT_DIR}"/common.sh

# Ensure that Git won't prompt for input and hang the script.
export GIT_TERMINAL_PROMPT=0

USAGE='Usage: bash run_through.sh -r <repo-slug> [-t <threads>] [-c <component-directory>]'


# Extract command line arguments.
OPTS=$(getopt -o c:r:t: --long component-directory:,repo:,threads: -n 'run-through' -- "$@")
while true; do
    case "$1" in
      # Shift twice for options that take an argument.
      -c | --component-directory ) component_directory="$2"; shift; shift ;;
      -r | --repo                ) repo="$2";                shift; shift ;;
      -t | --threads             ) threads="$2";             shift; shift ;;
      -- ) shift; break ;;
      *  ) break ;;
    esac
done

# Perform checks and set defaults for command line arguments.

if [ -z "${repo}" ]; then
    echo ${USAGE}
    exit 1
fi

if [[ -z "${threads}" ]]; then
    echo 'The number of threads is not specified. Defaulting to 1 thread.'
    threads=1
fi

if [[ -z "${component_directory}" ]]; then
    component_directory="$SCRIPT_DIR"
fi

if [[ ${repo} != *"/"* ]]; then
    echo 'The repo slug must be in the form <username>/<project> (e.g. google/guice). Exiting.'
    exit 1
fi

# The task name is the repo slug after replacing slashes with hypens.
if [ ${repo} ]; then
    task_name="$(echo ${repo} | tr / -)"
fi

reproducer_dir="${component_directory}"/reproducer

# Check for existence of the required repositories.
check_repo_exists ${reproducer_dir} 'reproducer'

# Mine pairs from the project.
bash "${SCRIPT_DIR}"/run_mine_project.sh -r ${repo} -t ${threads} -c "${component_directory}"

# Reproduce all pairs mined from the project.
bash "${SCRIPT_DIR}"/run_reproduce_project.sh -r ${repo} -t ${threads} -c "${component_directory}"

print_done_message 'The pipeline completed successfully.'
