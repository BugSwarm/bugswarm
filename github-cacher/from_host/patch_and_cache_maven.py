import fileinput
import os.path
import re
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


def redirect_maven_installation(folderpath):
    """
    Copy mvn to mvn_ori, and then change mvn to a command that executes
    mvn_ori -o
    """
    pathname_mvn = os.path.join(folderpath, 'bin/mvn')
    pathname_ori = os.path.join(folderpath, 'bin/mvn_ori')
    if not os.path.exists(pathname_mvn):
        _print_error('{} does not exist. Skipping {}.'.format(pathname_mvn, folderpath))
        return
    if os.path.exists(pathname_ori):
        _print_error('{} already exists. Skipping {}.'.format(pathname_ori, folderpath))
        return
    _, stdout, stderr, ok = _run_command(
        'cp -a {} {}'.format(pathname_mvn, pathname_ori))
    if not ok:
        _print_error('Error copying files', stdout, stderr)
        exit(1)
    with open(pathname_mvn, 'w') as f:
        f.write('#!/bin/sh\n')
        f.write('echo Forcing mvn -o > /dev/stderr\n')
        f.write('{} -o "$@"\n'.format(pathname_ori))
        f.write('\n')


def redirect_gradle_installation(folderpath):
    """
    Copy gradle to gradle_ori, and then change gradle to a command that
    executes gradle_ori --offline
    """
    pathname_grd = os.path.join(folderpath, 'bin/gradle')
    pathname_ori = os.path.join(folderpath, 'bin/gradle_ori')
    assert os.path.exists(pathname_grd)
    assert not os.path.exists(pathname_ori)
    _, stdout, stderr, ok = _run_command(
        'cp -a {} {}'.format(pathname_grd, pathname_ori))
    if not ok:
        _print_error('Error copying files', stdout, stderr)
        exit(1)
    with open(pathname_grd, 'w') as f:
        f.write('#!/bin/sh\n')
        f.write('echo Forcing gradle --offline > /dev/stderr\n')
        f.write('{} --offline "$@"\n'.format(pathname_ori))
        f.write('\n')


def add_mvn_local_repo(repo):
    """Add <localRepository> to Maven configurations"""
    # Not needed in GHA repos
    # TODO remove this from the GitHub cacher
    return

    local_repository_path = '/home/travis/.m2/repository/'
    # Process `.travis.settings.xml` in project directory
    found = 0
    for f_or_p in ['failed', 'passed']:
        travis_xml_setting_file_path = '/home/travis/build/{}/{}/.travis.settings.xml'.format(f_or_p, repo)
        if not os.path.exists(travis_xml_setting_file_path):
            continue
        found += 1
        setting_dom = parse(travis_xml_setting_file_path)
        setting_element = setting_dom.getElementsByTagName('settings').item(0)
        if not setting_dom.getElementsByTagName('localRepository'):
            insert_element = setting_dom.createElement('localRepository')
            insert_element.appendChild(setting_dom.createTextNode(local_repository_path))
            setting_element.appendChild(insert_element)
            file = open(travis_xml_setting_file_path, 'w')
            setting_dom.writexml(file, encoding='utf-8')
            file.close()
    # Process `~/.m2/settings.xml`
    travis_xml_setting_file_path = '/home/travis/.m2/settings.xml'
    if not os.path.exists(travis_xml_setting_file_path):
        if found != 2:
            raise Exception('Cannot modify Maven settings correctly')
        print('Warning: ~/.m2/settings.xml not found')
    else:
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

        for f_or_p in ('failed', 'passed'):
            output_file = '/home/travis/.m2/{}_settings.xml'.format(f_or_p)
            with open(output_file, 'w+') as file:
                setting_dom.writexml(file, encoding='utf-8')

            for line in fileinput.input('/usr/local/bin/run_{}.sh'.format(f_or_p), inplace=True):
                if line.strip() == '#!/bin/bash':
                    print(line)
                    print('cp {} {}'.format(output_file, travis_xml_setting_file_path))
                else:
                    print(line)
            fileinput.close()


def offline_all_maven():
    """Replace all occurrences of mvn binary to add the offline flag"""
    usr_share = '/usr/share'
    for folder in os.listdir(usr_share):
        if not folder.startswith('maven') and not folder.startswith('apache-maven'):
            continue
        folderpath = os.path.join(usr_share, folder)
        if not os.path.isdir(folderpath) or os.path.islink(folderpath):
            # e.g. /usr/local/maven may be a symbolic link to maven-3.5.2
            continue
        print('redirect_maven_installation for {}'.format(folderpath))
        redirect_maven_installation(folderpath)
        # Looks like ./mvnw will still use system-installed scripts
    """Add offline flag to settings.xml"""
    if not os.path.exists('/home/github/.m2'):
        os.mkdir('/home/github/.m2')
    with open('/home/github/.m2/settings.xml', 'w') as f:
        f.write('<settings><offline>true</offline></settings>')


def offline_all_gradle():
    """Replace all occurrences of gradle binary to add the offline flag"""
    usr_local = '/usr/local/'
    for folder in os.listdir(usr_local):
        if not folder.startswith('gradle'):
            continue
        folderpath = os.path.join(usr_local, folder)
        if not os.path.isdir(folderpath) or os.path.islink(folderpath):
            continue
        print('redirect_gradle_installation for {}'.format(folderpath))
        redirect_gradle_installation(folderpath)
    """Add offline flag to init.gradle"""
    if not os.path.exists('/home/github/.gradle'):
        os.mkdir('/home/github/.gradle')
    with open('/home/github/.gradle/init.gradle', 'w') as f:
        f.write('startParameter.offline=true')


def offline_maven():
    """Traditional way to add offline mode to Maven"""
    mvn_regex = re.compile(r'(?<![\w] )\b(mvnw?)\b')  # the words 'mvn' or 'mvnw'
    for f_or_p in ['failed', 'passed']:
        is_user_command = False
        for line in fileinput.input('/usr/local/bin/run_{}.sh'.format(f_or_p), inplace=True):
            if is_user_command and re.match(r'^chmod u\+x /home/github/', line):
                is_user_command = False
            elif not is_user_command and re.match(r'^echo \"##\[group\]\"Run', line):
                is_user_command = True

            # line = line.strip()

            # Replace every instance of mvn or mvnw with 'mvn -o' and 'mvnw -o' respectively
            # This is a very coarse method; a better method may be possible.
            if is_user_command:
                line = mvn_regex.sub(r'\1 -o', line)
            print(line, end='')
    fileinput.close()


def offline_gradle():
    """
    Add --offline flag to all instances of "gradle". This is a very
    coarse method, like offline_maven(); it may be worth it to look
    into more fine-grained methods.
    """

    for f_or_p in ('failed', 'passed'):
        is_user_command = False
        for line in fileinput.input('/usr/local/bin/run_{}.sh'.format(f_or_p), inplace=True):
            if is_user_command and re.match(r'^chmod u\+x /home/github/', line):
                is_user_command = False
            elif not is_user_command and re.match(r'^echo \"##\[group\]\"Run', line):
                is_user_command = True

            if is_user_command:
                line = re.sub(r'(?<![\w] )\b(gradlew?)\b', r'\1 --offline', line)
            print(line, end='')
        fileinput.close()


def main(argv=None):
    if argv is None:
        argv = sys.argv

    repo, actions = _validate_input(argv)

    if 'add-mvn-local-repo' in actions:
        add_mvn_local_repo(repo)
    if 'offline-all-maven' in actions:
        offline_all_maven()
    if 'offline-all-gradle' in actions:
        offline_all_gradle()
    if 'offline-maven' in actions:
        offline_maven()
    if 'offline-gradle' in actions:
        offline_gradle()


def _print_usage():
    print('Usage: sudo python patch_and_cache_maven.py <repo> [<actions> [...]]')
    print('Possible actions: add-mvn-local-repo, offline-all-maven, offline-all-gradle')
    print('    add-mvn-local-repo: add <localRepository> to Maven configurations')
    print('    offline-all-maven: Replace all occurrences of mvn binary to add the offline flag')
    print('    offline-all-gradle: Replace all occurrences of gradle binary to add the offline flag')
    print('    offline-maven: Add the -o flag to all instances of mvn(w) in the build script')
    print('    offline-gradle: Add the --offline flag to all instances of gradle(w) in the build script')


def _validate_input(argv):
    if len(argv) <= 2:
        _print_usage()
        sys.exit(1)

    repo = argv[1]
    actions = argv[2:]

    for action in actions:
        if action not in ['add-mvn-local-repo', 'offline-all-maven', 'offline-all-gradle',
                          'offline-maven', 'offline-gradle']:
            _print_usage()
            raise Exception('Unknown action: {}'.format(action))

    if os.getuid() != 0:
        raise Exception('Need to run this script as root')

    return repo, actions


if __name__ == '__main__':
    sys.exit(main())
