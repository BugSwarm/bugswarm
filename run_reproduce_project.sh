#!/usr/bin/env bash

# Get the absolute path to the directory containing this script. Source: https://stackoverflow.com/a/246128.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Include common functions and constants.
source "${SCRIPT_DIR}"/common.sh

# Increase REPRODUCER_RUNS to be more confident about pair stability at the cost of throughput.
REPRODUCER_RUNS=5
# Steps for Reproducer runs plus one step each for PairChooser, ReproducedResultsAnalyzer, ImagePackager,
# MetadataPackager, and CacheDependency.
TOTAL_STEPS=$((${REPRODUCER_RUNS} + 5))
STAGE='Reproduce Project'

USAGE='Usage: bash run_reproduce_project.sh -r <repo-slug> [-t <threads>] [-c <component-directory>]'


# Extract command line arguments.
OPTS=$(getopt -o c:r:t: --long component-directory:,repo:,threads: -n 'run-reproduce-project' -- "$@")
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
    component_directory="/home/$(whoami)/bugswarm"
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
cache_dep_dir="${component_directory}"/cache-dependency

# Check for existence of the required repositories.
check_repo_exists ${reproducer_dir} 'reproducer'

# Create a file containing all pairs mined from the project.
cd ${reproducer_dir}
print_step "${STAGE}" ${TOTAL_STEPS} "PairChooser"
pair_file_path=${reproducer_dir}/input/json/${task_name}.json
python3 pair_chooser.py -o ${pair_file_path} -r ${repo}
exit_if_failed 'PairChooser encountered an error.'

# Reproducer
for i in $(seq ${REPRODUCER_RUNS}); do
    print_step "${STAGE}" ${TOTAL_STEPS} "Reproducer (run ${i} of ${REPRODUCER_RUNS})"
    python3 entry.py -i ${pair_file_path} -k -t ${threads} -o ${task_name}_run${i}
    exit_if_failed 'Reproducer encountered an error.'
done

# ReproducedResultsAnalyzer
print_step "${STAGE}" ${TOTAL_STEPS} "ReproducedResultsAnalyzer"
python3 reproduced_results_analyzer.py -i ${pair_file_path} -n ${REPRODUCER_RUNS} --task-name ${task_name}
exit_if_failed 'ReproducedResultsAnalyzer encountered an error.'

# ImagePackager (push artifact images to Docker Hub)
print_step "${STAGE}" ${TOTAL_STEPS} 'ImagePackager'
python3 entry.py -i output/result_json/${task_name}.json --package -k -t ${threads} -o ${task_name}_run${REPRODUCER_RUNS}
exit_if_failed 'ImagePackager encountered an error.'

# MetadataPackager (push artifact metadata to the database)
print_step "${STAGE}" ${TOTAL_STEPS} 'MetadataPackager'
python3 packager.py -i output/result_json/${task_name}.json
exit_if_failed 'MetadataPackager encountered an error.'

print_step "${STAGE}" ${TOTAL_STEPS} 'CacheDependency'
cd ${cache_dep_dir}
python3 get_reproducer_output.py -i ${reproducer_dir}/output/result_json/${task_name}.json -o ${task_name}
exit_if_failed 'CacheDependency encountered an error.'
if [ -s input/${task_name} ]; then
    python3 CacheMaven.py input/${task_name} ${task_name}
    exit_if_failed 'CacheDependency encountered an error.'
fi

print_stage_done "${STAGE}"
