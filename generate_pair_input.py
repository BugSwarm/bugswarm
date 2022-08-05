import getopt
import json
import logging
import os
import sys

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import dateutil.parser
from bugswarm.common import log
from bugswarm.common import utils as bugswarmutils
from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN, GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper
from bugswarm.common.utils import get_diff_stats


class JobPairSelector(object):
    @staticmethod
    def select(buildpairs: List,
               repo: str,
               include_attempted: bool,
               include_archived: bool,
               include_resettable: bool,
               include_only_test_failures: bool,
               include_different_base_image: bool,
               restrict_classified_build: bool,
               restrict_classified_code: bool,
               restrict_classified_test: bool,
               restrict_classified_exclusive: bool,
               restrict_classified_exception: str,
               restrict_build_system: str,
               restrict_os_version: str,
               restrict_diff_size: str) -> List:
        """
        Select job pairs from `buildpairs`. The `include_*` parameters are used to decide which job pairs to include.

        :param buildpairs: A list of build pairs that were mined from `repo`.
        :param repo: A repository slug.
        :param include_attempted: Whether to include pairs that we have previously atttempted to reproduce
                                  (reproduce_attempts > 0).
        :param include_archived: Whether to include pairs that are archived by GitHub but not resettable.
        :param include_resettable: Whether to include pairs that are resettable.
        :param include_only_test_failures
        :param include_different_base_image: Whether to include pairs that have different base images
        :param restrict_classified_build: bool,
        :param restrict_classified_code: bool,
        :param restrict_classified_test: bool,
        :param restrict_classified_exclusive: bool,
        :param restrict_classified_exception: str,
        :param restrict_build_system: str,
        :param restrict_os_version: str,
        :param restrict_diff_size: str,
        :return: A list of job pairs.
        """
        final = set()
        archived_only, resettable, attempted, filtered, test_failures_only, classified_build_only, \
            classified_code_only, classified_test_only, classified_exception_only, build_system, os_version, \
            different_base_image \
            = JobPairSelector._bin_jobpairs(repo, buildpairs, include_only_test_failures,
                                            restrict_classified_exception, restrict_build_system,
                                            restrict_os_version)

        if include_archived:
            # Include archived-only job pairs.
            final = final.union(archived_only)
        if include_resettable:
            # Include resettable job pairs.
            final = final.union(resettable)
        if not include_attempted:
            # Exclude already attempted job pairs.
            final = final.difference(attempted)
        if not include_different_base_image:
            # Exclude job pairs with different base images.
            final = final.difference(different_base_image)
        if include_only_test_failures:
            final = final.intersection(test_failures_only)
        if restrict_classified_build:
            final = final.intersection(classified_build_only)
        if restrict_classified_test:
            final = final.intersection(classified_test_only)
        if restrict_classified_code:
            final = final.intersection(classified_code_only)
        if restrict_classified_exclusive:
            if not restrict_classified_build:
                final = final.difference(classified_build_only)
            if not restrict_classified_test:
                final = final.difference(classified_test_only)
            if not restrict_classified_code:
                final = final.difference(classified_code_only)
        if restrict_classified_exception != '':
            final = final.intersection(classified_exception_only)
        if restrict_build_system != '':
            final = final.intersection(build_system)
        if restrict_os_version != '':
            final = final.intersection(os_version)
        # Always remove filtered job pairs.
        final = final.difference(filtered)

        if restrict_diff_size:
            diff_min, diff_max = map(int, restrict_diff_size.split('~'))
            final = JobPairSelector._filter_diff_size(final, diff_min, diff_max)

        jobpairs = [JobPairSelector._str2jp(jp) for jp in final]
        return jobpairs

    @staticmethod
    def _filter_diff_size(final, diff_min, diff_max):
        git_wrapper = GitHubWrapper(GITHUB_TOKENS)
        result = set()
        for pair_str in final:
            pair = json.loads(pair_str)
            failed_sha = pair['failed_job']['travis_merge_sha']
            passed_sha = pair['passed_job']['travis_merge_sha']
            repo = pair['repo']
            _, _, changes = get_diff_stats(repo, failed_sha, passed_sha, git_wrapper)
            if changes and diff_min <= changes <= diff_max:
                result.add(pair_str)
        return result

    @staticmethod
    def _bin_jobpairs(repo,
                      buildpairs,
                      include_only_test_failures,
                      restrict_classified_exception,
                      restrict_build_system,
                      restrict_os_version) -> Tuple[Set, Set, Set, Set, Set, Set, Set, Set, Set, Set, Set, Set]:

        archived_only = set()
        resettable = set()
        attempted = set()
        filtered = set()
        test_failures_only = set()
        classified_build_only = set()
        classified_code_only = set()
        classified_test_only = set()
        classified_exception_only = set()
        build_system = set()
        os_version = set()
        different_base_image = set()
        start_time = end_time = None
        if restrict_os_version == '12.04':
            start_time = dateutil.parser.parse('2014-12-01T00:00:00Z').replace(tzinfo=None)
            end_time = dateutil.parser.parse('2017-09-30T23:59:59Z').replace(tzinfo=None)
        elif restrict_os_version == '14.04':
            start_time = dateutil.parser.parse('2017-07-01T00:00:00Z').replace(tzinfo=None)
            end_time = dateutil.parser.parse('2018-12-31T23:59:59Z').replace(tzinfo=None)
        elif restrict_os_version == '16.04':
            start_time = dateutil.parser.parse('2018-12-01T00:00:00Z').replace(tzinfo=None)
            end_time = dateutil.parser.parse('2999-09-30T12:59:59Z').replace(tzinfo=None)

        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        attempted_result = bugswarmapi.filter_artifacts(
            '{{"repo": "{}", "reproduce_attempts": {{"$gt": 0}}}}'.format(repo))
        attempted_image_tags = list(map(lambda a: a['image_tag'], attempted_result))
        for bp in buildpairs:
            for jp in bp['jobpairs']:
                jp['repo'] = bp['repo']
                jp['failed_job']['travis_merge_sha'] = bp['failed_build']['travis_merge_sha'] if bp['failed_build'][
                    'travis_merge_sha'] else bp['failed_build']['head_sha']
                jp['passed_job']['travis_merge_sha'] = bp['passed_build']['travis_merge_sha'] if bp['passed_build'][
                    'travis_merge_sha'] else bp['passed_build']['head_sha']
                s = JobPairSelector._jp2str(jp)
                if (
                        (bp['failed_build']['github_archived'] and not bp['failed_build']['resettable']) or
                        (bp['passed_build']['github_archived'] and not bp['passed_build']['resettable'])
                ):
                    archived_only.add(s)
                if bp['failed_build']['resettable'] and bp['passed_build']['resettable']:
                    resettable.add(s)
                if jp['failed_job']['heuristically_parsed_image_tag'] != jp['passed_job'][
                        'heuristically_parsed_image_tag']:
                    different_base_image.add(s)
                image_tag = bugswarmutils.get_image_tag(repo, jp['failed_job']['job_id'])
                if image_tag in attempted_image_tags:
                    attempted.add(s)
                if jp['is_filtered']:
                    filtered.add(s)
                if not jp['is_filtered']:
                    try:
                        classification_dict = jp['classification']
                        if classification_dict['build'] != 'No':
                            classified_build_only.add(s)
                        if classification_dict['code'] != 'No':
                            classified_code_only.add(s)
                        if classification_dict['test'] != 'No':
                            classified_test_only.add(s)
                        if restrict_classified_exception in classification_dict['exceptions']:
                            classified_exception_only.add(s)
                        if include_only_test_failures:
                            if jp['classification']['tr_log_num_tests_failed'] > 0:
                                test_failures_only.add(s)
                    except KeyError:
                        log.info('{} does not have classification.'.format(image_tag))
                try:
                    if jp['build_system'] == restrict_build_system:
                        build_system.add(s)
                except KeyError:
                    log.info('{} does not have build system info'.format(image_tag))

                if restrict_os_version != '':
                    if bp['failed_build']['committed_at'] is not None:
                        time_stamp = dateutil.parser.parse(bp['failed_build']['committed_at']).replace(tzinfo=None)
                        if start_time < time_stamp < end_time:
                            os_version.add(s)

        return \
            archived_only, resettable, attempted, filtered, test_failures_only, classified_build_only, \
            classified_code_only, classified_test_only, classified_exception_only, build_system, os_version, \
            different_base_image

    @staticmethod
    def _jp2str(jp) -> str:
        return json.dumps(jp, sort_keys=True)

    @staticmethod
    def _str2jp(s):
        return json.loads(s)


def main(argv=None):
    argv = argv or sys.argv

    # Configure logging.
    log.config_logging(getattr(logging, 'INFO', None))

    repo_list, output_path, include_attempted, include_archived_only, include_resettable, include_test_failures_only, \
        include_different_base_image, restrict_classified_build, restrict_classified_code, restrict_classified_test, \
        restrict_classified_exclusive, restrict_classified_exception, restrict_build_system, restrict_os_version, \
        restrict_diff_size = \
        _validate_input(argv)

    # create tmp folder to store logs
    os.makedirs('tmp/', exist_ok=True)

    # Returns '1 project' or 'n projects' where n is not 1.

    def _pluralize(n: int):
        s = '{} '.format(n)
        return s + 'project' if n == 1 else s + 'projects'

    # Returns 'Including' if the parameter is truthy and 'Excluding' otherwise.
    def _including_or_excluding(include: bool):
        return 'Including' if include else 'Excluding'

    # Print some context for the upcoming operation.
    log.info('Choosing pairs from {}.'.format(_pluralize(len(repo_list))))
    log.info('{} pairs with at least one reproduce attempt.'.format(_including_or_excluding(include_attempted)))
    log.info('{} pairs that are only archived by GitHub.'.format(_including_or_excluding(include_archived_only)))
    log.info('{} pairs that are resettable.'.format(_including_or_excluding(include_resettable)))
    log.info('{} pairs that have different base images'.format(_including_or_excluding(include_different_base_image)))
    log.info('Excluding pairs that were filtered by PairFilter.')
    if include_test_failures_only:
        log.info('Restricted to test_failures')
    if restrict_classified_build:
        log.info('Restricted to classified build')
    if restrict_classified_test:
        log.info('Restricted to classified test')
    if restrict_classified_code:
        log.info('Restricted to classified code')
    if restrict_classified_exclusive:
        log.info('Restricted to exclusively classified build/test/code')
    if restrict_classified_exception != '':
        log.info('Restricted to classified exception: {}'.format(restrict_classified_exception))
    if restrict_build_system != '':
        log.info('Restricted to build system: {}'.format(restrict_build_system))
    if restrict_os_version != '':
        log.info('Restricted OS version to: {}'.format(restrict_os_version))
    if restrict_diff_size != '':
        log.info('Restricted diff size: {}'.format(restrict_diff_size))
    log.info()

    with ThreadPoolExecutor(max_workers=min(len(repo_list), 64)) as executor:
        future_to_repo = {executor.submit(_choose_pairs_from_repo,
                                          repo,
                                          include_attempted,
                                          include_archived_only,
                                          include_resettable,
                                          include_test_failures_only,
                                          include_different_base_image,
                                          restrict_classified_build,
                                          restrict_classified_code,
                                          restrict_classified_test,
                                          restrict_classified_exclusive,
                                          restrict_classified_exception,
                                          restrict_build_system,
                                          restrict_os_version,
                                          restrict_diff_size): repo for repo in repo_list}

    errored = 0
    all_lines = []
    skipped_repos = []
    for future in as_completed(future_to_repo):
        try:
            lines, skipped_repo = future.result()
        except Exception:
            errored += 1
            raise
        all_lines += lines
        if skipped_repo:
            skipped_repos.append(skipped_repo)

    # Create any missing path components to the output file.
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Sort the lines and then append a newline to each line.
    all_lines = list(map(lambda l: l + '\n', sorted(all_lines)))
    # Write the output file.
    with open(output_path, 'w') as f:
        f.writelines(all_lines)

    # Print some context for the result of the operation.
    log.info()
    log.info('Attempted to choose pairs from {}.'.format(_pluralize(len(repo_list))))
    log.info('{} resulted in an error.'.format(_pluralize(errored)))
    if len(skipped_repos):
        log.info('{} were skipped because they have not been mined:'.format(_pluralize(len(skipped_repos))))
        for r in skipped_repos:
            log.info('    {}'.format(r))
    else:
        log.info('0 projects were skipped because they have not been mined.')
    log.info('Wrote {} lines to {}.'.format(len(all_lines), output_path))
    log.info('Done!')


def _choose_pairs_from_repo(repo: str,
                            include_attempted: bool,
                            include_archived: bool,
                            include_resettable: bool,
                            include_only_test_failures: bool,
                            include_different_base_image: bool,
                            restrict_classified_build: bool,
                            restrict_classified_code: bool,
                            restrict_classified_test: bool,
                            restrict_classified_exclusive: bool,
                            restrict_classified_exception: str,
                            build_system: str,
                            restrict_os_version: str,
                            restrict_diff_size: str) -> Tuple[List, Optional[str]]:
    """
    Returns a 2-tuple. The first element is a list of job pairs. The second element is a repository slug if the project
    was skipped or None.
    """
    log.info('Choosing pairs from {}.'.format(repo))
    bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
    if (not bugswarmapi.find_mined_project(repo, 'travis', error_if_not_found=False) and
            not bugswarmapi.find_mined_project(repo, 'github', error_if_not_found=False)):
        log.error('It seems that {} has not yet been mined. Skipping.'.format(repo))
        return [], repo

    buildpairs = bugswarmapi.filter_mined_build_pairs_for_repo(repo)
    log.info('Read {} unfiltered job pairs for {}.'.format(_count_unfiltered_jobpairs(buildpairs), repo))

    jobpairs = JobPairSelector.select(buildpairs, repo, include_attempted, include_archived, include_resettable,
                                      include_only_test_failures, include_different_base_image,
                                      restrict_classified_build, restrict_classified_code, restrict_classified_test,
                                      restrict_classified_exclusive,
                                      restrict_classified_exception, build_system, restrict_os_version,
                                      restrict_diff_size)
    lines = []
    for jp in jobpairs:
        failed_job_id = jp['failed_job']['job_id']
        passed_job_id = jp['passed_job']['job_id']
        lines.append('{},{},{}'.format(repo, failed_job_id, passed_job_id))
    return lines, None


def _count_unfiltered_jobpairs(buildpairs) -> int:
    return sum([len([jp for jp in bp['jobpairs'] if not jp['is_filtered']]) for bp in buildpairs])


def _jobpair_satisfies_filters(jp, failed_job_id, passed_job_id):
    """
    Not currently used.
    True if the jobpair meets the filters indicated by the presence of the -p and -f arguments.
    """
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
    short_opts = 'r:o:'
    long_opts = 'repo= repo-file= output-path= include-attempted include-archived-only include-resettable ' \
                'include-test-failures-only include-different-base-image classified-build classified-code ' \
                'classified-test exclusive-classify classified-exception= build-system= os-version= diff-size='.split()

    try:
        optlist, args = getopt.getopt(argv[1:], short_opts, long_opts)
    except getopt.GetoptError as err:
        _print_usage(msg=err.msg)
        sys.exit(2)

    repo = None
    repo_file_path = None
    output_path = None
    include_attempted = False
    include_archived_only = False
    include_resettable = False
    include_test_failures_only = False
    include_different_base_image = False
    restrict_classified_build = False
    restrict_classified_code = False
    restrict_classified_test = False
    restrict_classified_exclusive = False
    restrict_classified_exception = ''
    restrict_build_system = ''
    restrict_os_version = ''
    restrict_diff_size = ''

    for opt, arg in optlist:
        if opt in ('-r', '--repo'):
            repo = arg
        if opt == '--repo-file':
            repo_file_path = arg
        if opt in ('-o', '--output-path'):
            output_path = os.path.abspath(arg)
        if opt == '--include-attempted':
            include_attempted = True
        if opt == '--include-archived-only':
            include_archived_only = True
        if opt == '--include-resettable':
            include_resettable = True
        if opt == '--include-test-failures-only':
            include_test_failures_only = True
        if opt == '--include-different-base-image':
            include_different_base_image = True
        if opt == '--classified-build':
            restrict_classified_build = True
        if opt == '--classified-code':
            restrict_classified_code = True
        if opt == '--classified-test':
            restrict_classified_test = True
        if opt == '--exclusive-classify':
            restrict_classified_exclusive = True
        if opt == '--classified-exception':
            restrict_classified_exception = arg
            if arg is None:
                _print_usage(msg='Missing exception argument. Exiting.')
                sys.exit(2)
        if opt == '--build-system':
            restrict_build_system = arg
        if opt == '--os-version':
            restrict_os_version = arg
        if opt == '--diff-size':
            if not arg or '~' not in arg or len(arg.split('~')) != 2:
                _print_usage(msg='Diff size argument should be MIN~MAX. Exiting.')
                sys.exit(2)
            restrict_diff_size = arg

    if repo and repo_file_path:
        _print_usage(msg='The --repo and --repo-file arguments are mutually exclusive.')
        sys.exit(2)
    elif repo:
        repo_list = [repo]
    elif repo_file_path:
        with open(repo_file_path) as f:
            # Create a sorted list of unique lines after stripping lines and filtering empty lines.
            repo_list = sorted(list(set(filter(None, map(str.strip, f.readlines())))))
    else:
        _print_usage(msg='Exactly one of the --repo and --repo-file arguments is required.')
        sys.exit(2)

    if not output_path:
        _print_usage(msg='Missing output file argument. Exiting.')
        sys.exit(2)

    return \
        repo_list, output_path, include_attempted, include_archived_only, include_resettable, \
        include_test_failures_only, include_different_base_image, restrict_classified_build, restrict_classified_code, \
        restrict_classified_test, restrict_classified_exclusive, restrict_classified_exception, restrict_build_system, \
        restrict_os_version, restrict_diff_size


def _print_usage(msg=None):
    if msg:
        log.info(msg)
    log.info('Usage: python3 generate_pair_input.py OPTIONS')
    log.info('Options:')
    log.info('{:>6}, {:<31}{}'.format('-r', '--repo', 'Repo slug for the mined project from which to choose pairs. '
                                                      'Cannot be used with --repo-file.'))
    log.info('{:>6}  {:<31}{}'.format('', '--repo-file', 'Path to file containing a newline-separated list of repo '
                                                         'slugs for the mined projects from which to choose pairs. '
                                                         'Cannot be used with --repo.'))
    log.info('{:>6}, {:<31}{}'.format('-o', '--output-path', 'Path to the file where chosen pairs will be written.'))
    log.info('{:>6}  {:<31}{}'.format('', '--include-attempted', 'Include job pairs in the artifact database '
                                                                 'collection that we have already attempted to '
                                                                 'reproduce. Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--include-archived-only', 'Include job pairs in the artifact database '
                                                                     'collection that are marked as archived by '
                                                                     'GitHub but not resettable. Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--include-resettable', 'Include job pairs in the artifact database '
                                                                  'collection that are marked as resettable. Defaults '
                                                                  'to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--include-test-failures-only', 'Include job pairs that have a test failure '
                                                                          'according to the Analyzer. Defaults to '
                                                                          'false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--include-different-base-image', 'Include job pairs that passed and failed '
                                                                            'job have different base images. Defaults '
                                                                            'to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--classified-build', 'Restrict job pairs that have been classified as build '
                                                                'according to classifier Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--classified-code', 'Restrict job pairs that have been classified as code '
                                                               'according to classifier Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--classified-test', 'Restrict job pairs that have been classified as test '
                                                               'according to classifier Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--exclusive-classify', 'Restrict to job pairs that have been exclusively '
                                                                  'classified as build/code/test, as specified by '
                                                                  'their respective options. Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--classified-exception', 'Restrict job pairs that have been classified as '
                                                                    'contain certain exception'))
    log.info('{:>6}  {:<31}{}'.format('', '--build-system', 'Restricted to certain build system'))
    log.info('{:>6}  {:<31}{}'.format('', '--os-version', 'Restricted to certain OS version(e.g. 12.04, 14.04, 16.04)'))
    log.info('{:>6}  {:<31}{}'.format('', '--diff-size', 'Restricted to certain diff size MIN~MAX(e.g. 0~5)'))


if __name__ == '__main__':
    sys.exit(main())
