#!/usr/bin/env python3

import datetime
import getopt
import os
import statistics
import sys
import matplotlib.pyplot as plt

from typing import Any
from typing import Optional
from typing import Sequence

from bugswarm.common.json import read_json
from pair_finder.utils import Utils

OUTPUT_DIR = 'output'


class Stats(object):
    def __init__(self,
                 extracted_pull_requests,
                 merged_pull_requests,
                 extracted_build_pairs,
                 build_pairs_with_trigger,
                 build_pairs_with_base,
                 build_pairs_with_build_id,
                 build_pairs_with_jobs,
                 merged_unsquashed_and_squashed_pairs):
        self.num_extracted_pull_requests = len(extracted_pull_requests)
        self.num_merged_pull_requests = len(merged_pull_requests)
        self.num_extracted_build_pairs = len(extracted_build_pairs)
        self.num_build_pairs_with_trigger = len(build_pairs_with_trigger)
        self.num_build_pairs_with_base = len(build_pairs_with_base)
        self.num_build_pairs_with_build_id = len(build_pairs_with_build_id)
        self.num_build_pairs_with_jobs = len(build_pairs_with_jobs)
        self.num_merged_unsquashed_and_squashed_pairs = len(merged_unsquashed_and_squashed_pairs)

        # Merged pull requests with at least 2 builds
        merged_viable_pull_requests = [pr for pr_num, pr in merged_pull_requests.items() if len(pr.builds) >= 2]
        self.num_merged_viable_pull_requests = len(merged_viable_pull_requests)

        # Gather all builds
        all_failed_builds = []
        for pr_num, pairs in extracted_build_pairs.items():
            for p in pairs:
                all_failed_builds.append(p.failed_build)

        # Number of jobs in each failed build
        failed_build_job_counts = [len(b.jobs) for b in all_failed_builds]

        # Average jobs per build
        self.average_num_jobs_per_build = Stats.mean(failed_build_job_counts)

        # Gather all pull requests
        all_merged_pull_requests = []
        for pr_num, pr in merged_pull_requests.items():
            all_merged_pull_requests.append(pr)

        # Number of commits per merged pull request
        merged_pr_commit_counts = [pr.num_commits for pr in all_merged_pull_requests]

        # Average commits per merged pull request
        self.average_num_commits_per_merged_pr = Stats.mean(merged_pr_commit_counts)

    @staticmethod
    def mean(numbers):
        return float(sum(numbers)) / max(len(numbers), 1)


def main(argv=None):
    argv = argv or sys.argv

    # Parse command line arguments.
    try:
        optlist, args = getopt.getopt(argv[1:], 'r:', 'repo='.split())
    except getopt.GetoptError as err:
        print_usage(msg=err.msg)
        return 2
    repo = None
    for opt, arg in optlist:
        if opt in ('-r', '--repo'):
            repo = arg

    if repo is not None:
        output_file_list = [Utils.output_file_path_from_repo(repo)]
    else:
        output_file_list = [os.path.join(OUTPUT_DIR, file) for file in os.listdir(OUTPUT_DIR) if file.endswith('.json')]

    if not output_file_list:
        print('No output files found. Stopping.')
        return 2

    all_stats = get_all_stats(output_file_list)

    all_num_build_pairs_with_base = [d['num_build_pairs_with_base'] for d in all_stats]
    all_num_build_pairs_with_build_id = [d['num_build_pairs_with_build_id'] for d in all_stats]
    all_num_build_pairs_with_trigger = [d['num_build_pairs_with_trigger'] for d in all_stats]
    all_num_extracted_build_pairs = [d['num_extracted_build_pairs'] for d in all_stats]
    all_num_extracted_pull_requests = [d['num_extracted_pull_requests'] for d in all_stats]
    all_num_merged_pull_requests = [d['num_merged_pull_requests'] for d in all_stats]
    all_num_merged_unsquashed_and_squashed_pairs = [d['num_merged_unsquashed_and_squashed_pairs'] for d in all_stats]
    all_num_merged_viable_pull_requests = [d['num_merged_viable_pull_requests'] for d in all_stats]
    all_durations = get_all_durations(output_file_list)

    # Totals
    tot_num_extracted_build_pairs = sum(all_num_extracted_build_pairs)
    tot_num_extracted_pull_requests = sum(all_num_extracted_pull_requests)
    tot_num_merged_pull_requests = sum(all_num_merged_pull_requests)
    tot_num_merged_unsquashed_and_squashed_pairs = sum(all_num_merged_unsquashed_and_squashed_pairs)
    tot_num_merged_viable_pull_requests = sum(all_num_merged_viable_pull_requests)

    # Averages
    avg_num_build_pairs_with_base = Stats.mean(all_num_build_pairs_with_base)
    avg_num_build_pairs_with_build_id = Stats.mean(all_num_build_pairs_with_build_id)
    avg_num_build_pairs_with_trigger = Stats.mean(all_num_build_pairs_with_trigger)
    avg_num_extracted_build_pairs = Stats.mean(all_num_extracted_build_pairs)
    avg_num_extracted_pull_requests = Stats.mean(all_num_extracted_pull_requests)
    avg_num_merged_pull_requests = Stats.mean(all_num_merged_pull_requests)
    avg_num_merged_unsquashed_pairs = Stats.mean(all_num_merged_unsquashed_and_squashed_pairs)
    avg_num_merged_viable_pull_requests = Stats.mean(all_num_merged_viable_pull_requests)
    avg_duration = Stats.mean(all_durations)

    # Medians
    med_num_extracted_pull_requests = statistics.median(all_num_extracted_pull_requests)
    med_num_merged_pull_requests = statistics.median(all_num_merged_pull_requests)
    med_num_merged_viable_pull_requests = statistics.median(all_num_merged_viable_pull_requests)

    # Standard Deviations
    sdv_num_extracted_pull_requests = statistics.stdev(all_num_extracted_pull_requests)
    sdv_num_merged_pull_requests = statistics.stdev(all_num_merged_pull_requests)
    sdv_num_merged_viable_pull_requests = statistics.stdev(all_num_merged_viable_pull_requests)

    print('')
    print('Total project count:', len(all_stats))
    print('')
    print('Totals:')
    print('  {:<70}{}'.format('Total all (unfiltered) pull requests', tot_num_extracted_pull_requests))
    print('  {:<70}{}'.format('Total merged pull requests', tot_num_merged_pull_requests))
    print('  {:<70}{}'.format('Total merged pull requests with at least two builds',
                              tot_num_merged_viable_pull_requests))
    print('')
    print('  {:<70}{}'.format('Total all (unfiltered) extracted pairs', tot_num_extracted_build_pairs))
    print('  {:<70}{}'.format('Total merged, unsquashed pairs', tot_num_merged_unsquashed_and_squashed_pairs))
    print('')
    print('')
    print('Per-project:')
    print('  count of all (unfiltered) pull requests:')
    print('    {:<10}{:.1f}'.format('mean', avg_num_extracted_pull_requests))
    print('    {:<10}{:.1f}'.format('median', med_num_extracted_pull_requests))
    print('    {:<10}{:.1f}'.format('std dev', sdv_num_extracted_pull_requests))
    print('  count of merged pull requests')
    print('    {:<10}{:.1f}'.format('mean', avg_num_merged_pull_requests))
    print('    {:<10}{:.1f}'.format('median', med_num_merged_pull_requests))
    print('    {:<10}{:.1f}'.format('std dev', sdv_num_merged_pull_requests))
    print('  count of merged pull requests with at least two builds')
    print('    {:<10}{:.1f}'.format('mean', avg_num_merged_viable_pull_requests))
    print('    {:<10}{:.1f}'.format('median', med_num_merged_viable_pull_requests))
    print('    {:<10}{:.1f}'.format('std dev', sdv_num_merged_viable_pull_requests))
    print('')
    print('  {:<70}{:.1f}'.format('average count of all (unfiltered) extracted pairs', avg_num_extracted_build_pairs))
    print('  {:<70}{:.1f}'.format('average count of pairs with build ID', avg_num_build_pairs_with_build_id))
    print('  {:<70}{:.1f}'.format('average count of pairs with trigger commit', avg_num_build_pairs_with_trigger))
    print('  {:<70}{:.1f}'.format('average count of pairs with base commit', avg_num_build_pairs_with_base))
    print('  {:<70}{:.1f}'.format('average count of merged, unsquashed pairs', avg_num_merged_unsquashed_pairs))
    print('')
    print('  {:<70}{:.1f}'.format('average elapsed wall clock time (minutes)', avg_duration))

    # f1 = plt.figure(1)
    # f1.suptitle('Pull Request Figures')
    # bin_width1 = 25
    # bins1 = range(min(all_num_extracted_pull_requests), max(all_num_extracted_pull_requests) + bin_width1, bin_width1)
    # plot_figure(f1, 1, all_num_extracted_pull_requests,     log=True, bins=bins1, ymax=150, title='count of all
    # (unfiltered) pull requests')
    # plot_figure(f1, 2, all_num_merged_pull_requests,        log=True, bins=bins1, ymax=150, title='count of merged
    # pull requests')
    # plot_figure(f1, 3, all_num_merged_viable_pull_requests, log=True, bins=bins1, ymax=150, title='count of merged
    # pull requests with at least two builds')

    # f2 = plt.figure(2)
    # f2.suptitle('Pair Figures')
    # bin_width2 = 10
    # bins2 = range(min(all_num_extracted_build_pairs), 250 + bin_width2, bin_width2)
    # plot_figure(f2, 1, all_num_extracted_build_pairs,     log=True, bins=bins2, title='count of all (unfiltered)
    # extracted pairs')
    # plot_figure(f2, 2, all_num_build_pairs_with_build_id, log=True, bins=bins2, title='count of pairs with build ID')
    # plot_figure(f2, 3, all_num_build_pairs_with_trigger,  log=True, bins=bins2, title='count of pairs with trigger
    # commit')
    # plot_figure(f2, 4, all_num_build_pairs_with_base,     log=True, bins=bins2, title='count of pairs with base
    # commit')
    # plot_figure(f2, 5, all_num_merged_unsquashed_pairs,   log=True, bins=bins2, title='count of merged, unsquashed
    # pairs')

    # f3 = plt.figure(3)
    # f3.suptitle('Other Figures')
    # bin_width3 = 1
    # bins3 = range(0, 45 + bin_width3, bin_width3)
    # plot_figure(f3, 1, all_durations,                     log=True, bins=bins3, title='elapsed wall clock time
    # (minutes)')

    plt.show()


def plot_figure(figure, subplot_number, numbers: Sequence[Any], title='', ymax=None, **kwargs):
    sp = plt.subplot(3, 1, subplot_number)
    sp.set_title(title)
    plt.hist(numbers, **kwargs)
    if ymax is not None:
        plt.ylim(ymax=ymax)
    plt.title(title)


def get_all_stats(output_file_list: Sequence[str]) -> Sequence[dict]:
    all_stats = []
    for output_file_path in output_file_list:
        stats = get_stats(output_file_path)
        if stats is not None:
            all_stats.append(stats)
    return all_stats


def get_stats(output_file_path: str) -> Optional[dict]:
    try:
        return read_json(output_file_path)['stats']
    except FileNotFoundError:
        print('Cannot find output file at ' + output_file_path + '. Skipping.')
    except KeyError:
        print(output_file_path, 'does not have the key "stats". Skipping.')
    return None


def get_all_durations(output_file_list: Sequence[str]) -> Sequence[int]:
    all_durations = []
    for output_file_path in output_file_list:
        duration = get_duration(output_file_path)
        if duration is not None:
            all_durations.append(duration)
    return all_durations


def get_duration(output_file_path: str) -> Optional[int]:
    try:
        duration_string = read_json(output_file_path)['duration']
        duration = datetime.datetime.strptime(duration_string, '%Hh %Mm %S.%fs')
        delta = datetime.timedelta(hours=duration.hour, minutes=duration.minute, seconds=duration.second)
        return delta.total_seconds() // 60
    except FileNotFoundError:
        print('Cannot find output file at ' + output_file_path + '. Skipping.')
    except KeyError:
        print(output_file_path, 'does not have the key "duration". Skipping.')
    return None


def print_usage(msg=None):
    if msg is not None:
        print(msg)
    print('Usage: python3 pair_finder.py OPTIONS')
    print('\t{:<30}{:<30}'.format('-r, --repo', '(optional) repo slug. Get stats for a single repo'))


if __name__ == '__main__':
    sys.exit(main())
