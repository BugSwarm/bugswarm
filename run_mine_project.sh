#!/usr/bin/env bash

# Get the absolute path to the directory containing this script. Source: https://stackoverflow.com/a/246128.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Include common functions and constants.
source "${SCRIPT_DIR}"/common.sh

# One step each for PairFinder and PairFilter.
TOTAL_STEPS=3
STAGE='Mine Project'

USAGE='Usage: bash run_mine_project.sh (-r <repo-slug> | -f <repo-slug-file>) [-t <threads>] [-c <component-directory>]'

# Extract command line arguments.
OPTS=$(getopt -o c:r:f:t: --long component-directory:,repo:,repo-file:,threads: -n 'run-mine-project' -- "$@")
while true; do
    case "$1" in
      # Shift twice for options that take an argument.
      -c | --component-directory ) component_directory="$2"; shift; shift ;;
      -r | --repo                ) repo="$2";                shift; shift ;;
      -f | --repo-file           ) repo_file="$2";           shift; shift ;;
      -t | --threads             ) threads="$2";             shift; shift ;;
      -- ) shift; break ;;
      *  ) break ;;
    esac
done

# Perform checks and set defaults for command line arguments.

if [ -z "${repo}" ]; then
    repo_flag=false
else
    repo_flag=true
fi

if [ -z "${repo_file}" ]; then
    repo_file_flag=false
else
    file_path="$(realpath ${repo_file})"
    repo_file_flag=true
fi

if [ ${repo_flag} == ${repo_file_flag} ]; then
    echo ${USAGE}
    exit 1
fi

if [[ -z "${threads}" ]]; then
    echo 'The number of threads is not specified. Defaulting to 1 thread.'
    threads=1
fi

if [[ -z "${component_directory}" ]]; then
    component_directory="/home/$(whoami)/bugswarm"
fi

if ${repo_flag} && [[ ${repo} != ?*"/"?* ]]; then
    echo 'The repo slug must be in the form <username>/<project> (e.g. google/guice). Exiting.'
    exit 1
fi

if ${repo_file_flag} && ( [ ! -f ${file_path} ] || [ ! -s ${file_path} ] ); then
    echo 'The file' ${repo_file} 'is not found or it is empty. Exiting.'
    exit 1
fi

# The task name is the repo slug after replacing slashes with hypens.
if [ ${repo} ]; then
    task_name="$(echo ${repo} | tr / -)"
fi

json_name=${task_name}.json
pair_finder_dir="${component_directory}"/pair-finder
pair_filter_dir="${component_directory}"/pair-filter
pair_classifier_dir="${component_directory}"/pair-classifier

# Check for existence of the required repositories.
check_repo_exists ${pair_finder_dir} 'pair-finder'
check_repo_exists ${pair_filter_dir} 'pair-filter'
check_repo_exists ${pair_classifier_dir} 'pair-classifier'

# PairFinder
print_step "${STAGE}" ${TOTAL_STEPS} 'PairFinder'
cd ${pair_finder_dir}

if ${repo_flag}; then
    python3 pair_finder.py --keep-clone --repo ${repo} --threads ${threads}
else
    python3 pair_finder.py --keep-clone --repo-file ${file_path} --threads ${threads}
fi

exit_if_failed 'PairFinder encountered an error.'

# PairFilter
print_step "${STAGE}" ${TOTAL_STEPS} 'PairFilter'
cd ${pair_filter_dir}

if ${repo_flag}; then
    python3 pair-filter.py ${repo} ${pair_finder_dir}/output/${task_name}
    exit_if_failed 'PairFilter encountered an error.'
else
    task_name="$(echo $(basename ${file_path}) | cut -f 1 -d '.')"
    while read repo; do
        python3 pair-filter.py ${repo} ${pair_finder_dir}/output/${task_name}
        exit_if_failed 'PairFilter encountered an error.'
    done <${file_path}
fi

# PairClassifier
print_step "${STAGE}" ${TOTAL_STEPS} 'Classifier'
cd ${pair_classifier_dir}

if ${repo_flag}; then
    python3 pair-classifier.py --repo ${repo} --log-path ${pair_filter_dir}/original-logs
    exit_if_failed 'PairClassifier encountered an error.'
else
    while read repo; do
        python3 pair-classifier.py --repo ${repo} --log-path ${pair_filter_dir}/original-logs
        exit_if_failed 'PairClassifier encountered an error.'
    done <${file_path}
fi

print_stage_done "${STAGE}"
