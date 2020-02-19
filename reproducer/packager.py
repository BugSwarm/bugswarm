"""
Entry point for pushing artifact metadata to the database.
"""

import getopt
import logging
import os
import sys
import time

from datetime import date

from bugswarm.common import log
from bugswarm.common.json import read_json
from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.utils import get_current_component_version_message
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN

from reproducer.config import Config
from reproducer.utils import Utils


class Packager(object):
    def __init__(self, input_file, csv_mode=False):
        self.input_file = input_file
        self.csv_mode = csv_mode
        self.task = str(os.path.splitext(input_file)[0].split('/')[-1])
        self.config = Config(self.task)
        self.utils = Utils(self.config)

    def run(self):
        buildpairs = read_json(self.input_file)
        # Only check for skipping if CSV mode is disabled.
        to_insert = []
        for bp in buildpairs:
            for jp in bp['jobpairs']:
                image_tag = Utils.construct_jobpair_image_tag_from_dict(jp, bp['repo'])
                reproduce_successes, _, _ = Packager._calc_stability(jp)
                artifact_exists = Packager._is_artifact_in_db(image_tag)
                if artifact_exists and not reproduce_successes:
                    log.info('Artifact', image_tag, 'already exists in the database.')
                    continue
                to_insert.append((image_tag, artifact_exists, self._structure_artifact_data(image_tag, bp, jp)))

        if self.csv_mode:
            self._write_csv(to_insert)
        elif not to_insert:
            log.info('Done! No new metadata to insert.')
        else:
            inserts = 0
            errors = 0
            for artifact_data in to_insert:
                (image_tag, artifact_exists, artifact) = artifact_data
                if artifact_exists:
                    if Packager._update_artifact(image_tag, artifact):
                        inserts += 1
                    else:
                        errors += 1
                elif Packager._insert_artifact(artifact):
                    inserts += 1
                else:
                    errors += 1
            if errors == 0:
                log.info('Done! Inserted metadata for {} jobpairs with 0 errors.'.format(inserts))
            else:
                log.info('Done! Attempted to insert {} jobpairs into the database. {} insertions succeeded and {} '
                         'encountered an error.'.format(len(to_insert), inserts, errors))

    @staticmethod
    def _flatten_keys():
        keys = [
            'tag',
            'image_tag',
            'repo',
            'repo_mined_version',
            'pr_num',
            'branch',
            'base_branch',
            'lang',
            'build_system',
            'test_framework',
            'merged_at',
            'is_error_pass',
            'reproduced',

            'match',
            'reproduce_successes',
            'reproduce_attempts',
            'stability',

            # Evaluation info.
            'filtered_reason',

            # Metrics.
            'metrics',
        ]
        for prefix in ['failed_job_', 'passed_job_']:
            keys.append(prefix + 'build_id')
            keys.append(prefix + 'job_id')
            keys.append(prefix + 'build_job')
            keys.append(prefix + 'base_sha')
            keys.append(prefix + 'trigger_sha')
            keys.append(prefix + 'committed_at')
            keys.append(prefix + 'message')
            keys.append(prefix + 'num_tests_failed')
            keys.append(prefix + 'num_tests_run')
            keys.append(prefix + 'failed_tests')
            keys.append(prefix + 'mismatch_attrs')
            keys.append(prefix + 'is_git_repo')
        return keys

    def _write_csv(self, data):
        os.makedirs(self.config.csv_dir, exist_ok=True)
        filename = self.task + '.csv'
        filepath = os.path.join(self.config.csv_dir, filename)
        keys = Packager._flatten_keys()
        with open(filepath, 'w') as f:
            # Write header.
            f.write(','.join(keys) + '\n')
            for d in data:
                line = []
                for key in keys:
                    if key.startswith('failed_job_'):
                        k = key.split('failed_job_')[1]
                        replaced = str(d['failed_job'][k]).replace(',', '#')
                        replaced = replaced.replace('\n', ' ')
                        line.append(replaced)  # Replace , with # to disambiguate the delimiter.
                    elif key.startswith('passed_job_'):
                        k = key.split('passed_job_')[1]
                        replaced = str(d['passed_job'][k]).replace(',', '#')
                        replaced = replaced.replace('\n', ' ')
                        line.append(replaced)  # Replace , with # to disambiguate the delimiter.
                    else:
                        line.append(d[key])
                f.write(','.join(map(str, line)) + '\n')

        log.info('Done! Wrote', len(data), 'rows into the CSV file at', filepath + '.')

    def _structure_artifact_data(self, image_tag, bp, jp):
        log.info('Extracting metadata for jobpair', image_tag + '.')

        reproduced = Packager._is_jobpair_reproduced(jp)
        repo = bp['repo']
        reproduce_successes, reproduce_attempts, stability = Packager._calc_stability(jp)
        failed_job = jp['failed_job']
        passed_job = jp['passed_job']
        builds = [bp['failed_build'], bp['passed_build']]
        jobs = [failed_job, passed_job]

        # In the case where "No files are changed", determined by our pair-classifier.py, there would not be a
        # classification key for that jobpair. We insert a blank template in case the artifact is populated to our
        # website
        try:
            classification = jp['classification']
            classification = {
                'test': classification['test'],
                'build': classification['build'],
                'code': classification['code'],
                'exceptions': classification['exceptions']
            }
        except KeyError:
            classification = {
                'test': 'NA',
                'build': 'NA',
                'code': 'NA',
                'exceptions': []
            }

        today = str(date.today())
        status = 'Unreproducible'
        if reproduce_successes == 5:
            status = 'Reproducible'
        elif 0 < reproduce_successes < 5:
            status = 'Flaky'
        current_status = {
            'time_stamp': today,
            'status': status
        }

        d = {
            'tag': image_tag,
            'image_tag': image_tag,
            'repo': repo,
            'repo_mined_version': bp['repo_mined_version'],
            'pr_num': int(bp['pr_num']),
            'branch': bp['branch'],
            'base_branch': bp['base_branch'],
            'lang': [j['language'] for j in bp['failed_build']['jobs']
                     if j['job_id'] == failed_job['job_id']][0].title(),
            # Assume the build system and test framework is the same for both jobs. In some rare cases, this assumption
            # will not hold.
            'build_system': failed_job['orig_result']['tr_build_system'] if failed_job['orig_result'] else '',
            'test_framework': failed_job['orig_result']['tr_log_frameworks'] if failed_job['orig_result'] else '',
            'merged_at': bp['merged_at'],
            'is_error_pass': bp['is_error_pass'],
            'reproduced': reproduced,

            'match': Packager._calc_match_over_run(jp) if reproduced else '',
            'reproduce_successes': reproduce_successes,
            'reproduce_attempts': reproduce_attempts,
            'stability': stability,
            'creation_time': int(time.time()),

            # Evaluation info.
            'filtered_reason': jp.get('filtered_reason', ''),

            # Metrics. Empty by default and will be populated later by other components during post-processing.
            'metrics': {},
            'current_status': current_status,
            'classification': classification
        }

        for i in range(2):
            job_key = 'failed_job' if i == 0 else 'passed_job'
            patches = {}
            job = jobs[i]

            # Find index of job in builds[i]['jobs'].
            job_id = job['job_id']
            jobs_index = next(i for i, j in enumerate(builds[i]['jobs']) if j['job_id'] == job_id)

            # Add patch information if the job is Java 7 and has at least one reproduce success.
            job_config = builds[i]['jobs'][jobs_index]['config']
            if job_config.get('jdk') in ['oraclejdk7', 'openjdk7']:
                # TODO: Collect patch names as each patch is applied. That is, do not wait until this method because the
                # patches created now may not exactly match the patches applied.
                patches['mvn-tls'] = today

            if job.get('pip_patch'):
                patches['pip-yaml-patch'] = today

            patches['remove-ppa'] = today

            d[job_key] = {
                'base_sha': builds[i]['base_sha'],
                'build_id': builds[i]['build_id'],
                'build_job': [j['build_job'] for j in builds[i]['jobs'] if j['job_id'] == jobs[i]['job_id']][0],
                'committed_at': builds[i]['committed_at'],
                'failed_tests': jobs[i]['orig_result']['tr_log_tests_failed'] if jobs[i]['orig_result'] else '',
                'job_id': job_id,
                'message': builds[i]['message'],
                'mismatch_attrs': jobs[i]['mismatch_attrs'],
                'num_tests_failed': jobs[i]['orig_result']['tr_log_num_tests_failed'] if jobs[i]['orig_result'] else '',
                'num_tests_run': jobs[i]['orig_result']['tr_log_num_tests_run'] if jobs[i]['orig_result'] else '',
                'trigger_sha': builds[i]['travis_merge_sha'] if builds[i]['travis_merge_sha'] else
                builds[i]['head_sha'],
                'is_git_repo': Packager._artifact_is_git_repo(builds[i]),
                'config': job_config,
                'patches': patches,
                'component_versions': {
                    'analyzer': Utils.get_analyzer_version(),
                    'reproducer': Utils.get_reproducer_version(),
                },
            }
        return d

    @staticmethod
    def _is_jobpair_reproduced(jobpair):
        """
        If match type == N, then the jobpair encountered an error during the reproducing process.
        A jobpair is labeled 'reproduced' if it has at least 2 non-'N' match types.
        """
        matches = jobpair['match_history'].values()
        return len([m for m in matches if str(m).isdigit()]) >= 2

    @staticmethod
    def _calc_match_over_run(jobpair):
        assert jobpair
        matches = jobpair['match_history'].values()
        match_type = 0
        if 1 in matches:
            match_type = 1
        elif 2 in matches:
            match_type = 2
        elif 3 in matches:
            match_type = 3
        return match_type

    @staticmethod
    def _calc_stability(jobpair):
        """
        Returns a string representing the proportion of times the job completed as expected. e.g. '3/5'.

        :param jobpair: A dictionary representing job pair JSON.
        """
        assert jobpair
        matches = jobpair['match_history'].values()
        # Count the number of times the job completed as expected.
        reproduce_successes = len([m for m in matches if m == 1])
        # Reproduce attempts excludes 'N' match types.
        reproduce_attempts = len([m for m in matches if str(m).isdigit()])
        assert reproduce_successes <= reproduce_attempts
        return reproduce_successes, reproduce_attempts, '{}/{}'.format(reproduce_successes, reproduce_attempts)

    @staticmethod
    def _artifact_is_git_repo(build):
        """
        Returns True if the build is resettable, in which case the artifact will be a git repository.
        """
        return build['resettable']

    @staticmethod
    def _insert_artifact(artifact):
        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        resp = bugswarmapi.insert_artifact(artifact)
        if not resp:
            log.error('Could not insert artifact.')
        return resp.ok

    @staticmethod
    def _update_artifact(image_tag, artifact):
        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        resp = bugswarmapi.patch_artifact(image_tag, artifact)
        if not resp:
            log.error('Could not update artifact.')
        return resp.ok

    @staticmethod
    def _is_artifact_in_db(image_tag):
        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        return bugswarmapi.find_artifact(image_tag, error_if_not_found=False).ok


def _print_usage():
    log.info('Usage: python3 packager.py -i <input_file> [--csv]')


def _validate_input(argv):
    shortopts = 'i:c'
    longopts = 'csv'.split()
    input_file = None
    csv_mode = False
    try:
        optlist, args = getopt.getopt(argv[1:], shortopts, longopts)
    except getopt.GetoptError:
        log.error('Could not parse arguments. Exiting.')
        _print_usage()
        sys.exit(2)

    for opt, arg in optlist:
        if opt in ['-i']:
            input_file = arg
        if opt in ['-c', '--csv']:
            csv_mode = True

    if not input_file:
        _print_usage()
        sys.exit(1)
    if not os.path.isfile(input_file):
        log.error('The input_file argument ({}) is not a file or does not exist. Exiting.'.format(input_file))
        sys.exit(1)
    return input_file, csv_mode


def main(argv=None):
    argv = argv or sys.argv

    # Configure logging.
    log.config_logging(getattr(logging, 'INFO', None))

    # Log the current version of this BugSwarm component.
    log.info(get_current_component_version_message('MetadataPackager'))

    # Decrease logging severity from the requests library.
    logging.getLogger('requests').setLevel(logging.WARNING)

    input_file, csv_mode = _validate_input(argv)
    Packager(input_file, csv_mode).run()


if __name__ == '__main__':
    sys.exit(main())
