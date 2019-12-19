"""
This script filters out pairs in which the failing build does not have at least one failing test. It takes as input
two arguments:
  1. job_pair_file: A CSV file that is newline separated that has the format: project_name,failing_job_id,passing_job_id
  2. output_file: A path to a file that will have the filters pairs written to

Usage: python3 python process.py <job_pair_file> <output_file>

Requirements:
  1. This script is run with Python 3.x.
  2. bugswarm-common is installed
  3. bugswarm-analyzer is installed
"""

import os
import sys
import tempfile

from bugswarm.analyzer.analyzer import Analyzer
from bugswarm.common import log
from bugswarm.common import log_downloader


def main(argv=None):
    argv = argv or sys.argv

    job_pair_file, output_file = _validate_input(argv)

    log_list = []
    log_dict = {}
    logs_with_fail_tests = []

    # Make temp directory to store downloaded logs
    with tempfile.TemporaryDirectory() as tmpdirname:

        # Download the failing log for each build in the csv file
        with open(job_pair_file) as jp_file:
            for line in jp_file:
                line_split = line.strip().split(',')
                project_name = line_split[0].replace('/', '-')
                failing_job_id = line_split[1]
                passing_job_id = line_split[2]

                log_filename = '{}-{}'.format(project_name, failing_job_id)
                log_path = os.path.join(tmpdirname, log_filename)

                # Download the log
                if log_downloader.download_log(failing_job_id, log_path):
                    log_list.append(log_path)
                    log_dict[log_path] = '{},{},{}'.format(project_name, failing_job_id, passing_job_id)
                else:
                    log.error('Error trying to download: {}'.format(log_filename))

        # Run Analyzer on each log and filter
        analyzer = Analyzer()
        for fail_log in log_list:
            result = analyzer.analyze_single_log(fail_log)['tr_log_num_tests_failed']

            try:
                result_int = int(result)
            # Catch NA's and set to 0
            except ValueError:
                result_int = 0

            if result_int > 0:
                logs_with_fail_tests.append(fail_log)

        # Write out the logs that have at least one failing test
        with open(output_file, 'w') as out_file:
            for fail_log in logs_with_fail_tests:
                out_file.write('{}\n'.format(log_dict[fail_log]))


def _print_usage():
    print('Usage: python3 process.py <job_pair_file> <output_file>')


def _validate_input(argv):
    if len(argv) != 3:
        _print_usage()
        sys.exit(1)
    job_pair_file = argv[1]

    if not os.path.isfile(job_pair_file):
        log.error('The job_pair_file argument is not a file or does not exist. Exiting.')
        _print_usage()
        sys.exit(1)

    output_file = argv[2]

    return job_pair_file, output_file


if __name__ == '__main__':
    sys.exit(main())
