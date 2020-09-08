import os
import subprocess
import sys
import time
import logging

from bugswarm.common import log
from bugswarm.common.artifact_processing.runners import ParallelArtifactRunner

_COPY_DIR = 'from_host'
_PROCESS_SCRIPT = 'process.py'
_MODIFY_POM_SCRIPT = 'modify_pom.py'
_POST_RUN_SCRIPT = 'post_run.py'


class ReproducePairRunner(ParallelArtifactRunner):
    def __init__(self, image_tags_file, workers):
        with open(image_tags_file) as f:
            image_tags = list(map(str.strip, f.readlines()))
        super().__init__(image_tags, workers)

    def process_artifact(self, pair_tuple_str: str):
        pair_tuple_str_split = pair_tuple_str.strip().split(',')
        if len(pair_tuple_str_split) != 3:
            print('Invalid line' + ''.join(pair_tuple_str_split))
            return None, None, 1
        repo_slug = pair_tuple_str_split[0]
        failed_job_id = pair_tuple_str_split[1]
        passed_job_id = pair_tuple_str_split[2]

        cmd = 'bash run_reproduce_pair.sh -r {} -f {} -p {} -t 2 --reproducer-runs 5 && ' \
              'rm -rf {} {} 2> /dev/null'.format(repo_slug, failed_job_id, passed_job_id,
                                                 'reproducer/intermediates/workspace/' + failed_job_id,
                                                 'reproducer/intermediates/workspace/' + passed_job_id)
        _, stdout, stderr, ok = _run_command(cmd)
        task_name = repo_slug.replace('/', '-')
        with open('reproducer/output/result_json/' + task_name + '_' + failed_job_id + '.out', 'w+') as f:
            f.write(stdout)
            f.write('ok: {}'.format(ok))
        with open('reproducer/output/result_json/' + task_name + '_' + failed_job_id + '.err', 'w+') as f:
            f.write(stderr)
        print('stdout: {}'.format(stdout))
        print('stderr: {}'.format(stderr))
        print('ok: {}'.format(ok))

        return stdout, stderr, ok


def _run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    return process, stdout, stderr, ok


def _print_usage():
    log.info('Usage: python3 run_reproduce_pair_wrapper.py <image_tags_file> <number_of_workers>')
    log.info('image_tags_file: Path to a file containing a newline-separated list of image tags to process.')
    log.info('number_of_works * 2 threads will be spawned since each pair contains a failed-job-id and a passed-job-id')


def _validate_input(argv):
    if len(argv) != 3:
        _print_usage()
        sys.exit(1)
    image_tags_file = argv[1]
    num_workers = int(argv[2])
    if not os.path.isfile(image_tags_file):
        log.error('The image_tags_file argument is not a file or does not exist. Exiting.')
        _print_usage()
        sys.exit(1)
    if num_workers <= 0:
        log.error('Number of workers must be greater than 0')
        sys.exit(1)
    return image_tags_file, num_workers


def main(argv=None):
    log.config_logging(getattr(logging, 'INFO', None))
    argv = argv or sys.argv

    image_tags_file, num_workers = _validate_input(argv)

    t_start = time.time()
    ReproducePairRunner(image_tags_file, workers=num_workers).run()
    t_end = time.time()
    print('Running run_reproduce_pair_wrapper took {}s'.format(t_end-t_start))


if __name__ == '__main__':
    sys.exit(main())
