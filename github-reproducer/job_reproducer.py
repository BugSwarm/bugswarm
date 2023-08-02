"""
JobReproducer is a JobDispatcher subclass responsible for reproducing jobs.
"""

import time

from multiprocessing import Value

from bugswarm.common import log
from bugswarm.common.json import write_json
from termcolor import colored

from job_dispatcher import JobDispatcher
from reproducer.pipeline.gen_files_for_job import gen_files_for_job
from reproducer.pipeline.copy_log import copy_log
from reproducer.utils import Utils


class JobReproducer(JobDispatcher):
    """
    Subclass of JobDispatcher that reproduces jobs.
    """

    def __init__(self, input_file, task_name, threads, keep, package_mode, dependency_solver, skip_check_disk):
        super().__init__(input_file, task_name, threads, keep, package_mode, dependency_solver, skip_check_disk)
        self.newly_reproduced = Value('i', 0)
        self.already_reproduced = Value('i', 0)
        self.unicode_decode_error = Value('i', 0)

    def progress_str(self):
        self.job_center.update_buildpair_done_status()
        self.job_center.assign_pair_match_types()
        return colored(
            str(self.alive_threads) + ' alive threads, ' +
            str(self.job_center.total_jobs) + ' total jobs to reproduce, ' +
            str(self.newly_reproduced.value) + ' newly attempted, ' +
            str(self.already_reproduced.value) + ' previously attempted, ' +
            str(self.reproduce_err.value) + ' errors, ' +
            str(self.job_center.get_num_remaining_items(self.package_mode)) + ' remaining.', 'yellow')

    def process_item(self, job, tid):
        """
        This function is called for each item to be run.
        First we check for skipping (whether this item can be skipped).
        :param job: a Job object
        :param tid: thread_id
        """
        self.items_processed.value += 1
        job.reproduced.value = 1

        if self.utils.check_if_log_exist_in_task(job):
            log.debug('Log already exists in task.')
            self.already_reproduced.value += 1
        else:
            self.newly_reproduced.value += 1
            self._reproduce_job(job, tid)

    def _reproduce_job(self, job, tid):
        """
        This is the main function to reproduce a job, which involves the following steps:
        1. Generate files for the job
        2. Build a Docker image
        3. Spawn a Docker container to reproduce the job
        4. Copy files after the job is reproduced.

        :param job: Job object
        :param tid: Thread ID of the thread from which this function is being called
        """
        start_time = time.time()
        log.info('[THREAD {}] Running {}'.format(tid, job))

        gen_files_for_job(self, job, self.keep, self.dependency_solver)
        self.docker.build_and_run(job)
        copy_log(self, job)

        # If --keep is specified, gen_files_for_job copies the build directory into the output directory, so it's safe
        # to remove the workspace job dir.
        log.info('[THREAD {}] Cleaning workspace.'.format(tid))
        self.utils.clean_workspace_job_dir(job)
        if not self.keep:
            log.info('[THREAD {}] Removing reproduction image.'.format(tid))
            self.docker.remove_image('job_id:{}'.format(job.job_id))

        elapsed = time.time() - start_time
        self.job_time_acc += elapsed
        log.info('Done running job', job.job_name, 'after', elapsed, 'seconds.')

    def record_error_reason(self, item, message):
        self.error_reasons[item.job_id] = message

    def handle_failed_reproduce(self, job):
        if self.utils.check_if_travis_build_log_exist(job) and not self.utils.check_if_log_exist(job):
            if not self.utils.check_is_bad_travis_build_log(self.utils.get_travis_build_log_path(job)):
                self.utils.copy_travis_build_log_into_current_task_dir(job)

    def post_run(self):
        """
        Called when all jobs are done reproducing.
        """
        elapsed = time.time() - self.start_time
        log.debug('total elapsed =', elapsed)
        # If jobs were reproduced during this run, print the average processing time.
        if self.newly_reproduced.value:
            avg_job_time_0 = elapsed / self.newly_reproduced.value
            avg_job_time_1 = self.job_time_acc / self.newly_reproduced.value
            log.debug('avg_job_time_0 =', avg_job_time_0, 'avg_job_time_1 =', avg_job_time_1)

    def update_local_files(self):
        write_json(self.utils.get_error_reason_file_path(), Utils.deep_copy(self.error_reasons))
