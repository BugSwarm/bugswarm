import json
import logging
import os
import sys
from copy import deepcopy
from os import path
from typing import List

from bugswarm.common import filter_reasons as reasons
from bugswarm.common import log
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.json import read_json
from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.utils import get_current_component_version_message

from pair_filter import filters, utils
from pair_filter.constants import (DOCKERHUB_IMAGES_JSON, FILTERED_REASON_KEY,
                                   IGNORED_BUILDPAIR_KEYS, IS_FILTERED_KEY,
                                   OUTPUT_FILE_DIR, PARSED_IMAGE_TAG_KEY)


class PairFilter(object):
    """
    Given input pairs,
    (1st filter) filter down to non-squashed pairs based on the attribute `squashed` in the input JSON.
    (2nd filter) filter down to the pairs in which all jobs used Quay images.
    """

    @staticmethod
    def _set_is_filtered(buildpairs: List):
        for bp in buildpairs:
            for jp in bp['jobpairs']:
                jp[IS_FILTERED_KEY] = jp[FILTERED_REASON_KEY] is not None

    # Set attribute defaults.
    @staticmethod
    def _set_attribute_defaults(buildpairs: List):
        for bp in buildpairs:
            for jp in bp['jobpairs']:
                jp[FILTERED_REASON_KEY] = None
                jobs = [jp['failed_job'], jp['passed_job']]
                for j in jobs:
                    j[PARSED_IMAGE_TAG_KEY] = None

    @staticmethod
    def _insert_buildpairs(repo: str, buildpairs: List):
        buildpairs = deepcopy(buildpairs)

        for bp in buildpairs:
            for key in IGNORED_BUILDPAIR_KEYS:
                parts = key.split('.')
                target = bp
                try:
                    for part in parts[:-1]:
                        target = target[part]
                    del target[parts[-1]]
                except KeyError:
                    continue

        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        if not bugswarmapi.bulk_insert_mined_build_pairs(buildpairs):
            log.error('Could not bulk insert mined build pairs for {}. Exiting.'.format(repo))
            sys.exit(1)

    @staticmethod
    def _save_to_file(repo: str, output_dir: str, output_pairs: list):
        task_name = repo.replace('/', '-')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, '{}.json'.format(task_name))

        log.info('Saving output to', output_path)
        with open(output_path, 'w+') as f:
            json.dump(output_pairs, f, indent=2)
        log.info('Done writing output file.')

    @staticmethod
    def _update_mined_project(repo: str, ci_service: str, orig_metrics_dir: str, buildpairs: List):
        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        file_name = utils.canonical_repo(repo) + '.json'
        file_path = os.path.join(orig_metrics_dir, file_name)
        original_d = read_json(file_path)

        def _key(filter_name: str, pr: bool):
            return 'filtered{}_{}'.format('_pr' if pr else '', filter_name)

        def _unfiltered_key(pr: bool):
            return 'unfiltered{}'.format('_pr' if pr else '')

        d = {
            'filtered_no_sha': 0,
            'filtered_same_commit': 0,
            'filtered_unavailable': 0,
            'filtered_no_original_log': 0,
            'filtered_error_reading_original_log': 0,
            'filtered_no_image_provision_timestamp': 0,
            'filtered_inaccessible_image': 0,
            'unfiltered': 0,

            'filtered_pr_no_sha': 0,
            'filtered_pr_same_commit': 0,
            'filtered_pr_unavailable': 0,
            'filtered_pr_no_original_log': 0,
            'filtered_pr_error_reading_original_log': 0,
            'filtered_pr_no_image_provision_timestamp': 0,
            'filtered_pr_inaccessible_image': 0,
            'unfiltered_pr': 0,
        }
        for bp in buildpairs:
            is_pr = bp['pr_num'] > 0
            d[_unfiltered_key(is_pr)] += utils.count_unfiltered_jobpairs([bp])
            for jp in bp['jobpairs']:
                reason = jp[FILTERED_REASON_KEY]
                if reason == reasons.NO_HEAD_SHA:
                    d[_key('no_sha', is_pr)] += 1
                elif reason == reasons.SAME_COMMIT_PAIR:
                    d[_key('same_commit', is_pr)] += 1
                elif reason == reasons.NOT_AVAILABLE:
                    d[_key('unavailable', is_pr)] += 1
                elif reason == reasons.NO_ORIGINAL_LOG:
                    d[_key('no_original_log', is_pr)] += 1
                elif reason == reasons.ERROR_READING_ORIGINAL_LOG:
                    d[_key('error_reading_original_log', is_pr)] += 1
                elif reason == reasons.NO_IMAGE_PROVISION_TIMESTAMP:
                    d[_key('no_image_provision_timestamp', is_pr)] += 1
                elif reason == reasons.INACCESSIBLE_IMAGE:
                    d[_key('inaccessible_image', is_pr)] += 1
        for metric_name, metric_value in d.items():
            try:
                metric_value = metric_value + original_d['progression_metrics'][metric_name]
            except KeyError:
                pass
            if not bugswarmapi.set_mined_project_progression_metric(repo, ci_service, metric_name, metric_value):
                log.error('Encountered an error while setting a progression metric. Exiting.')
                sys.exit(1)

    @staticmethod
    def run(repo: str, ci_service: str, dir_of_jsons: str):
        utils.create_dirs()

        try:
            buildpairs = utils.load_buildpairs(dir_of_jsons, repo)
        except json.decoder.JSONDecodeError:
            log.error('At least one JSON file in {} contains invalid JSON. Exiting.'.format(dir_of_jsons))
            sys.exit(1)

        if not buildpairs:
            return None

        log.info('Filtering. Starting with', utils.count_jobpairs(buildpairs), 'jobpairs.')

        PairFilter._set_attribute_defaults(buildpairs)

        # Apply the filters.
        filters.filter_no_sha(buildpairs)
        filters.filter_same_commit(buildpairs)
        filters.filter_unavailable(buildpairs)
        filters.filter_unresettable_with_submodules(buildpairs)

        if ci_service == 'github':
            filters.filter_unavailable_github_runner(buildpairs)
            filters.filter_unredacted_tokens(buildpairs)
            filters.filter_unsupported_workflow(buildpairs)
            filters.filter_expired_logs(buildpairs)
        elif ci_service == 'travis':
            filters.filter_non_exact_images(buildpairs)
        log.info('Finished filtering.')

        PairFilter._set_is_filtered(buildpairs)
        log.info('Writing output to output_json')
        PairFilter._save_to_file(repo, OUTPUT_FILE_DIR, buildpairs)

        log.info('Writing build pairs to the database.')
        PairFilter._insert_buildpairs(repo, buildpairs)

        log.info('Updating mined project in the database.')
        orig_metrics_dir = os.path.join(dir_of_jsons, '..', 'original_metrics')
        PairFilter._update_mined_project(repo, ci_service, orig_metrics_dir, buildpairs)

        log.info('Done! After filtering,', utils.count_unfiltered_jobpairs(buildpairs), 'jobpairs remain.')


def _print_usage():
    log.info('Usage: python3 pair-filter.py <repo> <ci_service> <dir_of_jsons>')
    log.info('repo:         The GitHub slug for the project whose pairs are being filtered.')
    log.info('ci_service:   The CI service used by the mined project. One of "github" or "travis".')
    log.info('dir_of_jsons: Input directory containing JSON files of pairs. This directory is often be within the '
             'PairFinder output directory.')


def _validate_input(argv):
    if len(argv) != 4:
        _print_usage()
        sys.exit(1)
    repo = argv[1]
    ci_service = argv[2]
    if ci_service not in ['github', 'travis']:
        log.error('The ci_service argument must be one of "github" or "travis". Exiting.')
        _print_usage()
        sys.exit(1)
    dir_of_jsons = argv[3]
    if not os.path.isdir(dir_of_jsons):
        log.error('The dir_of_jsons argument is not a directory or does not exist. Exiting.')
        _print_usage()
        sys.exit(1)
    return repo, ci_service, dir_of_jsons


def main(argv=None):
    argv = argv or sys.argv

    # Configure logging.
    log.config_logging(getattr(logging, 'INFO', None))
    # Log the current version of this BugSwarm component.
    log.info(get_current_component_version_message('PairFilter'))
    if not path.exists(DOCKERHUB_IMAGES_JSON):
        log.info('File dockerhub_image.json not found. Please run gen_image_list.py')

    repo, ci_service, dir_of_jsons = _validate_input(argv)
    PairFilter.run(repo, ci_service, dir_of_jsons)


if __name__ == '__main__':
    sys.exit(main())
