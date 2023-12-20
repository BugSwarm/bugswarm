#!/usr/bin/env bash

# Get the absolute path to the directory containing this script. Source: https://stackoverflow.com/a/246128.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Include common functions and constants.
source "${SCRIPT_DIR}"/common.sh

STAGE='Cache Artifact Dependencies'

USAGE='Usage: bash run_cacher.sh --ci <ci> -i <input-json> [-t <threads>] [-c <component-directory>] [--no-push] [-a "<caching-args>"]'

# Extract command line arguments.
OPTS=$(getopt -o c:i:t:a: --long component-directory:,input-json:,threads:,no-push,caching-args:,ci: -n 'run-cacher' -- "$@")
if [[ $? -ne 0 ]]; then
    echo "$USAGE"
    exit 1
fi
eval set -- "$OPTS"
while true; do
    case "$1" in
      # Shift twice for options that take an argument.
      -c | --component-directory ) component_directory="$2";      shift; shift ;;
      -i | --input-json          ) input_json="$(realpath "$2")"; shift; shift ;;
      -t | --threads             ) threads="$2";                  shift; shift ;;
           --no-push             ) no_push='--no-push';           shift ;;
      -a | --caching-args        ) caching_args="$2";             shift; shift ;;
           --ci                  ) ci_service="$2";               shift; shift ;;
      -- ) shift; break ;;
      *  ) break ;;
    esac
done

# Perform checks and set defaults for command line arguments.

if [[ ${ci_service} != 'travis' && ${ci_service} != 'github' ]]; then
    echo '--ci must be one of "travis" or "github". Exiting.'
    exit 1
fi

if [[ ! -f "${input_json}" ]]; then
    echo "$input_json is not a file. Exiting."
    exit 1
fi

if [[ -z "${threads}" ]]; then
    echo 'The number of threads is not specified. Defaulting to 1 thread.'
    threads=1
fi

if [[ -z "${component_directory}" ]]; then
    component_directory="$SCRIPT_DIR"
elif [[ -d "${component_directory}" ]]; then
    component_directory="$(realpath "${component_directory}")"
else
    echo "The path '${component_directory}' does not exist or is not a directory. Exiting."
    exit 1
fi

if [[ ${no_push} ]]; then
    TOTAL_STEPS=1  # CacheDependency
else
    TOTAL_STEPS=3  # CacheDependency, MetadataPackager, ArtifactLogPackager
fi

# The task name is the basename of the input JSON file, without the extension.
task_name="$(basename "${input_json%.*}")"

reproducer_dir="${component_directory}/${ci_service}-reproducer"
cache_dep_dir="${component_directory}/${ci_service}-cacher"

# Check for existence of the required repositories.
check_repo_exists "${reproducer_dir}" 'reproducer'
check_repo_exists "${cache_dep_dir}" 'cache-dependency'

print_step "${STAGE}" ${TOTAL_STEPS} 'CacheDependency'
cd "${reproducer_dir}"
echo "Running: python3 get_reproducer_output.py -i $input_json -o $task_name"
python3 get_reproducer_output.py -i "${input_json}" -o "${task_name}"

cacher_input_file="${reproducer_dir}/input/${task_name}"

if [[ ! -s $cacher_input_file ]]; then
    print_red "$cacher_input_file does not exist or is empty."
    print_red "Either all reproducible artifacts have been cached, or there were no reproducible artifacts to begin with."
    print_red "Exiting."
    exit
fi

echo
echo 'Attempting to cache the following artifacts:'
cat "${reproducer_dir}/input/${task_name}"

cd "${cache_dep_dir}"
echo

echo "Running: python3 entry.py ${cacher_input_file} ${task_name} --workers ${threads} --task-json ${input_json} ${no_push} ${caching_args}"
python3 entry.py "${cacher_input_file}" "${task_name}" --workers "${threads}" --task-json "${input_json}" ${no_push} ${caching_args}
exit_if_failed 'CacheDependency encountered an error.'

if [[ ! ${no_push} ]]; then
    cd "${reproducer_dir}"

    # MetadataPackager (push artifact metadata to the database)
    print_step "${STAGE}" ${TOTAL_STEPS} 'MetadataPackager'
    python3 packager.py -i "output/result_json/${task_name}.json"
    exit_if_failed 'MetadataPackager encountered an error.'

    print_step "${STAGE}" ${TOTAL_STEPS} 'ArtifactLogPackager'
    python3 add_artifact_logs.py "${task_name}"
    exit_if_failed 'ArtifactLogPackager encountered an error.'
fi

print_stage_done "${STAGE}"
