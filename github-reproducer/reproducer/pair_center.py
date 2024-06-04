import json
import os

from queue import Queue

from bugswarm.common import log
from bugswarm.common.json import read_json

from .job_center import JobCenter
from .matching_checker import MatchChecker
from .model.jobpair import JobPair
from .model.repo import Repo


class PairCenter(JobCenter):
    """
    Reads the input JSON file and initializes model objects in a repo->buildpair->jobpair->job hierarchy.
    """

    def __init__(self, input_file, utils, package_mode=False, skip_filtered=True):
        super().__init__()
        log.info('Initializing pair center.')
        self.package_mode = package_mode
        self.skip_filtered = skip_filtered
        self.repos = {}
        self.uninitialized_repos = Queue()
        self.queue = None
        self._load_jobs_from_pairs_for_repo(input_file)
        self.utils = utils
        self.total_buildpairs = 0
        self.total_jobpairs = 0

    def _load_jobs_from_pairs_for_repo(self, input_file):
        """
        Read the input file, which should contain mined pairs from the database.
        Turn json dict into objects.
        """
        try:
            buildpairs = read_json(input_file)
        except json.JSONDecodeError:
            log.error('Error reading input file {} in PairCenter. Exiting.')
            raise
        for bp in buildpairs:
            # For debug purposes: When we only want to reproduce non-PR pairs, we can uncomment these lines.
            # if bp['pr_num'] == -1:
            #     continue
            repo = bp['repo']
            if repo not in self.repos:
                self.repos[repo] = Repo(repo)
                self.uninitialized_repos.put(repo)
            self._append_buildpair_and_jobpair_to_repo(repo, bp)

        self._init_names()
        self.set_skip_of_job_pairs()
        self._init_queue_of_repos()
        # Calculate buildpair and job numbers after done loading from file.
        self._calc_num_total_buildpairs()
        self._calc_num_total_jobpairs()
        self._calc_num_total_jobs()
        log.debug('pair_center.total_buildpairs =', self.total_buildpairs,
                  'pair_center.total_jobpairs =', self.total_jobpairs,
                  'pair_center.total_jobs =', self.total_jobs)

    def _init_names(self):
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                # Initialize name for buildpair.
                bp.buildpair_name = bp.repo + '/' + '-'.join([
                    str(bp.pr_num),
                    str(bp.builds[0].build_id),
                    str(bp.builds[1].build_id)
                ])
                # Initialize names for jobpairs.
                for jp in bp.jobpairs:
                    jp.buildpair_name = bp.buildpair_name
                    jp.full_name = jp.buildpair_name + '/' + jp.jobpair_name
                    # Initialize names for jobs.
                    for j in jp.jobs:
                        j.buildpair_name = bp.buildpair_name
                        j.jobpair_name = jp.jobpair_name
                        j.job_name = bp.buildpair_name + '/' + jp.jobpair_name + '/' + str(j.job_id)

    def _append_buildpair_and_jobpair_to_repo(self, repo, buildpair):
        if 'jobpairs' not in buildpair:
            log.error('Missing "jobpairs" key in buildpair. Exiting.')
            raise Exception

        # If this build pair has no unfiltered job pairs and we want to skip filtered job pairs, then return without
        # adding this build pair to the repo object.
        unfiltered_jobpairs = [jp for jp in buildpair['jobpairs'] if not jp['is_filtered']]
        if self.skip_filtered and not unfiltered_jobpairs:
            return

        buildpair_obj = self.repos[repo].add_buildpair_to_repo(repo, buildpair)

        for jp in buildpair['jobpairs']:
            # Skip if this jobpair is filtered out.
            if self.skip_filtered and jp['is_filtered']:
                continue
            failed_job_id = jp['failed_job']['job_id']
            failed_job = [failed_job for failed_job in buildpair_obj.builds[0].jobs
                          if failed_job.job_id == str(failed_job_id)][0]
            # TODO: Find out why we need to set image_tag here?
            # failed_job.image_tag = jp['failed_job']['heuristically_parsed_image_tag']
            # failed_job.image_tag = failed_job.config['runs-on']
            failed_job.build_system = jp['build_system'].lower() if jp.get('build_system', 'NA') != 'NA' else None

            passed_job_id = jp['passed_job']['job_id']
            passed_job = [passed_job for passed_job in buildpair_obj.builds[1].jobs
                          if passed_job.job_id == str(passed_job_id)][0]
            # passed_job.image_tag = jp['passed_job']['heuristically_parsed_image_tag']
            # passed_job.image_tag = passed_job.config['runs-on']
            passed_job.build_system = jp['build_system'].lower() if jp.get('build_system', 'NA') != 'NA' else None

            if 'match_history' in jp:
                buildpair_obj.jobpairs.append(JobPair(repo,
                                                      failed_job,
                                                      passed_job,
                                                      match_history=jp['match_history'],
                                                      failed_job_match_history=jp['failed_job']['match_history'],
                                                      passed_job_match_history=jp['passed_job']['match_history']))
            else:
                buildpair_obj.jobpairs.append(JobPair(repo, failed_job, passed_job))

    def _calc_num_total_buildpairs(self):
        self.total_buildpairs = 0
        for r in self.repos:
            self.total_buildpairs += len(self.repos[r].buildpairs)

    def _calc_num_total_jobpairs(self):
        self.total_jobpairs = 0
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                self.total_jobpairs += len(bp.jobpairs)

    def _calc_num_total_jobs(self):
        self.total_jobs = 0
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                for jp in bp.jobpairs:
                    for j in jp.jobs:
                        if j.job_id != '0':
                            self.total_jobs += 1

    def update_buildpair_done_status(self):
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                buildpair_done = True
                for jp in bp.jobpairs:
                    for j in jp.jobs:
                        if not j.reproduced.value and not j.skip and j.job_id != '0':
                            buildpair_done = False
                if buildpair_done:
                    bp.done.value = True

    def assign_pair_match_types(self):
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                if bp.done.value and not bp.set_match_type.value:
                    # Assign match types to build pairs.
                    if MatchChecker.is_buildpair_match_type_1(bp):
                        bp.match.value = 1
                    elif MatchChecker.is_buildpair_match_type_2(bp):
                        bp.match.value = 2
                    elif MatchChecker.is_buildpair_match_type_3(bp):
                        bp.match.value = 3
                    else:
                        bp.match.value = 0

                    # Assign match types to job pairs.
                    for jp in bp.jobpairs:
                        if MatchChecker.is_jobpair_match_type_1(jp):
                            jp.match.value = 1
                        elif MatchChecker.is_jobpair_match_type_2(jp):
                            jp.match.value = 2
                        elif MatchChecker.is_jobpair_match_type_3(jp):
                            jp.match.value = 3
                        else:
                            jp.match.value = 0

                    bp.set_match_type.value = True

    def assign_pair_match_history(self, run):
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                if bp.done.value:
                    for jp in bp.jobpairs:
                        jp.match_history[run] = jp.match.value
                        jp.failed_job_match_history[run] = 1 if jp.jobs[0].match.value else 0
                        jp.passed_job_match_history[run] = 1 if jp.jobs[1].match.value else 0

    def assign_pair_patch_history(self, run):
        # utils.get_patch_path_in_task()
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                for jp in bp.jobpairs:
                    for job in jp.jobs:
                        if os.path.isfile(self.utils.get_patch_path_in_task(job, run)):
                            job.pip_patch = True
                        else:
                            job.pip_patch = False

    # Set the skip attribute of the jobs of the job pairs that did not match over 3 runs.
    def set_skip_of_job_pairs(self):
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                for jp in bp.jobpairs:
                    match_history = [match for _, match in jp.match_history.items()]
                    if len(match_history) >= 3 and (set(match_history) == [0] or len(set(match_history)) > 1):
                        log.info('Skipping jobpair', jp.jobpair_name, 'because no match or unstable in 3 runs.')
                        for j in jp.jobs:
                            j.skip = True

    def get_buildpair_shas(self):
        shas = []
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                for b in bp.builds:
                    shas.append(b.head_sha)
        return list(set(shas))

    def get_buildpair_matching(self, match_type):
        buildpairs = []
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                if bp.match == match_type:
                    buildpairs.append(bp)
        return buildpairs

    def get_jobpair_matching(self, match_type):
        jobpairs = []
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                for jp in bp.jobpairs:
                    if jp.match.value == match_type:
                        jobpairs.append(jp)
        return jobpairs

    def get_num_remaining_jobs(self):
        remaining_jobs = 0
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                for jp in bp.jobpairs:
                    for j in jp.jobs:
                        if not j.skip.value and not j.reproduced.value and j.job_id != '0':
                            remaining_jobs += 1
        return remaining_jobs

    def get_num_remaining_items(self, package_mode):
        return self._get_num_remaining_jobpairs() if package_mode else self.get_num_remaining_jobs()

    def _get_num_remaining_jobpairs(self):
        remaining_jobpairs = 0
        for r in self.repos:
            for bp in self.repos[r].buildpairs:
                for jp in bp.jobpairs:
                    if not jp.reproduced.value:
                        remaining_jobpairs += 1
        return remaining_jobpairs

    def init_queue_for_threads(self, manager, package_mode=False):
        # Because our job/jobpair models use shared objects (e.g. multiprocessing.Value), we can't
        # put them in a shared queue; doing so causes a RuntimeError. Instead, we put the jobs/pairs
        # in a (non-shared) list, and the index of each job in the shared queue.
        self.queue = manager.Queue()
        self.items = []

        if package_mode:
            for r in self.repos:
                for bp in self.repos[r].buildpairs:
                    for jp in bp.jobpairs:
                        if not jp.reproduced.value:
                            self.items.append(jp)
        else:
            for r in self.repos:
                for bp in self.repos[r].buildpairs:
                    for jp in bp.jobpairs:
                        for j in jp.jobs:
                            if not j.reproduced.value and not j.skip.value and j.job_id != '0':
                                self.items.append(j)

        for i in range(len(self.items)):
            self.queue.put_nowait(i)

        log.info('Finished initializing job queue.')

    def dequeue_item(self):
        i = self.queue.get_nowait()
        return self.items[i]

    def item_queue_is_empty(self):
        return self.queue.empty()

    def _init_queue_of_repos(self):
        for r in self.repos:
            self.repos[r].init_queue_to_reproduce(self.package_mode)
