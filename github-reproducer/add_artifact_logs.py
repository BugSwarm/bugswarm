import os
import sys
import logging

from bugswarm.common import log
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.rest_api.database_api import DatabaseAPI
from reproducer.config import Config
from reproducer.utils import Utils


class ArtifactLogAdder(object):
    def __init__(self, task_name):
        log.info('Initializing ArtifactLogAdder.')
        self.config = Config(task_name)
        self.utils = Utils(self.config)
        self.task = task_name

    def run(self):
        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)

        if os.path.isfile('../cache-dependency/output/{}.csv'.format(self.task)) is False:
            log.error(
                'cache-dependency output CSV does not exist for task {}'.format(self.task))
            sys.exit()

        cached_image_tags = set()
        with open('../cache-dependency/output/{}.csv'.format(self.task)) as f:
            for row in f:
                # This assumes format '<image tag>, <succeed/error>, <size>, <size increase>'
                row_list = row.split(', ')
                if row_list[1] == 'succeed':
                    cached_image_tags.add(row_list[0])

        for image_tag in cached_image_tags:
            response = bugswarmapi.find_artifact(image_tag)
            if not response.ok:
                log.error('Artifact not found: {}'.format(image_tag))
                continue

            artifact = response.json()
            job_id = {
                'failed': artifact['failed_job']['job_id'],
                'passed': artifact['passed_job']['job_id'],
            }

            job_orig_log = {
                'failed': os.getcwd() + '/' + self.utils.get_orig_log_path(job_id['failed']),
                'passed': os.getcwd() + '/' + self.utils.get_orig_log_path(job_id['passed']),
            }

            for f_or_p in ['failed', 'passed']:
                response = bugswarmapi.set_build_log(
                    str(job_id[f_or_p]), job_orig_log[f_or_p])
                if response.ok:
                    log.info('{} build log with ID {} successfully set for artifact: {}'
                             .format(f_or_p, job_id[f_or_p], image_tag))
                else:
                    log.error('Error {} attempting to set {} build log with ID {} set for artifact: {}'
                              .format(str(response), f_or_p, job_id[f_or_p], image_tag))


def main(argv=None):
    argv = argv or sys.argv

    if len(argv) != 2:
        log.info('Usage: add_artifact_logs.py <task_name>')
        sys.exit()

    log.config_logging(getattr(logging, 'INFO', None))

    task_name = argv[1]
    ArtifactLogAdder(task_name=task_name).run()


if __name__ == '__main__':
    sys.exit(main())
