import getopt
import json
import logging
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple

import dateutil.parser
from bugswarm.common import log
from bugswarm.common import utils as bugswarmutils
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN, GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper
from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.unsupported_actions import SKIPPED_ACTIONS, SPECIAL_ACTIONS, UNSUPPORTED_ACTIONS
from bugswarm.common.utils import get_diff_stats


@dataclass
class Options:
    include_attempted: bool = False
    include_archived: bool = False
    include_resettable: bool = False
    include_only_test_failures: bool = False
    include_only_compile_failures: bool = False
    include_different_base_image: bool = False
    restrict_classified_build: bool = False
    restrict_classified_code: bool = False
    restrict_classified_test: bool = False
    exclude_classified_build: bool = False
    exclude_classified_code: bool = False
    exclude_classified_test: bool = False
    restrict_classified_exclusive: bool = False
    restrict_classified_exception: str = ''
    restrict_build_system: str = ''
    restrict_os_version: str = ''
    restrict_diff_size: str = ''
    restrict_ci_service: str = ''
    restrict_valid_failed_step: bool = True
    restrict_custom_failed_step: bool = False
    restrict_earliest_mine_date: datetime = None
    restrict_language: str = ''
    restrict_max_runtime: int = None
    restrict_non_docker: bool = False


class JobPairSelector(object):
    @staticmethod
    def select(buildpairs: List, repo: str, opts: Options) -> List:
        """
        Select job pairs from `buildpairs` using the specified filters.

        :param buildpairs: A list of build pairs that were mined from `repo`.
        :param repo: A repository slug.
        :param opts: An `Options` object containing the filters to select by.
        :return: A list of job pairs.
        """
        final = set()
        (archived_only, resettable, attempted, filtered, test_failures_only, classified_build_only,
         classified_code_only, classified_test_only, classified_exception_only, build_system, os_version,
         different_base_image, ci_service, valid_failed_step_only, custom_failed_step_only, within_time_range,
         failed_compile_step_only, has_target_language, within_max_runtime, non_docker, within_diff_size
         ) = JobPairSelector._bin_jobpairs(repo, buildpairs, opts)

        if opts.include_archived:
            # Include archived-only job pairs.
            final = final.union(archived_only)
        if opts.include_resettable:
            # Include resettable job pairs.
            final = final.union(resettable)
        if not opts.include_attempted:
            # Exclude already attempted job pairs.
            final = final.difference(attempted)
        if not opts.include_different_base_image:
            # Exclude job pairs with different base images.
            final = final.difference(different_base_image)
        if opts.include_only_test_failures:
            final = final.intersection(test_failures_only)
        if opts.restrict_classified_build:
            final = final.intersection(classified_build_only)
        if opts.restrict_classified_test:
            final = final.intersection(classified_test_only)
        if opts.restrict_classified_code:
            final = final.intersection(classified_code_only)
        if opts.exclude_classified_build:
            final = final.difference(classified_build_only)
        if opts.exclude_classified_test:
            final = final.difference(classified_test_only)
        if opts.exclude_classified_code:
            final = final.difference(classified_code_only)
        if opts.restrict_classified_exclusive:
            if not opts.restrict_classified_build:
                final = final.difference(classified_build_only)
            if not opts.restrict_classified_test:
                final = final.difference(classified_test_only)
            if not opts.restrict_classified_code:
                final = final.difference(classified_code_only)
        if opts.restrict_classified_exception != '':
            final = final.intersection(classified_exception_only)
        if opts.restrict_build_system != '':
            final = final.intersection(build_system)
        if opts.restrict_os_version != '':
            final = final.intersection(os_version)
        if opts.restrict_ci_service != '':
            final = final.intersection(ci_service)
        if opts.restrict_valid_failed_step:
            final = final.intersection(valid_failed_step_only)
        if opts.restrict_custom_failed_step:
            final = final.intersection(custom_failed_step_only)
        if opts.restrict_earliest_mine_date:
            final = final.intersection(within_time_range)
        if opts.include_only_compile_failures:
            final = final.intersection(failed_compile_step_only)
        if opts.restrict_language:
            final = final.intersection(has_target_language)
        if opts.restrict_max_runtime:
            final = final.intersection(within_max_runtime)
        if opts.restrict_non_docker:
            final = final.intersection(non_docker)
        if opts.restrict_diff_size:
            final = final.intersection(within_diff_size)
        # Always remove filtered job pairs.
        final = final.difference(filtered)

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
    def _bin_jobpairs(repo, buildpairs, opts: Options) -> Tuple[Set, ...]:
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
        ci_service = set()
        valid_failed_step_only = set()
        custom_failed_step_only = set()
        within_time_range = set()
        failed_compile_step_only = set()
        has_target_language = set()
        within_max_runtime = set()
        non_docker = set()
        within_diff_size = set()

        start_time = end_time = None
        if opts.restrict_os_version == '12.04':
            start_time = dateutil.parser.parse('2014-12-01T00:00:00Z').replace(tzinfo=None)
            end_time = dateutil.parser.parse('2017-09-30T23:59:59Z').replace(tzinfo=None)
        elif opts.restrict_os_version == '14.04':
            start_time = dateutil.parser.parse('2017-07-01T00:00:00Z').replace(tzinfo=None)
            end_time = dateutil.parser.parse('2018-12-31T23:59:59Z').replace(tzinfo=None)
        elif opts.restrict_os_version == '16.04':
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

                failed_job = next(job for job in bp['failed_build']['jobs']
                                  if job['job_id'] == jp['failed_job']['job_id'])
                passed_job = next(job for job in bp['passed_build']['jobs']
                                  if job['job_id'] == jp['passed_job']['job_id'])
                failed_config = failed_job['config']

                s = JobPairSelector._jp2str(jp)
                if (
                        (bp['failed_build']['github_archived'] and not bp['failed_build']['resettable']) or
                        (bp['passed_build']['github_archived'] and not bp['passed_build']['resettable'])
                ):
                    archived_only.add(s)
                if bp['failed_build']['resettable'] and bp['passed_build']['resettable']:
                    resettable.add(s)
                if jp['failed_job'].get('heuristically_parsed_image_tag') != \
                        jp['passed_job'].get('heuristically_parsed_image_tag'):
                    different_base_image.add(s)
                if bp['ci_service'] == opts.restrict_ci_service:
                    ci_service.add(s)

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
                        if opts.restrict_classified_exception in classification_dict['exceptions']:
                            classified_exception_only.add(s)
                        if opts.include_only_test_failures:
                            if jp['classification']['tr_log_num_tests_failed'] > 0:
                                test_failures_only.add(s)
                    except KeyError:
                        log.info('{} does not have classification.'.format(image_tag))
                try:
                    if jp['build_system'] == opts.restrict_build_system:
                        build_system.add(s)
                except KeyError:
                    log.info('{} does not have build system info'.format(image_tag))

                if opts.restrict_os_version != '':
                    if bp['ci_service'] == 'travis' and bp['failed_build']['committed_at'] is not None:
                        time_stamp = dateutil.parser.parse(bp['failed_build']['committed_at']).replace(tzinfo=None)
                        if start_time < time_stamp < end_time:
                            os_version.add(s)
                    elif bp['ci_service'] == 'github' and isinstance(failed_config['runs-on'], str):
                        # PairFinder ensures that config is always the same between jobs in pairs
                        failed_os = failed_config['runs-on']

                        # Handle matrix params
                        # TODO Add the ability to handle more complicated replacements.
                        # According to
                        # https://docs.github.com/en/actions/learn-github-actions/contexts#context-availability,
                        # jobs.<job-id>.runs-on can access the `github`, `needs`, `strategy`,
                        # `matrix`, and `inputs` contexts. This only handles the `matrix` context.
                        failed_os = re.sub(r'\${{\s*matrix\.([^\s}]+)\s*}}',
                                           lambda m: JobPairSelector._replace_matrix_param(m[1], failed_config),
                                           failed_os)

                        if failed_os == 'ubuntu-latest':
                            # https://github.blog/changelog/2022-11-09-github-actions-ubuntu-latest-workflows-will-use-ubuntu-22-04/
                            to_2204 = dateutil.parser.parse('2022-10-01T00:00:00Z').replace(tzinfo=None)
                            time_stamp = dateutil.parser.parse(bp['failed_build']['committed_at']).replace(tzinfo=None)

                            if time_stamp > to_2204:
                                failed_os = 'ubuntu-22.04'
                            else:
                                failed_os = 'ubuntu-20.04'
                        if failed_os == opts.restrict_os_version:
                            os_version.add(s)

                invalids = SKIPPED_ACTIONS | SPECIAL_ACTIONS
                # If the failed step is NOT within the UNSUPPORTED_ACTIONS & SPECIAL_ACTIONS set, marks it as valid.
                try:
                    if jp['failed_step_kind'] != 'uses' or not any(s in jp['failed_step_command'] for s in invalids):
                        valid_failed_step_only.add(s)
                    if jp['failed_step_kind'] == 'run':
                        custom_failed_step_only.add(s)

                    # Matches 'mvn compile' or 'mvn install -DskipTests'
                    # TODO similar searches for other build systems
                    maven_compile_regex = r'(mvn|\./mvnw)( \S*)*' \
                        r'( compile| test-compile| install( \\S*)* -DskipTests(?!=false))'
                    if jp['failed_step_kind'] == 'run' and re.search(maven_compile_regex, jp['failed_step_command']):
                        failed_compile_step_only.add(s)
                except KeyError:
                    log.info('{} does not have failed_step_kind/command.'.format(image_tag))

                mine_date = dateutil.parser.parse(bp['_created'])
                if opts.restrict_earliest_mine_date and mine_date >= opts.restrict_earliest_mine_date:
                    within_time_range.add(s)

                if opts.restrict_language and failed_job['language'].lower() == opts.restrict_language:
                    has_target_language.add(s)

                if opts.restrict_max_runtime:
                    failed_job_runtime = failed_job.get('run_time_seconds', math.inf)
                    passed_job_runtime = passed_job.get('run_time_seconds', math.inf)
                    if (failed_job_runtime < opts.restrict_max_runtime and
                            passed_job_runtime < opts.restrict_max_runtime):
                        within_max_runtime.add(s)

                if opts.restrict_non_docker:
                    contains_docker = False
                    if 'services' in failed_config and failed_config['services']:
                        contains_docker = True

                    regex = r'^[^#]*docker\s+(build|exec|image|login|pull|push|rmi|run|start|compose|buildx|tag)\s+'
                    for step in failed_config.get('steps', []):
                        if 'run' in step and re.search(regex, str(step['run'])):
                            contains_docker = True

                        # TODO: Add a new filter to specifically allow unsupported actions, instead of
                        # wrapping it in --allow-failed-step?
                        elif (
                                'uses' in step and
                                any(action in step['uses'] for action in UNSUPPORTED_ACTIONS) and
                                s in valid_failed_step_only
                        ):
                            valid_failed_step_only.remove(s)
                    if not contains_docker:
                        non_docker.add(s)

                if opts.restrict_diff_size:
                    min_size, max_size = map(int, opts.restrict_diff_size.split('~'))
                    num_changed_lines = jp.get('metrics', {}).get('changes')
                    if num_changed_lines is not None and min_size <= num_changed_lines <= max_size:
                        within_diff_size.add(s)

        return (archived_only, resettable, attempted, filtered, test_failures_only, classified_build_only,
                classified_code_only, classified_test_only, classified_exception_only, build_system, os_version,
                different_base_image, ci_service, valid_failed_step_only, custom_failed_step_only, within_time_range,
                failed_compile_step_only, has_target_language, within_max_runtime, non_docker, within_diff_size)

    @staticmethod
    def _jp2str(jp) -> str:
        return json.dumps(jp, sort_keys=True)

    @staticmethod
    def _str2jp(s):
        return json.loads(s)

    @staticmethod
    def _replace_matrix_param(param: str, config: dict):
        try:
            result = config['strategy']['matrix']
        except KeyError:
            return ''

        for key in param.split('.'):
            result = result[key] if isinstance(result, dict) and key in result else ''
        return result


def main(argv=None):
    argv = argv or sys.argv

    # Configure logging.
    log.config_logging(getattr(logging, 'INFO', None))

    repo_list, output_path, flags = _validate_input(argv)

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
    log.info('{} pairs with at least one reproduce attempt.'.format(_including_or_excluding(flags.include_attempted)))
    log.info('{} pairs that are only archived by GitHub.'.format(_including_or_excluding(flags.include_archived)))
    log.info('{} pairs that are resettable.'.format(_including_or_excluding(flags.include_resettable)))
    log.info('{} pairs that have different base images'.format(
        _including_or_excluding(flags.include_different_base_image)))
    log.info('Excluding pairs that were filtered by PairFilter.')
    if flags.include_only_test_failures:
        log.info('Restricted to test failures')
    if flags.include_only_compile_failures:
        log.info('Restricted to compile failures')
    if flags.restrict_classified_build:
        log.info('Restricted to classified build')
    if flags.restrict_classified_test:
        log.info('Restricted to classified test')
    if flags.restrict_classified_code:
        log.info('Restricted to classified code')
    if flags.exclude_classified_build:
        log.info('Excluding classified build')
    if flags.exclude_classified_test:
        log.info('Excluding classified test')
    if flags.exclude_classified_code:
        log.info('Excluding classified code')
    if flags.restrict_classified_exclusive:
        log.info('Restricted to exclusively classified build/test/code')
    if flags.restrict_classified_exception != '':
        log.info('Restricted to classified exception: {}'.format(flags.restrict_classified_exception))
    if flags.restrict_build_system != '':
        log.info('Restricted to build system: {}'.format(flags.restrict_build_system))
    if flags.restrict_os_version != '':
        log.info('Restricted OS version to: {}'.format(flags.restrict_os_version))
    if flags.restrict_diff_size != '':
        log.info('Restricted diff size: {}'.format(flags.restrict_diff_size))
    if flags.restrict_ci_service != '':
        log.info('Restricted CI service: {}'.format(flags.restrict_ci_service))
    if flags.restrict_valid_failed_step:
        log.info('Restricted to valid failed step')
    if flags.restrict_custom_failed_step:
        log.info('Restricted to custom action failed step')
    if flags.restrict_earliest_mine_date:
        log.info('Restricted to pairs mined before {}'.format(
            flags.restrict_earliest_mine_date.strftime('%Y-%m-%d %H:%M:%S')))
    if flags.restrict_max_runtime:
        log.info('Restricted to jobs with runtime under {}'.format(timedelta(seconds=flags.restrict_max_runtime)))
    if flags.restrict_non_docker:
        log.info('Restricted to non-Docker')
    log.info()

    with ThreadPoolExecutor(max_workers=min(len(repo_list), 64)) as executor:
        future_to_repo = {executor.submit(_choose_pairs_from_repo, repo, flags): repo for repo in repo_list}

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


def _choose_pairs_from_repo(repo: str, opts: Options) -> Tuple[List, Optional[str]]:
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

    jobpairs = JobPairSelector.select(buildpairs, repo, opts)
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


def _seconds_from_runtimestr(s: str) -> int:
    if not s:
        raise ValueError

    # e.g. 2h3m1s
    match = re.match(r'^((?P<hour>\d+)h)?((?P<min>\d+)m)?((?P<sec>\d+)s)?$', s)
    if not match:
        # e.g. 02:03:01
        match = re.match(r'^((?P<hour>\d+):)?((?P<min>\d+):(?P<sec>\d+))$', s)
    if not match:
        raise ValueError

    hours = int(match.group('hour') or 0)
    minutes = int(match.group('min') or 0)
    seconds = int(match.group('sec') or 0)

    return seconds + 60 * minutes + 3600 * hours


def _validate_input(argv):
    # Parse command line arguments.
    short_opts = 'r:o:'
    long_opts = ('repo= repo-file= output-path= include-attempted include-archived-only include-resettable '
                 'include-test-failures-only include-different-base-image classified-build classified-code '
                 'classified-test exclusive-classify classified-exception= build-system= os-version= diff-size= '
                 'ci-service= allow-invalid-step exclude-predefined-actions include-compile-failures-only '
                 'no-classified-build no-classified-code no-classified-test earliest-mine-date= language= '
                 'max-job-runtime= exclude-docker').split()

    try:
        optlist, args = getopt.getopt(argv[1:], short_opts, long_opts)
    except getopt.GetoptError as err:
        _print_usage(msg=err.msg)
        sys.exit(2)

    repo = None
    repo_file_path = None
    output_path = None

    flags = Options()

    for opt, arg in optlist:
        if opt in ('-r', '--repo'):
            repo = arg
        if opt == '--repo-file':
            repo_file_path = arg
        if opt in ('-o', '--output-path'):
            output_path = os.path.abspath(arg)
        if opt == '--include-attempted':
            flags.include_attempted = True
        if opt == '--include-archived-only':
            flags.include_archived = True
        if opt == '--include-resettable':
            flags.include_resettable = True
        if opt == '--include-test-failures-only':
            flags.include_only_test_failures = True
        if opt == '--include-different-base-image':
            flags.include_different_base_image = True
        if opt == '--classified-build':
            flags.restrict_classified_build = True
        if opt == '--classified-code':
            flags.restrict_classified_code = True
        if opt == '--classified-test':
            flags.restrict_classified_test = True
        if opt == '--no-classified-build':
            flags.exclude_classified_build = True
        if opt == '--no-classified-code':
            flags.exclude_classified_code = True
        if opt == '--no-classified-test':
            flags.exclude_classified_test = True
        if opt == '--exclusive-classify':
            flags.restrict_classified_exclusive = True
        if opt == '--classified-exception':
            flags.restrict_classified_exception = arg
            if arg is None:
                _print_usage(msg='Missing exception argument. Exiting.')
                sys.exit(2)
        if opt == '--build-system':
            flags.restrict_build_system = arg
        if opt == '--os-version':
            flags.restrict_os_version = arg
        if opt == '--diff-size':
            if not arg or '~' not in arg or len(arg.split('~')) != 2:
                _print_usage(msg='Diff size argument should be MIN~MAX. Exiting.')
                sys.exit(2)
            flags.restrict_diff_size = arg
        if opt == '--ci-service':
            if arg is None:
                _print_usage('Missing CI service argument. Exiting.')
                sys.exit(2)
            if arg.lower() not in ['github', 'travis']:
                _print_usage('CI service argument must be either "github" or "travis". Exiting.')
                sys.exit(2)
            flags.restrict_ci_service = arg.lower()
        if opt == '--allow-invalid-step':
            flags.restrict_valid_failed_step = False
        if opt == '--exclude-predefined-actions':
            flags.restrict_custom_failed_step = True
        if opt == '--include-compile-failures-only':
            flags.include_only_compile_failures = True
        if opt == '--earliest-mine-date':
            try:
                flags.restrict_earliest_mine_date = dateutil.parser.parse(arg).astimezone()
            except dateutil.parser.ParserError:
                _print_usage('Invalid date: {}'.format(arg))
                sys.exit(2)
        if opt == '--language':
            flags.restrict_language = arg.lower()
        if opt == '--max-job-runtime':
            try:
                flags.restrict_max_runtime = _seconds_from_runtimestr(arg.lower())
            except ValueError:
                _print_usage('Invalid duration: {}'.format(arg))
                sys.exit(2)
        if opt == '--exclude-docker':
            flags.restrict_non_docker = True

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

    return repo_list, output_path, flags


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
    log.info('{:>6}  {:<31}{}'.format('', '--include-compile-failures-only', 'Include job pairs whose failed step was '
                                                                             'a compilation step. Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--include-different-base-image', 'Include job pairs that passed and failed '
                                                                            'job have different base images. Defaults '
                                                                            'to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--classified-build', 'Restrict job pairs that have been classified as build '
                                                                'according to classifier Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--classified-code', 'Restrict job pairs that have been classified as code '
                                                               'according to classifier Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--classified-test', 'Restrict job pairs that have been classified as test '
                                                               'according to classifier Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--no-classified-build', 'Exclude job pairs that have been classified as '
                                                                   'build according to the classifier. Defaults to '
                                                                   'false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--no-classified-code', 'Exclude job pairs that have been classified as code '
                                                                  'according to the classifier. Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--no-classified-test', 'Exclude job pairs that have been classified as test '
                                                                  'according to the classifier. Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--exclusive-classify', 'Restrict to job pairs that have been exclusively '
                                                                  'classified as build/code/test, as specified by '
                                                                  'their respective options. Defaults to false.'))
    log.info('{:>6}  {:<31}{}'.format('', '--classified-exception', 'Restrict job pairs that have been classified as '
                                                                    'contain certain exception'))
    log.info('{:>6}  {:<31}{}'.format('', '--build-system <SYSTEM>', 'Restricted to certain build system'))
    log.info('{:>6}  {:<31}{}'.format('', '--os-version <OS>', 'Restricted to certain OS version (e.g. 12.04, 14.04, '
                                                               '16.04 for Travis, ubuntu-18.04 for Github)'))
    log.info('{:>6}  {:<31}{}'.format('', '--diff-size <MIN>~<MAX>', 'Restricted to certain diff size MIN~MAX '
                                                                     '(e.g. 0~5)'))
    log.info('{:>6}  {:<31}{}'.format('', '--ci-service <CI>', 'Restricted to certain CI service (either "travis" or '
                                                               '"github")'))
    log.info('{:>6}  {:<31}{}'.format('', '--allow-invalid-step', 'Include job pairs that have invalid failed step. '
                                                                  'Note: They are excluded by default because '
                                                                  'reproducer cannot reproduce them.'))
    log.info('{:>6}  {:<31}{}'.format('', '--exclude-predefined-actions', 'Exclude job pairs that have predefined '
                                                                          'action as the failed step.'))
    log.info('{:>6}  {:<31}{}'.format('', '--earliest-mine-date', 'Restrict to CI runs mined on or after the given '
                                                                  'date.'))
    log.info('{:>6}  {:<31}{}'.format('', '--language <LANG>', 'Restrict to a given language.'))
    log.info('{:>6}  {:<31}{}'.format('', '--max-job-runtime <TIME>', 'Restrict to jobs that took at most <TIME> to run'
                                                                      ' (e.g. "20m"/"20:00" or "1h30m5s"/"1:30:05").'))
    log.info('{:>6}  {:<31}{}'.format('', '--exclude-docker', 'Exclude job pairs that used Docker command'))


if __name__ == '__main__':
    sys.exit(main())
