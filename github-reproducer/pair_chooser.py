"""
PairChooser will filter build pairs based on --failed-job-id and --passed-job-id.
Steps:
1: Use Database to list all artifacts, save [failed job id: artifact] json into a file
2: For each job pair in build pair, filter job pairs based on the inputs.
3: Use json to check if the failed job id is in Database. If yes, names should match.
4: Write filtered build pairs into a file.
"""

import getopt
import logging
import os
import sys
import json

from bugswarm.common import log
from bugswarm.common.json import write_json
from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN


def main(argv=None):
    argv = argv or sys.argv

    # Configure logging.
    log.config_logging(getattr(logging, 'INFO', None))

    output_path, repo, failed_job_id, passed_job_id = _validate_input(argv)

    log.info('Choosing pairs from {}.'.format(repo))

    bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
    buildpairs = bugswarmapi.filter_mined_build_pairs_for_repo(repo)
    if not buildpairs:
        log.error('No mined build pairs exist in the database for {}. Exiting.'.format(repo))
        return 1

    filename = 'artifacts_for_comparing.json'
    if not os.path.isfile(filename):
        artifacts = bugswarmapi.list_artifacts()
        _create_static_artifacts_file(filename, artifacts)
    with open(filename, 'r') as file:
        # artifacts -> [failed job id: artifact]
        artifacts = json.load(file)

    filtered_buildpairs = []
    filtered_jobpair_count = 0
    for bp in buildpairs:
        filtered_jobpairs = []
        for jp in bp['jobpairs']:
            # Filter jobs based on input.
            if should_include_jobpair(jp, failed_job_id, passed_job_id):
                if not is_jp_unique(repo, jp, artifacts):
                    continue
                filtered_jobpairs.append(jp)
                filtered_jobpair_count += 1
        if filtered_jobpairs:
            bp['jobpairs'] = filtered_jobpairs
            filtered_buildpairs.append(bp)

    # Create any missing path components to the output file.
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Write the output file.
    write_json(output_path, filtered_buildpairs)
    bp_pluralized = 'buildpair' if len(filtered_buildpairs) == 1 else 'buildpairs'
    jp_pluralized = 'jobpair' if filtered_jobpair_count == 1 else 'jobpairs'
    log.info('Wrote {} {} with {} {} to {}.'
             .format(len(filtered_buildpairs), bp_pluralized, filtered_jobpair_count, jp_pluralized, output_path))
    log.info('Done!')


def _create_static_artifacts_file(filename, artifacts):
    artifact_dict = {}
    for artifact in artifacts:
        artifact_failed_job_id = artifact['failed_job']['job_id']
        artifact_dict[artifact_failed_job_id] = artifact
    with open(filename, 'w+') as f:
        json.dump(artifact_dict, f)


def is_jp_unique(repo, jp, artifacts):
    # Return False if failed job ID is in the database but repo name doesn't match.
    failed_job_id = jp['failed_job']['job_id']
    if str(failed_job_id) in artifacts:
        artifact_failed_job_id = artifacts[str(failed_job_id)]['failed_job']['job_id']
        artifact_repo = artifacts[str(failed_job_id)]['repo']

        if artifact_failed_job_id == failed_job_id and artifact_repo != repo:
            log.info("Failed Job ID: {} is already associated Artifact's image_tag: {}"
                     .format(failed_job_id, artifacts[str(artifact_failed_job_id)]['image_tag']))
            return False
    return True


def should_include_jobpair(jp, failed_job_id, passed_job_id):
    # Always include if no job ID filters provided.
    if not failed_job_id and not passed_job_id:
        return True
    f_id_matches = jp['failed_job']['job_id'] == failed_job_id
    p_id_matches = jp['passed_job']['job_id'] == passed_job_id
    # Include if both job ID filters are provided and satisfied.
    if failed_job_id and passed_job_id and f_id_matches and p_id_matches:
        return True
    # Include if the failed job ID filter is provided and satisfied.
    if failed_job_id and f_id_matches:
        return True
    # Include if the failed job ID filter is provided and satisfied.
    if passed_job_id and p_id_matches:
        return True
    # Otherwise, exclude.
    return False


def _validate_input(argv):
    # Parse command line arguments.
    short_opts = 'o:r:f:p:'
    long_opts = 'output-path= repo= failed-job-id= passed-job-id='.split()
    try:
        optlist, args = getopt.getopt(argv[1:], short_opts, long_opts)
    except getopt.GetoptError as err:
        _print_usage(msg=err.msg)
        sys.exit(2)

    repo = None
    output_path = None
    failed_job_id = 0
    passed_job_id = 0
    for opt, arg in optlist:
        if opt in ('-o', '--output-path'):
            output_path = os.path.abspath(arg)
        if opt in ('-r', '--repo'):
            repo = arg
        if opt in ('-f', '--failed-job-id'):
            try:
                failed_job_id = int(arg)
            except ValueError:
                _print_usage(msg='The failed_job_id argument must be an integer. Exiting.')
                sys.exit(2)
        if opt in ('-p', '--passed-job-id'):
            try:
                passed_job_id = int(arg)
            except ValueError:
                _print_usage(msg='The passed_job_id argument must be an integer. Exiting.')
                sys.exit(2)

    if not output_path:
        _print_usage(msg='Missing output file argument. Exiting.')
        sys.exit(2)
    if not repo:
        _print_usage(msg='Missing repo argument. Exiting.')
        sys.exit(2)
    f_id_given = failed_job_id != 0
    p_id_given = passed_job_id != 0
    # TODO: Fix this or fix the usage: mode 2 and 3 in usage don't work due to this assertion.
    # Assert that exactly neither or both of the job ID arguments were provided. In other words, if exactly one job ID
    # argument was provided, then exit. Logically, the condition is equivalent to f_id_given XOR p_id_given.
    if f_id_given is not p_id_given:
        _print_usage(msg='Provide exactly neither or both of the job ID arguments. Exiting.')
        sys.exit(2)
    # Assert that, if either or both of the job ID arguments was provided, they are not the same.
    if (f_id_given or p_id_given) and failed_job_id == passed_job_id:
        _print_usage(msg='The passed and failed job ID arguments cannot be the same. Exiting.')
        sys.exit(2)

    return output_path, repo, failed_job_id, passed_job_id


def _print_usage(msg=None):
    if msg:
        log.info(msg)
    log.info('Usage: python3 pair_chooser.py -o <output-path> -r <repo> [-f <failed-job-id> -p <passed-job-id>]')
    log.info('{:>6}, {:<20}{}'.format('-o', '--output-path', 'Path to the file where chosen pairs will be written.'))
    log.info('{:>6}, {:<20}{}'.format('-r', '--repo', 'Repo slug for which to choose mined build pairs.'))
    log.info('{:>6}, {:<20}{}'.format('-f', '--failed-job-id', 'Failed job ID. See discussion below about modes.'))
    log.info('{:>6}, {:<20}{}'.format('-p', '--passed-job-id', 'Passed job ID. See discussion below about modes.'))
    log.info('The output path and repository slug are required.')
    log.info('PairFileCreator has four modes, which will determine the pairs included in the output file.')
    log.info('1. Choose all pairs from a project.')
    log.info('     Input:  repo')
    log.info('2. Choose pairs from a project s.t. the failed job has a specific ID.')
    log.info('     Input:  repo, failed job ID')
    log.info('3. Choose pairs from a project s.t. the passed job has a specific ID.')
    log.info('     Input:  repo, passed job ID')
    # TODO: Current behavior is OR, not AND. Bug or feature?
    log.info('4. Choose pairs from a project s.t. the failed and passed jobs have specific IDs.')
    log.info('     Input:  repo, failed job ID, passed job ID')


if __name__ == '__main__':
    sys.exit(main())
