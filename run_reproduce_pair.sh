#!/usr/bin/env bash

# Get the absolute path to the directory containing this script. Source: https://stackoverflow.com/a/246128.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Include common functions and constants.
source "${SCRIPT_DIR}"/common.sh

# Increase REPRODUCER_RUNS to be more confident about pair stability at the cost of throughput.
REPRODUCER_RUNS=1
# Steps for Reproducer runs plus one step each for PairChooser, ReproducedResultsAnalyzer, ImagePackager, and
# MetadataPackager.
STAGE='Reproduce Pair'

USAGE='Usage: bash run_reproduce_pair.sh -r <repo-slug> -f <failed-job-id> -p <passed-job-id> [-t <threads>] [-c <component-directory>] [-k | --keep-output]'


# Extract command line arguments.
OPTS=$(getopt -o c:r:t:f:p:k --long component-directory:,repo:,threads:,failed-job-id:,passed-job-id:,keep-output,reproducer-runs: -n 'run-reproduce-pair' -- "$@")
while true; do
    case "$1" in
      # Shift twice for options that take an argument.
      -c | --component-directory ) component_directory="$2"; shift; shift ;;
      -r | --repo                ) repo="$2";                shift; shift ;;
      -t | --threads             ) threads="$2";             shift; shift ;;
      -f | --failed-job-id       ) failed_job_id="$2";       shift; shift ;;
      -k | --keep-output         ) keep_output=true;         shift; shift ;;
      -p | --passed-job-id       ) passed_job_id="$2";       shift; shift ;;
           --reproducer-runs     ) REPRODUCER_RUNS="$2";     shift; shift ;;
      -- ) shift; break ;;
      *  ) break ;;
    esac
done

# Perform checks and set defaults for command line arguments.

if [ -z "${repo}" ]; then
    echo ${USAGE}
    exit 1
fi

if [ -z "${failed_job_id}" ]; then
    echo ${USAGE}
    exit 1
fi

if [ -z "${passed_job_id}" ]; then
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
total_steps=$((${REPRODUCER_RUNS} + 4))

# Check for existence of the required repositories.
check_repo_exists ${reproducer_dir} 'reproducer'

# Create a file containing all pairs mined from the project.
cd ${reproducer_dir}
print_step "${STAGE}" ${total_steps} "PairChooser"

# failed-job-id is used for unique identifier for each job pair since different job pairs could has the same task name
pair_file_path=${reproducer_dir}/input/json/${failed_job_id}/${task_name}.json
python3 pair_chooser.py -o ${pair_file_path} -r ${repo} -f ${failed_job_id} -p ${passed_job_id}
exit_if_failed 'PairChooser encountered an error.'

# Reproducer
for i in $(seq ${REPRODUCER_RUNS}); do
    print_step "${STAGE}" ${total_steps} "Reproducer (run ${i} of ${REPRODUCER_RUNS})"
    python3 entry.py -i ${pair_file_path} -k -t ${threads} -o ${task_name}_${failed_job_id}_run${i}
    exit_if_failed 'Reproducer encountered an error.'
done

# ReproducedResultsAnalyzer
print_step "${STAGE}" ${total_steps} "ReproducedResultsAnalyzer"
python3 reproduced_results_analyzer.py -i ${pair_file_path} -n ${REPRODUCER_RUNS} --task-name ${task_name}_${failed_job_id}
exit_if_failed 'ReproducedResultsAnalyzer encountered an error.'

# ImagePackager (push artifact images to Docker Hub)
print_step "${STAGE}" ${total_steps} 'ImagePackager'
python3 entry.py -i output/result_json/${task_name}_${failed_job_id}.json --package -k -t ${threads} -o ${task_name}_${failed_job_id}_run${REPRODUCER_RUNS}
exit_if_failed 'ImagePackager encountered an error.'

# MetadataPackager (push artifact metadata to the database)
print_step "${STAGE}" ${total_steps} 'MetadataPackager'
python3 packager.py -i output/result_json/${task_name}_${failed_job_id}.json
exit_if_failed 'MetadataPackager encountered an error.'

# clean up output task if no -k flag
if [[ ! "${keep_output}" ]]; then
  for i in $(seq ${REPRODUCER_RUNS}); do
    find output/tasks/${task_name}_${failed_job_id}_run${i} -type f -not -name '*.log' -not -name '*.out' -delete 2>/dev/null
  done
fi

print_stage_done "${STAGE}"
