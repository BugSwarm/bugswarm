import os
import time

from multiprocessing import Lock
from multiprocessing import Manager
from multiprocessing import Process
from multiprocessing import Value
from typing import Optional

from bugswarm.common import log
from bugswarm.common.json import read_json
from termcolor import colored

from reproducer.config import Config
from reproducer.docker_wrapper import DockerWrapper
from reproducer.pair_center import PairCenter
from reproducer.reproduce_exception import ReproduceError
from reproducer.utils import Utils


class JobDispatcher(object):
    """
    JobDispatcher controls the entire reproducing workflow by dispatching tasks to a pool of worker threads.
    Subclasses determine the specific task.
    """

    def __init__(self, input_file, task_name, threads=1, keep=False, package_mode=False, dependency_solver=False,
                 skip_check_disk=False):
        """
        Initializes JobDispatcher with user specified input and starts work.
        If `threads` is specified, JobDispatcher will dispatch jobs to be reproduced in each thread. Otherwise, each job
        will be reproduced sequentially.
        """
        log.info('Initializing job dispatcher.')
        self.input_file = input_file
        self.thread_num = threads
        self.keep = keep
        self.package_mode = package_mode
        self.dependency_solver = dependency_solver
        # -----
        self.config = Config(task_name)
        self.config.skip_check_disk = skip_check_disk
        self.utils = Utils(self.config)
        self.items_processed = Value('i', 0)
        self.reproduce_err = Value('i', 0)
        self.job_time_acc = 0
        self.start_time = time.time()
        self.docker = DockerWrapper(self.utils)
        self.docker_storage_path = self.docker.setup_docker_storage_path()
        self.terminate = Value('i', 0)
        self.manager = Manager()
        self.lock = Lock()
        self.workspace_locks = self.manager.dict()
        self.cloned_repos = self.manager.dict()
        self.threads = {}
        self.error_reasons = {}
        self.alive_threads = 0
        self.travis_images = None
        self.job_center = PairCenter(self.input_file, self.utils, self.package_mode)

    def run(self):
        """
        The entry point for reproducing jobs. Calls post_run() after all items are processed.

        Subclasses must not override this method.
        """
        self._base_pre_run()
        self.pre_run()
        try:
            while self.job_center.get_num_remaining_items(self.package_mode):
                log.info('Ready to initialize threads.')
                if not self.utils.check_disk_space_available():
                    self.utils.clean_disk_usage(self)
                    if not self.utils.check_disk_space_available():
                        msg = 'Still inadequate disk space after removing temporary Reproducer files. Exiting.'
                        log.error(msg)
                        raise OSError(msg)
                if not self.utils.check_docker_disk_space_available(self.docker_storage_path):
                    self.utils.clean_docker_disk_usage(self.docker)
                    if not self.utils.check_docker_disk_space_available(self.docker_storage_path):
                        msg = 'Still inadequate disk space after removing inactive Docker Images. Exiting.'
                        log.error(msg)
                        raise OSError(msg)
                self._init_threads()
        except KeyboardInterrupt:
            log.info('Caught KeyboardInterrupt. Cleaning up before terminating.')
            self.terminate.value = 1
        else:
            self.post_run()
            log.info('Done!')
        finally:
            log.info(self.progress_str())

    def _spawn(self, tid):
        t = Process(target=self._thread_main, args=(tid,))
        thread = {'process': t, 'exit_reason': ''}
        self.threads[tid] = thread
        t.start()

    def _thread_watcher(self):
        """
        Repeatedly check if process is alive.
        """
        log.info('Initialized', len(self.threads), 'threads.')
        count = 0
        old_str = self.progress_str()
        while True:
            time.sleep(3)
            count += 1
            if count == 6:
                count = 0
                self.update_local_files()  # Update local files every 3*6 seconds.
                if self.terminate.value:
                    log.info(colored('Waiting for threads...', 'blue'))
                # elif not self.utils.check_disk_space_available():
                #     log.warning(colored('Not enough disk space. Joining threads...', 'yellow'))
                #     self.terminate.value = 1

            alive_threads = 0
            for tid in self.threads:
                p = self.threads[tid]['process']
                if p.is_alive():
                    alive_threads += 1
                else:
                    if p.exitcode is None:  # Not finished and not running.
                        # Do error handling and restarting here assigning the new process to processes[n].
                        self.threads[tid]['exit_reason'] = 'not finished and not running'
                        self._spawn(tid)
                    elif p.exitcode != 0:
                        self.threads[tid]['exit_reason'] = 'errored or terminated'
                        # Handle this either by restarting or deleting the entry so it is removed from list.
                        self._spawn(tid)
                    else:
                        self.threads[tid]['exit_reason'] = 'finished'
                        self.terminate.value = 1
                        p.join()  # Allow cleanup.

            self.alive_threads = alive_threads
            if not alive_threads:
                break

            curr_str = self.progress_str()
            if curr_str != old_str:
                old_str = curr_str
                if curr_str:
                    log.info(curr_str)

    def _init_threads(self):
        """
        Initialize min(num_threads, number of jobs to reproduce) threads.
        """
        self.lock = Lock()
        self.workspace_locks = self.manager.dict()
        self.cloned_repos = self.manager.dict()
        self.threads = {}
        self.terminate.value = 0
        num_remaining_items = self.job_center.get_num_remaining_items(self.package_mode)
        if not num_remaining_items:
            log.info('No remaining items. Exiting.')
            return 0
        self.thread_num = min(self.thread_num, num_remaining_items)
        self.job_center.init_queues_for_threads(self.thread_num, self.package_mode)
        # Begin initializing threads.
        for tid in range(self.thread_num):
            self._spawn(tid)
        self._thread_watcher()

    def _thread_main(self, tid):
        """
        This is the target function for each thread.
        It receives the work load (a queue) for a given thread from job_center.thread_workloads.
        For each item, it calls self.process_item() to run.
        :param tid: Thread ID
        """
        workload = self.job_center.thread_workloads[tid]
        while not workload.empty():
            # Break out of the loop if the terminate flag is set.
            if self.terminate.value:
                return 0
            item = workload.get()

            # Intentionally catch ReproduceError but allow KeyboardInterrupt to propagate.
            try:
                self.process_item(item, tid)
            except ReproduceError as e:
                log.info(colored('[THREAD {}] {} {}'.format(tid, item, e), 'red'))
                self.reproduce_err.value += 1
                self.record_error_reason(item, str(e))
                # Optionally handle failed reproducing here.
        log.info('[THREAD {}] Workload complete. Exiting thread.'.format(tid))

    def _base_pre_run(self):
        if self.job_center.total_jobs < 1:
            log.info('No jobs to reproduce. Exiting.')
            return

        # Set up the required directories.
        os.makedirs(self.config.orig_logs_dir, exist_ok=True)
        os.makedirs(self.config.output_dir, exist_ok=True)
        self.utils.directories_setup()
        if os.path.isfile(self.utils.get_error_reason_file_path()):
            self.error_reasons = read_json(self.utils.get_error_reason_file_path())
        self.error_reasons = self.manager.dict(self.error_reasons)

        # TODO: Remove this
        # Check if commands to Travis work.
        """
        if not Utils.is_travis_installed():
            log.error(colored('Commands to Travis are failing unexpectedly. Try restarting your shell and ensure your '
                              'environment is provisioned correctly. Also try restarting your shell.', 'red'))
            raise Exception('Unexpected state: Commands to Travis are failing unexpectedly.')
        # Read travis_images.json.
        try:
            self.travis_images = read_json(self.config.travis_images_json)
        except FileNotFoundError:
            log.error(colored(self.config.travis_images_json + ' not found. Exiting.', 'red'))
            raise
        """

    def pre_run(self):
        """
        Called before any items have been processed.

        Overriding is optional. Defaults to no-op.
        """
        pass

    def progress_str(self) -> Optional[str]:
        """
        Subclasses should return a string, which will be logged, representing progress at the time the method is called.
        Returns None by default, which indicates to the caller that logging the progress should be skipped.

        Overriding is optional.
        :return: A string representing the dispatcher's progress or None to skip logging the progress.
        """
        return None

    def update_local_files(self):
        """
        Called periodically to allow the dispatcher to update local files as needed.

        Overriding is optional. Defaults to no-op.
        """
        pass

    def process_item(self, item, tid):
        """
        Subclasses must override this method to process each item in the workload.
        :param item: The item to process.
        :param tid: The thread ID tasked with processing the item.
        """
        raise NotImplementedError

    def record_error_reason(self, item, message):
        """
        Overriding is optional. Defaults to no-op.
        :param item: The item for which to record an error message.
        :param message: The error message to record.
        """
        pass

    def post_run(self):
        """
        Called after all items have been processed.

        Overriding is optional. Defaults to no-op.
        """
        pass
