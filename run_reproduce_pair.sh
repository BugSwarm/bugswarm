#!/usr/bin/env bash

# Get the absolute path to the directory containing this script. Source: https://stackoverflow.com/a/246128.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Include common functions and constants.
source "${SCRIPT_DIR}"/common.sh

# Ensure that Git won't prompt for input and hang the script.
export GIT_TERMINAL_PROMPT=0

# Increase REPRODUCER_RUNS to be more confident about pair stability at the cost of throughput.
REPRODUCER_RUNS=5
STAGE='Reproduce Pair'

USAGE='Usage: bash run_reproduce_pair.sh --ci <ci> (--pair-file <pair-file> | -r <repo-slug> -f <failed-job-id> -p <passed-job-id>) [-t <threads>] [-c <component-directory>] [--reproducer-runs <reproducer-runs>] [--skip-cacher] [--cleanup-images] [-s]'


# Extract command line arguments.
OPTS=$(getopt -o c:r:t:f:p:s --long component-directory:,pair-file:,repo:,threads:,failed-job-id:,passed-job-id:,reproducer-runs:,skip-check-disk,ci:,skip-cacher,no-push,cleanup-images -n 'run-reproduce-pair' -- "$@")
exit_if_failed 'Unrecognized command-line options.'
eval set -- "$OPTS"
while true; do
    case "$1" in
      # Shift twice for options that take an argument.
      -c | --component-directory ) component_directory="$2";    shift; shift ;;
      -r | --repo                ) repo="$2";                   shift; shift ;;
           --pair-file           ) gpi_file="$(realpath "$2")"; shift; shift ;;
      -t | --threads             ) threads="$2";                shift; shift ;;
      -f | --failed-job-id       ) failed_job_id="$2";          shift; shift ;;
      -p | --passed-job-id       ) passed_job_id="$2";          shift; shift ;;
           --reproducer-runs     ) REPRODUCER_RUNS="$2";        shift; shift ;;
      -s | --skip-check-disk     ) skip_check_disk="-s";        shift;;
           --ci                  ) ci_service="$2";             shift; shift ;;
           --skip-cacher         ) skip_cacher='true';          shift;;
           --no-push             ) no_push='--no-push';         shift;;
           --cleanup-images      ) cleanup='--cleanup-images';  shift;;
      -- ) shift; break ;;
      *  ) break ;;
    esac
done

# Perform checks and set defaults for command line arguments.

if [[ ${ci_service} != 'travis' && ${ci_service} != 'github' ]]; then
    echo '--ci must be one of "travis" or "github". Exiting.'
    echo ${USAGE}
    exit 1
fi

if [ -z "${gpi_file}" ]; then
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

    if [[ ${repo} != *"/"* ]]; then
        echo 'The repo slug must be in the form <username>/<project> (e.g. google/guice). Exiting.'
        exit 1
    fi
elif [[ "${repo}" || "${failed_job_id}" || "${passed_job_id}" ]]; then
    print_red 'The --pair-file and --repo/--failed-job-id/--passed-job-id options cannot be used together. Exiting.'
    exit 1
fi

if [[ -n "${cleanup}" && "${ci}" == "travis" ]]; then
    echo 'The --cleanup-images flag is not available for Travis runs. Exiting.'
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

if [ "${gpi_file}" ]; then
    # Task name is the basename of the pair file with the extension removed
    task_name="$(basename "${gpi_file%.*}")"
elif [ ${repo} ]; then
    # The task name is the repo slug and failed job ID after replacing slashes with hypens.
    task_name="$(echo ${repo} | tr / -)_${failed_job_id}"
fi

reproducer_dir="${component_directory}/${ci_service}-reproducer"
cacher_dir="${component_directory}/${ci_service}-cacher"

if [[ $skip_cacher ]]; then
    check_repo_exists "${reproducer_dir}" 'reproducer'
    TOTAL_STEPS=$((REPRODUCER_RUNS + 3))
else
    check_repo_exists "${reproducer_dir}" 'reproducer'
    check_repo_exists "${cacher_dir}" 'cacher'
    TOTAL_STEPS=$((REPRODUCER_RUNS + 7))
fi

# Create a file containing all pairs mined from the project.
cd "${reproducer_dir}"
print_step "${STAGE}" ${TOTAL_STEPS} "PairChooser"

# failed-job-id is used for unique identifier for each job pair since different job pairs could has the same task name
pair_file_path="${reproducer_dir}/input/json/${task_name}.json"
if [ ${gpi_file} ]; then
    python3 pair_chooser.py -o "${pair_file_path}" --pair-file "${gpi_file}"
    exit_if_failed 'PairChooser encountered an error.'
else
    python3 pair_chooser.py -o "${pair_file_path}" -r "${repo}" -f "${failed_job_id}" -p "${passed_job_id}"
    exit_if_failed 'PairChooser encountered an error.'
fi

# Reproducer
for i in $(seq ${REPRODUCER_RUNS}); do
    print_step "${STAGE}" ${TOTAL_STEPS} "Reproducer (run ${i} of ${REPRODUCER_RUNS})"
    python3 entry.py -i "${pair_file_path}" -t "${threads}" -o "${task_name}_run${i}" ${skip_check_disk}
    exit_if_failed 'Reproducer encountered an error.'
done

# ReproducedResultsAnalyzer
print_step "${STAGE}" ${TOTAL_STEPS} "ReproducedResultsAnalyzer"
python3 reproduced_results_analyzer.py -i "${pair_file_path}" -n "${REPRODUCER_RUNS}" --task-name "${task_name}"
exit_if_failed 'ReproducedResultsAnalyzer encountered an error.'

# ImagePackager (push artifact images to Docker Hub)
print_step "${STAGE}" ${TOTAL_STEPS} 'ImagePackager'
python3 entry.py -i "output/result_json/${task_name}.json" --package -t 1 -o "${task_name}_pkg" ${skip_check_disk} ${no_push} ${cleanup}
exit_if_failed 'ImagePackager encountered an error.'

if [[ ! $skip_cacher ]]; then
    task_json_path="${reproducer_dir}/output/result_json/${task_name}.json"
    cacher_input_file="${reproducer_dir}/input/${task_name}"
    repo_clone_path="${reproducer_dir}/intermediates/project_repos"
    cacher_output_path="${cacher_dir}/output/${task_name}.csv"

    print_step "${STAGE}" ${TOTAL_STEPS} 'Cacher'
    python3 get_reproducer_output.py -i "${task_json_path}" -o "${task_name}"
    exit_if_failed 'get_reproducer_output.py encountered an error.'

    if [[ ! -s $cacher_input_file ]]; then
        print_red "$cacher_input_file does not exist or is empty."
        print_red "Either all reproducible artifacts have already been cached, or there were no reproducible artifacts to begin with."
        print_red "Exiting."
        exit
    fi

    cd "${cacher_dir}"
    python3 entry.py "${cacher_input_file}" "${task_name}" --workers "${threads}" --task-json "${task_json_path}" ${no_push} ${cleanup} --disconnect-network-during-test
    exit_if_failed "CacheDependency encountered an error."

    cd "${reproducer_dir}"
    print_step "${STAGE}" ${TOTAL_STEPS} 'MetadataPackager'
    python3 packager.py -i "${task_json_path}"
    exit_if_failed 'MetadataPackager encountered an error.'

    print_step "${STAGE}" ${TOTAL_STEPS} 'ArtifactLogPackager'
    python3 add_artifact_logs.py "${task_name}"
    exit_if_failed 'ArtifactLogPackager encountered an error.'

    print_step "${STAGE}" ${TOTAL_STEPS}, 'ArtifactDiffAdder'
    python3 add_artifact_diffs.py -j "${task_json_path}" -c "${cacher_output_path}" -p "${repo_clone_path}"
    exit_if_failed 'ArtifactDiffAdder encountered an error.'
fi

print_stage_done "${STAGE}"
