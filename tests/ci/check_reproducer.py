import os
import sys
import json


def verify_log(src, is_failed):
    try:
        with open(src) as f:
            lines = f.readlines()
            for line in reversed(lines):
                if line.startswith('##[error]'):
                    return (is_failed, lines)
                if line.startswith('##Test passed'):
                    return (not is_failed, lines)
            return False, lines
    except BaseException:
        pass
    return False, None


def main():
    jobpairs = []
    with open('test.json') as f:
        data = json.load(f)
        for buildpair in data:
            for jobpair in buildpair['jobpairs']:
                jobpairs.append((buildpair['repo'],
                                 buildpair['failed_build']['build_id'],
                                 buildpair['passed_build']['build_id'],
                                 jobpair['failed_job']['job_id'],
                                 jobpair['passed_job']['job_id']))

    print('Checking {} jobpairs'.format(len(jobpairs)))

    failed_test = 0
    for jobpair in jobpairs:
        subdir1 = '-1-{}-{}'.format(jobpair[1], jobpair[2])
        subdir2 = '{}-{}'.format(jobpair[3], jobpair[4])
        log_dir = os.path.join('output', 'tasks', 'test', jobpair[0], subdir1, subdir2)

        log_path = os.path.join(log_dir, '{}.log'.format(jobpair[3]))
        success, log = verify_log(log_path, True)
        if not success:
            failed_test += 1
            print(log_path + ' failed, expected failed log, got passed log.')
            print(log)
            print('\n\n')

        log_path = os.path.join(log_dir, '{}.log'.format(jobpair[4]))
        success, log = verify_log(log_path, False)
        if not success:
            failed_test += 1
            print(log_path + ' failed, expected passed log, got failed log.')
            print(log)
            print('\n\n')

    if failed_test > 0:
        print('Reproducer failed {} tests'.format(failed_test))
        exit(1)
    else:
        print('Reproducer test passed!')


if __name__ == "__main__":
    sys.exit(main())
