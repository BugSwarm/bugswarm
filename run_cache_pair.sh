#!/usr/bin/env bash

# Get the absolute path to the directory containing this script. Source: https://stackoverflow.com/a/246128.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Include common functions and constants.
source "${SCRIPT_DIR}"/common.sh

# Increase REPRODUCER_RUNS to be more confident about pair stability at the cost of throughput.
REPRODUCER_RUNS=5
# Steps for Reproducer runs plus one step each for PairChooser, ReproducedResultsAnalyzer, ImagePackager,
# MetadataPackager, and CacheDependency.
STAGE='Cache Pair'

# Only need failed-job-id
USAGE='Usage: bash run_cache_pair.sh --ci <ci> -r <repo-slug> -f <failed-job-id> [-c <component-directory>] [--no-push] [-a <caching-args>]'


# Extract command line arguments.
OPTS=$(getopt -o c:r:f:a: --long component-directory:,repo:,failed-job-id:,caching-args:,no-push,ci: -n 'run-cache-pair' -- "$@")
eval set -- "$OPTS"
while true; do
    case "$1" in
      # Shift twice for options that take an argument.
      -c | --component-directory ) component_directory="$2"; shift; shift ;;
      -r | --repo                ) repo="$2";                shift; shift ;;
      -f | --failed-job-id       ) failed_job_id="$2";       shift; shift ;;
           --no-push             ) no_push='--no-push';      shift ;;
      -a | --caching-args        ) caching_args="$2";        shift; shift ;;
           --ci                  ) ci_service="$2";          shift; shift ;;
      -- ) shift; break ;;
      *  ) break ;;
    esac
done

# Perform checks and set defaults for command line arguments.

if [[ ${ci_service} != 'travis' && ${ci_service} != 'github' ]]; then
    echo '--ci must be one of "travis" or "github". Exiting.'
    exit 1
fi

if [ -z "${repo}" ]; then
    echo ${USAGE}
    exit 1
fi

if [ -z "${failed_job_id}" ]; then
    echo ${USAGE}
    exit 1
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

if [[ -z "${caching_args}" ]]; then
    caching_args=""
fi

if [[ ${no_push} ]]; then
    TOTAL_STEPS=1
else
    TOTAL_STEPS=3
fi

reproducer_dir="${component_directory}/${ci_service}-reproducer"
cache_dep_dir="${component_directory}/${ci_service}-cacher"

# Check for existence of the required repositories.
check_repo_exists "${reproducer_dir}" 'reproducer'
check_repo_exists "${cache_dep_dir}" 'cache-dependency'

print_step "${STAGE}" ${TOTAL_STEPS} 'CacheDependency'

cd "${reproducer_dir}"
echo "Running: python3 get_reproducer_output.py -i ${reproducer_dir}/output/result_json/${task_name}_${failed_job_id}.json -o ${task_name}_${failed_job_id}"
python3 get_reproducer_output.py -i "${reproducer_dir}/output/result_json/${task_name}_${failed_job_id}.json" -o "${task_name}_${failed_job_id}"

if [ ! -s ${reproducer_dir}/input/${task_name}_${failed_job_id} ]; then
    print_red "${reproducer_dir}/input/${task_name}_${failed_job_id} does not exist, which should be created by get_reproducer_output.py."
    print_red 'Either all reproducible artifacts have been cached, or there were no reproducible artifacts to begin with.'
    exit 1
fi

echo
echo 'Attempting to cache the following artifacts:'
cat "${reproducer_dir}/input/${task_name}_${failed_job_id}"

cd "${cache_dep_dir}"
echo
echo "Running: python3 CacheMaven.py ${reproducer_dir}/input/${task_name}_${failed_job_id} ${task_name}_${failed_job_id} --task_json ${reproducer_dir}/output/result_json/${task_name}_${failed_job_id}.json ${no_push} ${caching_args}"
python3 CacheMaven.py "${reproducer_dir}/input/${task_name}_${failed_job_id}" "${task_name}_${failed_job_id}" --task_json "${reproducer_dir}/output/result_json/${task_name}_${failed_job_id}.json" ${no_push} ${caching_args}
exit_if_failed 'CacheDependency encountered an error.'

if [[ ! ${no_push} ]]; then
    cd "${reproducer_dir}"

    # MetadataPackager (push artifact metadata to the database)
    print_step "${STAGE}" ${TOTAL_STEPS} 'MetadataPackager'
    python3 packager.py -i "output/result_json/${task_name}_${failed_job_id}.json"
    exit_if_failed 'MetadataPackager encountered an error.'

    print_step "${STAGE}" ${TOTAL_STEPS} 'ArtifactLogPackager'
    python3 add_artifact_logs.py "${task_name}_${failed_job_id}"
    exit_if_failed 'ArtifactLogPackager encountered an error.'
fi

print_stage_done "${STAGE}"
