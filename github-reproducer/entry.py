import getopt
import logging
import os
import sys

from bugswarm.common import log
from bugswarm.common.utils import get_current_component_version_message

from job_reproducer import JobReproducer
from image_packager import ImagePackager


def main(argv=None):
    argv = argv or sys.argv

    # Configure logging.
    log.config_logging(getattr(logging, 'INFO', None))

    # Log the current version of this BugSwarm component.
    log.info(get_current_component_version_message('Reproducer'))

    # Parse input.
    shortopts = 'i:t:o:kpds'
    longopts = 'input-file= threads= task-name= keep package skip-check-disk'.split()
    input_file = None
    threads = 1
    task_name = None
    keep = False
    package_mode = False
    dependency_solver = False
    skip_check_disk = False
    try:
        optlist, args = getopt.getopt(argv[1:], shortopts, longopts)
    except getopt.GetoptError:
        log.error('Error parsing arguments. Exiting.')
        print_usage()
        sys.exit(2)
    for opt, arg in optlist:
        if opt in ['-i', '--input-file']:
            input_file = arg
        if opt in ['-t', '--threads']:
            threads = int(arg)
        if opt in ['-o', '--task-name']:
            task_name = arg
        if opt in ['-k', '--keep']:
            keep = True
        if opt in ['-p', '--package']:
            package_mode = True
        if opt in ['-d', '--dependency-solver']:
            dependency_solver = True
        if opt in ['-s', '--skip-check-disk']:
            skip_check_disk = True

    if not input_file:
        print_usage()
        sys.exit(2)
    if threads <= 0:
        log.error('The threads argument must be greater than 0. Exiting.')
        sys.exit(1)
    if not os.path.isfile(input_file):
        log.error('The input_file argument is not a file or does not exist. Exiting.')
        sys.exit(1)
    if not task_name:
        print_usage()
        sys.exit(2)

    # Initialize JobDispatcher.
    # Pipeline will run JobReproducer (5 times) first, then it will run ImagePackager.
    if package_mode:
        reproducer = ImagePackager(input_file, task_name, threads, keep, package_mode, dependency_solver,
                                   skip_check_disk)
    else:
        reproducer = JobReproducer(input_file, task_name, threads, keep, package_mode, dependency_solver,
                                   skip_check_disk)
    reproducer.run()


def print_usage():
    log.info('Usage: python3 entry.py -i <input_file> -o <task_name> OPTIONS')
    log.info('{:<30}{:<30}'.format('-i, --input-file', 'Path to a JSON file containing fail-pass pairs to reproduce.'))
    log.info('{:<30}{:<30}'.format('-o, --task-name', 'Name of task folder.'))
    log.info('OPTIONS:')
    log.info('{:<30}{:<30}'.format('-t, --threads', 'Number of threads to use, defaults to 1.'))
    log.info('{:<30}{:<30}'.format('-k, --keep', 'Whether to skip deletion of repo files after running.'))
    log.info('{:<30}{:<30}'.format('-s, --skip-check-disk', 'Whether to check for free disk space.'))


if __name__ == '__main__':
    sys.exit(main())
