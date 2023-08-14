"""
PairChooser will filter build pairs based on --failed-job-id and --passed-job-id.
Steps:
1: Use Database to list all artifacts, save [failed job id: artifact] json into a file
2: For each job pair in build pair, filter job pairs based on the inputs.
3: Use json to check if the failed job id is in Database. If yes, names should match.
4: Write filtered build pairs into a file.
"""

import argparse
import csv
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

    output_path, pair_file, repo, failed_job_id, passed_job_id = _validate_input(argv)

    bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
    filename = 'artifacts_for_comparing.json'
    if not os.path.isfile(filename):
        artifacts = bugswarmapi.list_artifacts()
        _create_static_artifacts_file(filename, artifacts)
    with open(filename, 'r') as file:
        # artifacts -> [failed job id: artifact]
        artifacts = json.load(file)

    try:
        if pair_file:
            buildpairs, jobpair_count = handle_pair_file(pair_file, artifacts)
        else:
            buildpairs, jobpair_count = handle_single_repo(repo, failed_job_id, passed_job_id, artifacts)
    except Exception as e:
        log.error('{}'.format(e))
        return 1

    write_output_file(output_path, buildpairs, jobpair_count)


def handle_single_repo(repo, failed_job_id, passed_job_id, artifacts):
    log.info('Choosing pairs from {}.'.format(repo))

    bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
    buildpairs = bugswarmapi.filter_mined_build_pairs_for_repo(repo)
    if not buildpairs:
        raise Exception('No mined build pairs exist in the database for {}. Exiting.'.format(repo))

    filtered_buildpairs = []
    filtered_jobpair_count = 0
    for bp in buildpairs:
        if bp['ci_service'] != 'github':
            # Filter out non-GitHub builds.
            continue

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

    return filtered_buildpairs, filtered_jobpair_count


def handle_pair_file(pair_file, artifacts):
    log.info('Choosing pairs from pair file {}.'.format(pair_file))
    with open(pair_file) as f:
        try:
            # job_pairs is a list of (str, int, int) tuples
            job_id_pairs = [(fields[0], *map(int, fields[1:])) for fields in csv.reader(f)]
            print(job_id_pairs)
        except Exception:
            raise Exception('{} is improperly formatted. Exiting.'.format(pair_file))

    found_buildpairs = {}
    found_jobpairs = {}
    filtered_jobpair_count = 0

    bugswarmapi = DatabaseAPI(DATABASE_PIPELINE_TOKEN)
    for repo, failed_id, passed_id in job_id_pairs:
        log.info('Processing job pair ({}, {}, {})'.format(repo, failed_id, passed_id))

        if failed_id not in found_jobpairs:
            # Failed job ID is not in the cache, so we have to query the database.

            # Get the build pair with a specific job pair.
            flt = {
                'repo': repo,
                'jobpairs': {
                    '$elemMatch': {
                        'failed_job.job_id': failed_id,
                        'passed_job.job_id': passed_id
                    }
                },
                'ci_service': 'github'
            }
            try:
                # Assumes that each repo-failed_id-passed_id combination is unique.
                # (If it isn't, something's gone wrong.)
                bp = bugswarmapi.filter_mined_build_pairs(json.dumps(flt))[0]
            except IndexError:
                log.warning('The job pair ({}, {}, {}) is not in the database or is not a GitHub Actions pair.'
                            'Skipping.')
                continue

            # Cache the BP.
            failed_build_id = bp['failed_build']['build_id']
            found_buildpairs[failed_build_id] = bp

            # Cache all the JPs in this BP, so we don't have to query the database for each JP.
            for jp in bp['jobpairs']:
                found_jobpairs[jp['failed_job']['job_id']] = (failed_build_id, jp)

            # Empty the JP list so we can add back in the ones we want.
            bp['jobpairs'] = []

        # Get buildpair ID and jobpair from the cache.
        failed_build_id, jp = found_jobpairs[failed_id]
        if is_jp_unique(repo, jp, artifacts):
            # Add this JP back to its BP's list.
            found_buildpairs[failed_build_id]['jobpairs'].append(jp)
            filtered_jobpair_count += 1

    # Discard BPs with empty JP lists.
    filtered_buildpairs = [bp for bp in found_buildpairs.values() if bp['jobpairs']]
    return filtered_buildpairs, filtered_jobpair_count


def write_output_file(output_path, filtered_buildpairs, filtered_jobpair_count):
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
    if failed_job_id and passed_job_id:
        return f_id_matches and p_id_matches
    # Include if the failed job ID filter is provided and satisfied.
    if failed_job_id and f_id_matches:
        return True
    # Include if the failed job ID filter is provided and satisfied.
    if passed_job_id and p_id_matches:
        return True
    # Otherwise, exclude.
    return False


def _validate_input(argv):
    epilog = """
PairChooser has 5 modes, which will determine the pairs included in the output file.
1. Choose all pairs from a project.
     Input: --repo
2. Choose pairs from a project s.t. the failed job has a specific ID.
     Input: --repo and --failed-job-id
3. Choose pairs from a project s.t. the passed job has a specific ID.
     Input: --repo and --passed-job-id
4. Choose pairs from a project s.t. the failed and passed jobs have specific IDs.
     Input: --repo, --failed-job-id, and --passed-job-id
5. Choose pairs from an input CSV file.
     Input: --pair-file
"""
    p = argparse.ArgumentParser(argv[0], description='Creates an input file for the reproducer.',
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=epilog)

    p.add_argument('-o', '--output-path', required=True, type=os.path.abspath,
                   help='Path to the file where chosen pairs will be written.')
    p.add_argument('--pair-file', type=os.path.abspath,
                   help='Path to a file generated by generate_pair_input.py. Cannot be used with -r, -f, or -p.')
    p.add_argument('-r', '--repo', help='Repo slug for which to choose mined build pairs.')
    p.add_argument('-f', '--failed-job-id', type=int, help='Failed job ID. See discussion below about modes.')
    p.add_argument('-p', '--passed-job-id', type=int, help='Passed job ID. See discussion below about modes.')
    args = p.parse_args(argv[1:])

    if not args.repo and not args.pair_file:
        p.error('One of --repo or --pair-file must be provided.')
    if args.pair_file and (args.repo or args.failed_job_id or args.passed_job_id):
        p.error('--pair-file cannot be used with -r, -f, or -p.')
    if args.failed_job_id == args.passed_job_id is not None:
        p.error('The passed and failed job ID arguments cannot be the same.')
    if not os.path.isfile(args.pair_file):
        p.error('"{}" does not exist or is not a file.'.format(args.pair_file))

    return args.output_path, args.pair_file, args.repo, args.failed_job_id, args.passed_job_id


if __name__ == '__main__':
    sys.exit(main())
