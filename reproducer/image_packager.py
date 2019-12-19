"""
ImagePackager is a JobDispatcher subclass responsible for pushing artifact images to Docker Hub.
"""

import time

from multiprocessing import Value

from bugswarm.common import log
from bugswarm.common.json import write_json
from termcolor import colored

from job_dispatcher import JobDispatcher
from reproducer.dockerhub_wrapper import DockerHub
from reproducer.model.jobpair import JobPair
from reproducer.package_jobpair_image import package_jobpair_image
from reproducer.pipeline.gen_files_for_job import gen_files_for_job
from reproducer.utils import Utils


class ImagePackager(JobDispatcher):
    """
    Subclass of JobDispatcher that packages Docker images for jobs.
    """

    def __init__(self, input_file, task_name, threads, keep, package_mode, dependency_solver):
        super().__init__(input_file, task_name, threads, keep, package_mode, dependency_solver)
        self.jobpairs_packaged = Value('i', 0)
        self.dockerhub = DockerHub()

    def progress_str(self):
        return colored(
            str(self.alive_threads) + ' alive threads, ' +
            str(self.job_center.total_jobpairs) + ' total pairs, ' +
            str(self.jobpairs_packaged.value) + ' packaged, ' +
            str(self.reproduce_err.value) + ' errors, ' +
            str(self.job_center.get_num_remaining_items(self.package_mode)) + ' remaining.', 'yellow')

    def process_item(self, item, tid):
        """
        First check whether this item can be skipped. We can skip when the item previously errored or when the image for
        this item already exists on Docker Hub. If the item cannot be skipped, then package the jobpair.
        :param item: Jobpair object
        :param tid: thread ID
        """
        self.items_processed.value += 1
        item.reproduced.value = 1

        # Do not push the image if reproducer encountered an error while reproducing the pair.
        if item.full_name in self.error_reasons:
            log.info('Previously encountered an error while reproducing a pair: {}.'
                     .format(self.error_reasons[item.full_name]))
            log.info('This pair will not be pushed to Docker Hub.')
            self.reproduce_err.value += 1
            return 0

        # Do not push the image if the pair is irreproducible.
        reproduce_successes, _, _ = self._calc_stability(item)
        if not reproduce_successes:
            log.info('This pair is not reproducible.')
            log.info('This pair will not be pushed to Docker Hub.')
            return 0

        # Otherwise, proceed with packaging.
        self._package_jobpair(item, tid)

    def _image_already_exists(self, image_tag) -> bool:
        _, result = self.dockerhub.image_exists(self.config.dockerhub_repo, image_tag)
        return result

    @staticmethod
    def _calc_stability(jobpair: JobPair):
        """
        Returns a string representing the proportion of times the job completed as expected. e.g. '3/5'.
        """
        assert jobpair
        matches = jobpair.match_history.values()
        # Count the number of times the job completed as expected.
        reproduce_successes = len([m for m in matches if m == 1])
        # Reproduce attempts excludes 'N' match types.
        reproduce_attempts = len([m for m in matches if str(m).isdigit()])
        assert reproduce_successes <= reproduce_attempts
        return reproduce_successes, reproduce_attempts, '{}/{}'.format(reproduce_successes, reproduce_attempts)

    def _package_jobpair(self, jobpair, tid):
        log.info('[THREAD {}] Running {}'.format(tid, jobpair.full_name))
        start_time = time.time()
        for j in jobpair.jobs:
            self.utils.setup_jobpair_dir(j)
            gen_files_for_job(self, j, True)
        # Create and push a Docker image to Docker Hub.
        package_jobpair_image(self.utils, self.docker, jobpair)
        elapsed = time.time() - start_time
        log.info(colored('[THREAD {}] Finished creating and pushing Docker image in {} seconds.'
                         .format(tid, int(elapsed)), 'green'))
        self.jobpairs_packaged.value += 1

    def record_error_reason(self, item, message):
        log.error('Encountered an error while creating an image and pushing it to Docker Hub:', message)
        self.error_reasons[item.full_name] = message

    def update_local_files(self):
        write_json(self.utils.get_error_reason_file_path(), Utils.deep_copy(self.error_reasons))
