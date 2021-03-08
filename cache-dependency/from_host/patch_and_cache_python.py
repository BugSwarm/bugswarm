import fileinput
import subprocess
import sys


def _run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    return process, stdout, stderr, ok


def _print_error(msg, stdout=None, stderr=None):
    print('Error: ' + msg)
    if stdout is not None:
        print('stdout:\n{}'.format(stdout))
    if stderr is not None:
        print('stderr:\n{}'.format(stderr))


def _get_dependency_list(pip_argument_list):
    package_list = []
    pip_version = pip_argument_list[1]
    idx = 3
    while idx < len(pip_argument_list):
        argument = pip_argument_list[idx]
        if argument == '-r':
            package_list.append('-r {}'.format(pip_argument_list[idx + 1]))
            idx += 1
        elif argument == '-e':
            idx += 1
        elif argument == '--assert':
            break
        elif argument[0] == '-':
            pass
        else:
            package_list.append(argument)
        idx += 1
    return pip_version, package_list


def main(argv=None):
    if argv is None:
        argv = sys.argv

    repo, f_or_p, build_script_fp = _validate_input(argv)
    package_cache_directory = '/home/travis/build/{}/{}'.format(f_or_p, 'requirements')
    for line in fileinput.input(build_script_fp, inplace=True):
        line = line.strip()
        if 'pip\\ install\\' in line:
            index = line.find('install\\ ') + len('install\\ ')
            line = line[:index] + '--no-index\\ --find-links={}\\ '.format(package_cache_directory) + line[index:]
            print(line)
        else:
            print(line)
    fileinput.close()

    print('Done')


def _print_usage():
    print('Usage: python patch_and_cache_maven.py <repo> <f_or_p>')


def _validate_input(argv):
    if len(argv) != 3:
        _print_usage()
        sys.exit(1)

    repo = argv[1]
    f_or_p = argv[2]
    build_script_fp = '/usr/local/bin/run_{}.sh'.format(f_or_p)

    if f_or_p not in ['failed', 'passed']:
        print('The f_or_p argument must be either "failed" or "passed". Exiting.')
        _print_usage()
        sys.exit(1)

    return repo, f_or_p, build_script_fp


if __name__ == '__main__':
    sys.exit(main())
