#!/usr/bin/env python3

import getopt
import logging
import os
import sys
import time

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor

from bugswarm.common import log
from bugswarm.common.json import write_json
from bugswarm.common.utils import get_current_component_version_message

from pair_finder.model.mined_project_builder import MinedProjectBuilder
from pair_finder.output_manager import OutputManager
from pair_finder.pipeline.pipeline import Pipeline
from pair_finder.pipeline.steps.assign_base_commits import AssignBaseCommits
from pair_finder.pipeline.steps.assign_trigger_commits import AssignTriggerCommits
from pair_finder.pipeline.steps.extract_all_build_pairs import ExtractAllBuildPairs
from pair_finder.pipeline.steps.align_job_pairs import AlignJobPairs
from pair_finder.pipeline.steps.group_jobs_by_branch import GroupJobsByBranch
from pair_finder.pipeline.steps.postflight import Postflight
from pair_finder.pipeline.steps.preflight import Preflight
from pair_finder.pipeline.steps.get_jobs_from_travis_api import GetJobsFromTravisAPI
from pair_finder.pipeline.steps.get_pr_merge_statuses import GetPullRequestMergeStatuses
from pair_finder.pipeline.steps.download_pr_commits import DownloadPullRequestCommits
from pair_finder.pipeline.steps.clean_pairs import CleanPairs
from pair_finder.pipeline.steps.get_build_system_info import GetBuildSystemInfo
from pair_finder.utils import Utils

SUPPRESS_THREAD_EXCEPTIONS = False


def main(argv=None):
    argv = argv or sys.argv

    # Parse command line arguments.
    short_opts = 'hr:t:'
    long_opts = 'help repo= repo-file= log= threads= fast keep-clone api'.split()
    try:
        optlist, args = getopt.getopt(argv[1:], short_opts, long_opts)
    except getopt.GetoptError as err:
        print_usage(msg=err.msg)
        return 2

    repo = None
    repo_file_path = None
    log_level = logging.INFO
    skip_if_output_exists = False
    keep_clone = False
    num_threads = 1
    for opt, arg in optlist:
        if opt in ('-h', '--help'):
            print_usage()
            return 2
        if opt in ('-r', '--repo'):
            repo = arg
        if opt == '--repo-file':
            repo_file_path = arg
        if opt == '--log':
            # Validate the passed log level.
            log_level = getattr(logging, arg.upper(), None)
            if log_level is None:
                print_usage(msg='Log level is invalid. Use CRITICAL, ERROR, WARNING, INFO, or DEBUG')
                return 2
        if opt in ('-t', '--threads'):
            num_threads = int(arg)
        if opt == '--fast':
            skip_if_output_exists = True
        if opt == '--keep-clone':
            keep_clone = True

    if repo and repo_file_path:
        print_usage(msg='The --repo and --repo-file arguments are mutually exclusive.')
        return 2
    elif repo:
        task_name = Utils.canonical_task_name_from_repo(repo)
        repo_list = [repo]
    elif repo_file_path:
        task_name = os.path.splitext(repo_file_path)[0].split('/')[-1]
        with open(repo_file_path) as repo_list_file:
            repo_list = list(set([l.strip() for l in repo_list_file if l.strip()]))
    else:
        print_usage(msg='Exactly one of the --repo and --repo-file arguments is required.')
        return 2

    Utils.create_dirs(task_name)
    Utils.clean_bad_json_files(task_name)

    num_workers = min(len(repo_list), num_threads)
    log.info('Initializing', num_workers, 'worker threads.')
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_repo = {executor.submit(_thread_main,
                                          repo,
                                          task_name,
                                          log_level,
                                          skip_if_output_exists,
                                          keep_clone): repo for repo in repo_list}

    for future in as_completed(future_to_repo):
        try:
            future.result()
        except Exception as e:
            if not SUPPRESS_THREAD_EXCEPTIONS:
                log.error(e)
                raise


def _thread_main(repo, task_name, log_level, skip_if_output_exists, keep_clone):
    log.config_logging(log_level, Utils.log_file_path_from_repo(repo))

    # Log the current version of this BugSwarm component.
    log.info(get_current_component_version_message('PairFinder'))

    log.info('Processing', repo)
    output_file_path = Utils.output_file_path_from_repo(repo, task_name)
    if skip_if_output_exists and os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
        log.info('Skipping', repo, 'because output already exists.')
        return

    start_time = time.time()

    in_context = {
        'repo': repo,
        'utils': Utils(),
        'keep_clone': keep_clone,
        'task_name': task_name,
        'mined_project_builder': MinedProjectBuilder(),
        'original_mined_project_metrics': MinedProjectBuilder.query_current_metrics(repo)
    }
    steps = [
        Preflight(),
        GetJobsFromTravisAPI(),
        GroupJobsByBranch(),
        ExtractAllBuildPairs(),
        AlignJobPairs(),
        GetPullRequestMergeStatuses(),
        DownloadPullRequestCommits(),
        AssignTriggerCommits(),
        AssignBaseCommits(),
        CleanPairs(),
        GetBuildSystemInfo(),
        Postflight(),
    ]
    pipeline = Pipeline(steps)

    result, out_context = pipeline.run(None, in_context)
    if not result:
        # A filter in the pipeline encountered a fatal error and made the pipeline exit early.
        # Skip writing the output file.
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
        return

    builder = out_context['mined_project_builder']
    builder.repo = repo
    builder.latest_mined_version = Utils.get_latest_commit_for_repo(repo)
    (mined_build_pairs,
     mined_job_pairs,
     mined_pr_build_pairs,
     mined_pr_job_pairs) = Utils.count_mined_pairs_in_branches(result)
    builder.mined_job_pairs = mined_job_pairs + \
        in_context['original_mined_project_metrics']['progression_metrics']['mined_job_pairs']
    builder.mined_pr_job_pairs = mined_pr_job_pairs + \
        in_context['original_mined_project_metrics']['progression_metrics']['mined_pr_job_pairs']
    builder.mined_build_pairs = mined_build_pairs + \
        in_context['original_mined_project_metrics']['progression_metrics']['mined_build_pairs']
    builder.mined_pr_build_pairs = mined_pr_build_pairs + \
        in_context['original_mined_project_metrics']['progression_metrics']['mined_pr_build_pairs']
    mined_project = builder.build()
    OutputManager.output_to_database(mined_project)
    OutputManager.output(repo, output_path=output_file_path, branches=result)
    metrics_output_file_path = Utils.output_metrics_path_from_repo(repo, task_name)
    write_json(metrics_output_file_path, in_context['original_mined_project_metrics'])

    elapsed = time.time() - start_time
    log.info('Processed {} in {} seconds. Done!'.format(repo, elapsed))


def print_usage(msg=None):
    if msg:
        log.info(msg)
    log.info('Usage: python3 pair_finder.py OPTIONS')
    log.info('Options:')
    log.info('{:>6}, {:<20}{}'.format('-r', '--repo', 'Repo slug. Cannot be used with --repo-file.'))
    log.info('{:>6}  {:<20}{}'.format('', '--repo-file', 'Path to file containing a newline-separated list of repo '
                                                         'slugs. Cannot be used with --repo.'))
    log.info('{:>6}  {:<20}{}'.format('', '--log', 'Log level. Use CRITICAL (lowest), ERROR, WARNING, INFO (default), '
                                                   'or DEBUG (highest).'))
    log.info('{:>6}  {:<20}{}'.format('', '--fast', 'Skips repos that already have an output file.'))
    log.info('{:>6}  {:<20}{}'.format('', '--keep-clone', 'Prevent the default cleanup of the cloned repo after '
                                                          'running.'))
    log.info('{:>6}, {:<20}{}'.format('-h', '--help', 'Display help.'))


if __name__ == '__main__':
    sys.exit(main())
