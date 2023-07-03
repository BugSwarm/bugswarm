import getopt
import logging
import os
import sys
import time

from typing import List
from typing import Tuple

from bugswarm.analyzer import analyzer
from bugswarm.common import log
from bugswarm.common.json import read_json
from bugswarm.common.json import write_json
from bugswarm.common.log_downloader import download_log
from bugswarm.common.utils import get_current_component_version_message

from reproducer.config import Config
from reproducer.model.jobpair import JobPair
from reproducer.pair_center import PairCenter
from reproducer.utils import Utils
from reproducer.pipeline.analyze_and_compare import analyze_and_compare


class ReproducedResultsAnalyzer(object):
    def __init__(self, input_file, runs, task_name):
        log.info('Initializing ReproducedResultsAnalyzer.')
        self.input_file = input_file
        self.runs = runs
        self.config = Config(task_name)
        self.utils = Utils(self.config)
        self.analyzer = analyzer.Analyzer()
        # Initializing pair_center should not be in _pre_analyze because we want the pairs to maintain state between
        # analyzing each run.
        self.pair_center = PairCenter(input_file, self.utils)

        # The below attributes are initialized in _pre_analyze.
        self.start_time = None
        self.reproduced_logs = None
        self.reproduced_logs_analyzed = None
        self.error_count = None

    def run(self):
        for i in range(1, self.runs + 1):
            self._pre_analyze()
            self._analyze(i)
            self._post_analyze(i)
        self._show_reproducibility()
        self._write_output_json()
        log.info('Done!')

    def _pre_analyze(self):
        """
        Reset state before analyzing the next run.
        """
        self.start_time = time.time()
        self.reproduced_logs = {}
        self.reproduced_logs_analyzed = 0
        self.error_count = 0

        # Reset the match type flag before each run
        for r in self.pair_center.repos:
            for bp in self.pair_center.repos[r].buildpairs:
                bp.set_match_type.value = False

    def _analyze(self, run):
        """
        Analyze a single run of reproduced results.
        For each job in a jobpair, check if the reproduced log exists in the task folder. If it does, then download the
        original Travis log. Finally, analyze and compare the two logs.
        """
        for r in self.pair_center.repos:
            for bp in self.pair_center.repos[r].buildpairs:
                for jp in bp.jobpairs:
                    for j in jp.jobs:
                        try:
                            analyzed_reproduced_log = analyze_and_compare(self, j, run)
                            if analyzed_reproduced_log:
                                self.reproduced_logs_analyzed += 1
                        except Exception as e:
                            log.error('Encountered an error while analyzing and comparing {}: {}'.format(j.job_name, e))
                            self.error_count += 1
        self.pair_center.update_buildpair_done_status()
        self.pair_center.assign_pair_match_types()
        self.pair_center.assign_pair_match_history(run)
        self.pair_center.assign_pair_patch_history(run)

    def _post_analyze(self, run):
        """
        This function is called after analyzing each run. Print statistics like how many pairs matched and time elapsed
        and then visualize the match history after this run.
        """
        log.info('Done analyzing run {}.'.format(run))
        self._visualize_match_history()
        log.info('{} reproduced logs analyzed and {} errors in run {}.'
                 .format(self.reproduced_logs_analyzed, self.error_count, run))
        # Print a blank line to separate each run.
        log.info()
        mmm = self.utils.construct_mmm_count(self.pair_center)
        aaa = self.utils.construct_aaa_count(self.pair_center)
        log.debug('Match types in run {}: m1-m2-m3: {} a1-a2-a3: {}.'.format(run, mmm, aaa))

    def _write_output_json(self):
        log.info('Writing output JSON annotated with match history.')
        pairs = read_json(self.input_file)
        # Write default attributes.
        for p in pairs:
            for jp in p['jobpairs']:
                jp['match_history'] = {}
                jp['failed_job']['match_history'] = {}
                jp['passed_job']['match_history'] = {}
                jp['failed_job']['orig_result'] = ''
                jp['passed_job']['orig_result'] = ''
                jp['failed_job']['mismatch_attrs'] = []
                jp['passed_job']['mismatch_attrs'] = []
                jp['failed_job']['pip_patch'] = False
                jp['passed_job']['pip_patch'] = False

        for p in pairs:
            repo = p['repo']
            if repo not in self.pair_center.repos:
                continue

            # Try to find this build pair in pair center.
            for bp in self.pair_center.repos[repo].buildpairs:
                if p['failed_build']['build_id'] == bp.builds[0].build_id:
                    # Found build pair in pair center.

                    # Optional: Write buildpair match type.
                    # This is not used since we switched to jobpair packaging.
                    p['match'] = bp.match.value
                    trigger_sha = p['failed_build']['head_sha']
                    # Similarly, for each job pair in build pair, try to find it in the pair center.
                    for jp in p['jobpairs']:
                        # For a build that has some jobs filtered and some jobs not filtered,
                        # the job cannot be found in paircenter.
                        if jp['is_filtered']:
                            continue

                        found_in_paircenter = False
                        for jobpair in bp.jobpairs:
                            if str(jobpair.jobs[0].job_id) == str(jp['failed_job']['job_id']):
                                found_in_paircenter = True
                                # Write jobpair match history, analyzed results, and mismatched attributes.
                                jp['match_history'] = jobpair.match_history
                                jp['failed_job']['match_history'] = jobpair.failed_job_match_history
                                jp['passed_job']['match_history'] = jobpair.passed_job_match_history
                                jp['failed_job']['orig_result'] = jobpair.jobs[0].orig_result
                                jp['passed_job']['orig_result'] = jobpair.jobs[1].orig_result
                                jp['failed_job']['mismatch_attrs'] = jobpair.jobs[0].mismatch_attrs
                                jp['passed_job']['mismatch_attrs'] = jobpair.jobs[1].mismatch_attrs
                                jp['failed_job']['pip_patch'] = jobpair.jobs[0].pip_patch
                                jp['passed_job']['pip_patch'] = jobpair.jobs[1].pip_patch

                        if not found_in_paircenter:
                            # If not found in pair center, this jobpair was filtered out.
                            # In this case, we still analyze the original log to get as many attributes as possible.
                            for i in range(2):
                                job_name = 'failed_job' if i == 0 else 'passed_job'
                                job_id = jp[job_name]['job_id']
                                original_log_path = self.utils.get_orig_log_path(job_id)
                                if not download_log(job_id, original_log_path, repo=repo):
                                    continue
                                original_result = self.analyzer.analyze_single_log(original_log_path, job_id, 'github',
                                                                                   trigger_sha=trigger_sha, repo=repo)
                                if 'not_in_supported_language' in original_result:
                                    continue
                                jp[job_name]['orig_result'] = original_result
                            raise RuntimeError('Unexpected state: Jobpair not found in pair center. Exiting.')

        os.makedirs(self.config.result_json_dir, exist_ok=True)
        filename = self.config.task + '.json'
        filepath = os.path.join(self.config.result_json_dir, filename)
        write_json(filepath, pairs)

    def _get_all_jobpairs_and_all_runs(self) -> Tuple[List[JobPair], List[str]]:
        all_jobpairs = []
        for r in self.pair_center.repos:
            for bp in self.pair_center.repos[r].buildpairs:
                for jp in bp.jobpairs:
                    all_jobpairs.append(jp)
        all_runs = []
        for jp in all_jobpairs:
            for run in jp.match_history:
                all_runs.append(run)
        all_runs = list(set(all_runs))
        all_runs.sort()
        return all_jobpairs, all_runs

    def _visualize_match_history(self):
        log.info('Visualizing match history:')
        log.info('N means no reproduced log exists. (An error occured in reproducer while reproducing the job.)')
        all_jobpairs, all_runs = self._get_all_jobpairs_and_all_runs()
        for jp in all_jobpairs:
            log.info(jp.full_name)
            match_histories = [
                (jp.match_history, 'Job pair'),
                (jp.failed_job_match_history, 'Failed job'),
                (jp.passed_job_match_history, 'Passed job'),
            ]
            for match_history, history_name in match_histories:
                # Task name is run number 1-5
                mh = [str(match_history.get(run, 'N')) for run in all_runs]
                if mh:
                    full_history_name = '{} match history'.format(history_name)
                    log.info('{:>24}:'.format(full_history_name), ' -> '.join(mh))
                else:
                    log.info('No match history. (This jobpair is not reproduced.)')

    def _show_reproducibility(self):
        log.info('Visualizing reproducibility:')
        all_jobpairs, all_runs = self._get_all_jobpairs_and_all_runs()
        if not all_jobpairs:
            log.info('Nothing to visualize since no jobs were run.')
        else:
            full_name_max_length = max([len(jp.full_name) for jp in all_jobpairs])
            for jp in all_jobpairs:
                mh = []
                for run in all_runs:
                    run_result = jp.match_history.get(run)
                    # run_result could be 'N', 0, or 1
                    if run_result != 1:
                        mh.append(0)
                    else:
                        mh.append(run_result)

                # No reproducing runs were successful
                if all(v == 0 for v in mh):
                    reproducibility = 'Unreproducible'
                # match history is all 1s, all runs reproducible
                elif all(mh):
                    reproducibility = 'Reproducible'
                else:
                    reproducibility = 'Flaky'
                log.info('{full_name: >{width}} job pair reproducibility: {result}'
                         .format(width=full_name_max_length, full_name=jp.full_name, result=reproducibility))
        # Print a blank separator line.
        log.info()


def _print_usage():
    log.info('Usage: python3 reproduced_results_analyzer.py -i <input_file> -n <runs> --task-name <task_name>')
    log.info('{:<30}{:<30}'.format('-i, --input-file', 'Path to a JSON file containing fail-pass pairs to reproduce.'))
    log.info('{:<30}{:<30}'.format('-n, --runs', 'Number of reproducer runs to analyze.'))
    log.info('{:<30}{:<30}'.format('--task-name', 'Name of task folder, or default to the name of JSON file'))


def _validate_input(argv):
    shortopts = 'i:n:'
    longopts = 'input-file= runs= task-name='.split()
    input_file = None
    runs = 0
    task_name = None
    try:
        optlist, args = getopt.getopt(argv[1:], shortopts, longopts)
    except getopt.GetoptError:
        log.error('Could not parse arguments. Exiting.')
        _print_usage()
        sys.exit(2)

    for opt, arg in optlist:
        if opt in ('-i', '--input-file'):
            input_file = arg
        elif opt in ('-n', '--runs'):
            try:
                runs = int(arg)
            except (ValueError, TypeError):
                log.error('The runs argument must be an integer.')
                _print_usage()
                sys.exit(2)
        elif opt == '--task-name':
            task_name = arg

    if not input_file:
        _print_usage()
        sys.exit(2)
    if not os.path.isfile(input_file):
        log.error('The input_file argument is not a file or does not exist. Exiting.')
        sys.exit(2)
    if not runs:
        _print_usage()
        sys.exit(2)
    if not task_name:
        _print_usage()
        sys.exit(2)

    return input_file, runs, task_name


def main(argv=None):
    argv = argv or sys.argv

    # Configure logging.
    log.config_logging(getattr(logging, 'INFO', None))

    # Log the current version of this BugSwarm component.
    log.info(get_current_component_version_message('ReproducedResultsAnalyzer'))

    input_file, runs, task_name = _validate_input(argv)
    ReproducedResultsAnalyzer(input_file, runs, task_name).run()


if __name__ == '__main__':
    sys.exit(main())
