import argparse
import json
import logging
import os
import os.path
import sys
import threading
from concurrent.futures import ProcessPoolExecutor, wait
from typing import List

from bugswarm.common import log
from bugswarm.common.log_downloader import download_log
from bugswarm.common.utils import get_current_component_version_message
from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.json import read_json
from bugswarm.common.json import write_json
from pair_classifier.classify_bugs import classify_build, classify_code, classify_test, process_error, process_logs
from get_changed_files import get_github_url, gather_info
from bugswarm.analyzer.analyzer import Analyzer


class PairClassifier(object):

    @staticmethod
    def load_buildpairs(dir_of_jsons: str, filename: str):
        """
        :param dir_of_jsons: A directory containing JSON files of build pairs.
        :param filename: the name of json file
        :raises json.decoder.JSONDecodeError: When the passed directory contains JSON files with invalid JSON.
        """
        all_buildpairs = []
        # Iterate over files that we expect to contain JSON.
        try:
            data = read_json(os.path.join(dir_of_jsons, filename))
        except json.decoder.JSONDecodeError:
            log.error('{} contains invalid JSON.'.format(filename))
            raise

        all_buildpairs.extend(data)
        if not data:
            log.warning('{} does not contain any build pairs.'.format(filename))
        log.info('Read {} build pairs from {}.'.format(len(all_buildpairs), filename))
        return all_buildpairs

    @staticmethod
    def _insert_buildpairs(repo: str, buildpairs: List):
        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        if not bugswarmapi.replace_mined_build_pairs_for_repo(repo, buildpairs):
            log.error('Could not replace filtered build pairs for {}. Exiting.'.format(repo))
            raise RuntimeError

    @staticmethod
    def _save_output(repo: str, output_pairs: list):
        task_name = repo.replace('/', '-')
        os.makedirs(os.path.dirname('output/'), exist_ok=True)
        output_path = 'output/{}.json'.format(task_name)
        log.info('Saving output to', output_path)
        with open(output_path, 'w+') as f:
            json.dump(output_pairs, f, indent=2)
        log.info('Done writing output file.')

    @staticmethod
    def _get_category_confidence(confidence):
        if not confidence or confidence == 0:
            category_confidence = 'No'
        elif confidence == 1:
            category_confidence = 'Yes'
        else:
            category_confidence = 'Partial'
        return category_confidence

    @staticmethod
    def _dl_log_if_not_present(ci_service, repo, job_id, log_dir):
        os.makedirs(os.path.dirname(log_dir), exist_ok=True)
        log_path = os.path.join(log_dir, '{}-orig.log'.format(job_id))

        if os.path.exists(log_path):
            return True
        if ci_service == 'travis' and download_log(job_id, log_path):
            return True
        if ci_service == 'github' and download_log(job_id, log_path, repo=repo):
            return True

        return False

    @staticmethod
    def run(repo: str, dir_of_jsons: str, args: dict):
        threading.current_thread().name = '[{}]'.format(repo)

        task_name = repo.replace('/', '-')
        analyzer = Analyzer()
        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)

        try:
            buildpairs = PairClassifier.load_buildpairs(dir_of_jsons, '{}.json'.format(task_name))
        except json.decoder.JSONDecodeError:
            log.error('{} contains invalid JSON. Exiting.'.format(dir_of_jsons))
            raise RuntimeError

        for bp in buildpairs:
            bp_id = bp['_id']
            ci_service = bp['ci_service'] if 'ci_service' in bp else 'travis'

            if bp['jobpairs']:
                if all((jp['is_filtered'] for jp in bp['jobpairs'])):
                    continue

                failed_sha = bp['failed_build']['travis_merge_sha'] if bp['failed_build']['travis_merge_sha'] else \
                    bp['failed_build']['head_sha']
                passed_sha = bp['passed_build']['travis_merge_sha'] if bp['passed_build']['travis_merge_sha'] else \
                    bp['passed_build']['head_sha']
                url = get_github_url(failed_sha, passed_sha, repo)
                image_tag_info = gather_info(url)

                files_changed = image_tag_info['changed_paths']

                for jp in bp['jobpairs']:
                    if jp['is_filtered']:
                        continue

                    jp.setdefault('build_system', 'NA')
                    jp['metrics'] = image_tag_info['metrics']

                    failed_job_id = jp['failed_job']['job_id']
                    passed_job_id = jp['passed_job']['job_id']

                    file_list = ['{}-orig.log'.format(failed_job_id), '{}-orig.log'.format(passed_job_id)]

                    origin_log_dir = args.get('log_path')

                    # origin_log_dir is not provided, then download the log
                    if origin_log_dir is None:
                        origin_log_dir = 'original-logs/'
                        if not PairClassifier._dl_log_if_not_present(ci_service, repo, failed_job_id, origin_log_dir):
                            log.error('Error: log cannot be downloaded for', failed_job_id)
                            continue
                        if not PairClassifier._dl_log_if_not_present(ci_service, repo, passed_job_id, origin_log_dir):
                            log.error('Error: log cannot be downloaded for', passed_job_id)
                            continue

                    failed_log = process_logs(origin_log_dir, file_list, ci_service)
                    if failed_log is None:
                        log.error('Error processing logs for job pair ({}, {}). Skipping.'.format(
                            failed_job_id, passed_job_id))
                        continue
                    try:
                        language = bp['failed_build']['jobs'][0]['language']
                    except KeyError:
                        log.info('Language not detected')
                        continue
                    if language not in ['python', 'java']:
                        log.info('Lang is :{}'.format(language))
                        continue

                    # CLASSIFICATION
                    files_modified = []
                    files_modified.extend(files_changed)
                    files_modified = list(filter(lambda x: '.git' not in x, files_modified))
                    is_test, test_confidence, remain_files = classify_test(files_modified)
                    is_build, build_confidence, remain_files = classify_build(remain_files, files_modified)
                    is_code, code_confidence = classify_code(remain_files, files_modified)
                    error_dict, userdefined, _ = process_error(language, failed_log)
                    if error_dict == -1:
                        log.error(
                            'Error finding error dict for job pair ({}, {}). Skipping.'.format(
                                failed_job_id, passed_job_id))
                        continue

                    test_confidence = PairClassifier._get_category_confidence(test_confidence)
                    build_confidence = PairClassifier._get_category_confidence(build_confidence)
                    code_confidence = PairClassifier._get_category_confidence(code_confidence)

                    # default to be -1
                    num_tests_failed = -1

                    try:
                        result = analyzer.analyze_single_log('{}/{}-orig.log'.format(origin_log_dir, failed_job_id),
                                                             failed_job_id, ci_service, trigger_sha=failed_sha,
                                                             repo=repo)
                    except BaseException:
                        log.error('Error analyzing log for {}'.format(failed_job_id))
                        continue
                    if 'tr_log_num_tests_failed' in result and not result['tr_log_num_tests_failed'] == 'NA':
                        num_tests_failed = result['tr_log_num_tests_failed']

                    classification = {
                        'code': code_confidence,
                        'test': test_confidence,
                        'build': build_confidence,
                        'exceptions': list(error_dict.keys()),
                        'tr_log_num_tests_failed': num_tests_failed}
                    jp['classification'] = classification

            log.info('patching job pairs to the database.')
            resp = bugswarmapi.patch_job_pairs(bp_id, bp['jobpairs'])
            if not resp.ok:
                log.error(resp)

        log.info('Finished classification.')
        log.info('Writing build pairs to the database.')
        log.info('Saving classified json.')
        PairClassifier._save_output(repo, buildpairs)
        log.info('Finished')


def generate_build_pair_json(repo, orig_file=None):
    log.info('Getting build_pair from Database')
    dir_of_jsons = 'input/'
    task_name = repo.replace('/', '-')
    bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
    buildpairs = bugswarmapi.filter_mined_build_pairs_for_repo(repo)
    if orig_file is not None:
        log.info('Filtering build pairs using local file', orig_file)
        with open(orig_file) as f:
            local_bps = json.load(f)
        # We use orig_file as a filter (instead of just copying it to dir_of_jsons) because we need the `_id`
        # attribute to patch our results to the database, and the json in orig_file does not have that attribute.
        bp_filter = [_build_pair_id_tuple(bp) for bp in local_bps]
        buildpairs = [bp for bp in buildpairs if _build_pair_id_tuple(bp) in bp_filter]
    os.makedirs(os.path.dirname(dir_of_jsons), exist_ok=True)
    write_json('{}{}.json'.format(dir_of_jsons, task_name), buildpairs)
    return dir_of_jsons


def _build_pair_id_tuple(bp):
    return (bp['failed_build']['build_id'], bp['passed_build']['build_id'])


def _validate_input():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-r', '--repo', help='The repo slug of the repo to classify.')
    group.add_argument('-f', '--file', '--repo-file', help='A file containing a list of repo slugs.')
    parser.add_argument('--log-path', help='Directory containing original job logs.')
    parser.add_argument('-p', '--pipeline', action='store_true', help='Run in pipeline mode.')
    parser.add_argument('-w', '--workers', default=1, type=int, help='Number of worker processes to spawn.')

    args = parser.parse_args()

    repo_list = list()

    if args.repo is not None:
        repo_list.append(args.repo)
    else:
        with open(args.file) as file:
            for line in file:
                repo_list.append(line.rstrip())

    if args.log_path is not None and not os.path.isdir(args.log_path):
        parser.error('--log-path "{}" is not a directory or does not exist.'.format(args.log_path))

    if args.workers <= 0:
        parser.error('--workers must be at least 1.')

    return repo_list, args


def main():
    log.config_logging(getattr(logging, 'INFO', None), show_thread_name=True)
    threading.current_thread().name = '[main]'

    # Log the current version of this BugSwarm component.
    log.info(get_current_component_version_message('Classifier'))

    repo_list, args = _validate_input()
    filter_output_dir = os.path.join(os.path.dirname(__file__), '../pair-filter/output-json/')

    if args.pipeline and not os.path.exists(filter_output_dir):
        log.error('pipeline == true, but output_file_path ({}) does not exist. '
                  'Exiting PairClassifier.'.format(filter_output_dir))
        return

    for repo in list(repo_list):
        if args.pipeline:
            task_name = repo.replace('/', '-')
            json_path = os.path.join(filter_output_dir, task_name + '.json')
            if not os.path.exists(json_path):
                log.error(json_path, 'does not exist. Repo', repo, 'will be skipped.')
                repo_list.remove(repo)
                continue
            # Get the input json from the file generated by pair-filter.
            dir_of_jsons = generate_build_pair_json(repo, json_path)
        else:
            # Get the input json from the DB.
            dir_of_jsons = generate_build_pair_json(repo)

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(PairClassifier.run, repo, dir_of_jsons, vars(args)) for repo in repo_list]
        wait(futures)

        errored_futures = [future for future in futures if future.exception()]
        if errored_futures:
            log.error('{} repo(s) encountered an error. Check the logs for details.'.format(len(errored_futures)))
            return 1


if __name__ == '__main__':
    sys.exit(main())
