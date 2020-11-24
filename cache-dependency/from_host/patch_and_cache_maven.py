import fileinput
import os.path
import subprocess
import sys
from xml.dom.minidom import parse


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


def main(argv=None):
    if argv is None:
        argv = sys.argv

    repo, f_or_p, build_script_fp, option, package_mode = _validate_input(argv)
    travis_xml_setting_file_path = '/home/travis/build/{}/{}/.travis.settings.xml'.format(f_or_p, repo)
    local_repository_path = '/home/travis/.m2/{}/'.format(f_or_p)

    # no .travis.settings.xml the build script will use default local
    if not os.path.exists(travis_xml_setting_file_path):
        travis_xml_setting_file_path = '/home/travis/.m2/settings.xml'
        setting_dom = parse(travis_xml_setting_file_path)
        setting_element = setting_dom.getElementsByTagName('settings').item(0)

        existing_nodes = setting_dom.getElementsByTagName('localRepository')
        if existing_nodes:
            for node in existing_nodes:
                parent = node.parentNode
                parent.removeChild(node)

        insert_element = setting_dom.createElement('localRepository')
        insert_element.appendChild(setting_dom.createTextNode(local_repository_path))
        setting_element.appendChild(insert_element)
        output_file = '/home/travis/.m2/{}_settings.xml'.format(f_or_p)
        file = open(output_file, 'w+')
        setting_dom.writexml(file, encoding='utf-8')
        file.close()

        for line in fileinput.input('/usr/local/bin/run_{}.sh'.format(f_or_p), inplace=True):
            if line.strip() == '#!/bin/bash':
                print(line.strip())
                print('cp {} {}'.format(output_file, travis_xml_setting_file_path))
            else:
                print(line.strip())
        fileinput.close()
    else:
        setting_dom = parse(travis_xml_setting_file_path)
        setting_element = setting_dom.getElementsByTagName('settings').item(0)
        if not setting_dom.getElementsByTagName('localRepository'):
            insert_element = setting_dom.createElement('localRepository')
            insert_element.appendChild(setting_dom.createTextNode(local_repository_path))
            setting_element.appendChild(insert_element)
            file = open(travis_xml_setting_file_path, 'w')
            setting_dom.writexml(file, encoding='utf-8')
            file.close()

    print('Apply caching')
    # Approach 1: using dependency resolve
    if option == 'offline':
        line_idx = -1
        for idx, line in enumerate(fileinput.input('/usr/local/bin/run_{}.sh'.format(f_or_p), inplace=True), 0):
            line = line.strip()
            if line.startswith('travis_cmd mvn\\ install'):
                line_idx = idx
                print('travis_cmd mvn\\ dependency:go-offline')
                print('exit 0')
            print(line)
        fileinput.close()
        # run it
        run_command = 'bash /usr/local/bin/run_{}.sh'.format(f_or_p)
        _, stdout, stderr, ok = _run_command(run_command)

        # Make sure write permissions are still active
        _, stdout, stderr, ok = _run_command('sudo chmod -R o+w /usr/local/bin/')

        # Revert the change
        if line_idx != -1:
            for idx, line in enumerate(fileinput.input('/usr/local/bin/run_{}.sh'.format(f_or_p), inplace=True), 0):
                line = line.strip()
                if idx == line_idx:
                    continue
                elif idx == line_idx + 1:
                    continue
                else:
                    print(line)
            fileinput.close()

    # Approach 2: build the target
    if option == 'build':
        run_command = 'bash /usr/local/bin/run_{}.sh'.format(f_or_p)
        _, stdout, stderr, ok = _run_command(run_command)

        # Make sure write permissions are still active
        _, stdout, stderr, ok = _run_command('sudo chmod -R o+w /usr/local/bin/')

    # enable offline
    for line in fileinput.input('/usr/local/bin/run_{}.sh'.format(f_or_p), inplace=True):
        line = line.strip()
        if line.startswith('travis_cmd mvn\\ install'):
            index = line.find('install\\')
            line = line[:index] + '-o\\ ' + line[index:]
        print(line)
    fileinput.close()

    print('Ran build script')

    if not package_mode:
        run_command = 'bash /usr/local/bin/run_{}.sh > /home/travis/log-{}.log'.format(f_or_p, f_or_p)
        _, stdout, stderr, ok = _run_command(run_command)
        print('Ran the {} build script.'.format(f_or_p))

    print('Done')


def _print_usage():
    print(
        'Usage: python patch_and_cache_maven.py <repo> <f_or_p> <option> <package_mode>')


def _validate_input(argv):
    if len(argv) != 5:
        _print_usage()
        sys.exit(1)

    repo = argv[1]
    f_or_p = argv[2]
    build_script_fp = '/usr/local/bin/run_{}.sh'.format(f_or_p)
    option = argv[3]
    package_mode = argv[4] == 'True'

    if f_or_p not in ['failed', 'passed']:
        print('The f_or_p argument must be either "failed" or "passed". Exiting.')
        _print_usage()
        sys.exit(1)

    return repo, f_or_p, build_script_fp, option, package_mode


if __name__ == '__main__':
    sys.exit(main())
