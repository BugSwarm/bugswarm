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


def setup_for_install(repo, f_or_p, build_script_fp):
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

    # Copy virtualenv tars if any and remove download from script
    _, stdout, _, ok = _run_command('ls {}/py*.tar.bz2'.format(package_cache_directory))
    if ok:
        for venv_download in stdout.splitlines():
            _run_command('cp {} /home/travis/build/'.format(venv_download))
            # Comment out the download line in the build script
            venv_download_name = venv_download.split('/')[-1]
            _run_command('sudo sed -i "/curl.*{}/s/^/#/" {}'.format(venv_download_name, build_script_fp))

    print('Done')


def setup_for_download(repo, f_or_p, build_script_fp):
    for line in fileinput.input(build_script_fp, inplace=True):
        line = line.strip()
        if 'pip\\ install\\' in line:
            index = line.find('pip\\ install\\')
            line = line[:index] + '/usr/local/bin/pip_install_wrapper.sh\\ ' + line[index:]
            print(line)
        else:
            print(line)
    fileinput.close()


def main(argv=None):
    if argv is None:
        argv = sys.argv

    repo, f_or_p, build_script_fp, d_or_i = _validate_input(argv)

    if d_or_i == 'install':
        setup_for_install(repo, f_or_p, build_script_fp)
    else:
        setup_for_download(repo, f_or_p, build_script_fp)


def _print_usage():
    print('Usage: python patch_and_cache_python.py <repo> <f_or_p> <d_or_i>')


def _validate_input(argv):
    if len(argv) != 4:
        _print_usage()
        sys.exit(1)

    repo = argv[1]
    f_or_p = argv[2]
    d_or_i = argv[3]
    build_script_fp = '/usr/local/bin/run_{}.sh'.format(f_or_p)

    if f_or_p not in ['failed', 'passed']:
        print('The f_or_p argument must be either "failed" or "passed". Exiting.')
        _print_usage()
        sys.exit(1)
    if d_or_i not in ['download', 'install']:
        print('The d_or_i argument must be either "download" or "install". Existing.')

    return repo, f_or_p, build_script_fp, d_or_i


if __name__ == '__main__':
    sys.exit(main())
