import os
import docker
import shutil
import unittest
import subprocess
from os.path import dirname, join


DATA_DIR = join(dirname(__file__), 'data')
SANDBOX_DIR = join(dirname(__file__), 'test-sandbox')
FROM_HOST = join(dirname(__file__), '..', 'from_host')
IN_CONTAINER = os.environ.get('IN_CONTAINER', False)


class CacheGitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree(SANDBOX_DIR, ignore_errors=True)
        os.makedirs(SANDBOX_DIR)
        shutil.copytree(FROM_HOST, join(SANDBOX_DIR, 'from_host'))

    def setUp(self):
        if IN_CONTAINER:
            self.run_command(['sudo', 'mkdir', '-p', '/home/github'])
            self.run_command(['sudo', 'mv', '/usr/bin/git', '/usr/bin/git_original'])

            self.copy(src=join(FROM_HOST, 'wrapper_scripts', 'git.py'), dest='/usr/bin/git')
            self.run_command(['sudo', 'chmod', '777', '/usr/bin/git'])

            self.owd = os.getcwd()
            os.chdir('/tmp')
        else:
            client = docker.from_env()
            self.container = client.containers.run('bugswarm/githubactionsjobrunners:ubuntu-20.04',
                                                   tty=True, detach=True, remove=False)
            self.container.exec_run(['mv', '/usr/bin/git', '/usr/bin/git_original'])
            self.container.exec_run(['mkdir', '-p', '/home/github'])

            self.copy(src=join(FROM_HOST, 'wrapper_scripts', 'git.py'), dest='/usr/bin/git')
            self.container.exec_run(['chmod', '777', '/usr/bin/git'])

    def tearDown(self):
        try:
            self.container.remove(force=True)
        except AttributeError:
            self.run_command(['sudo', 'rm', '-rf', '/home/github'])
            self.run_command(['sudo', 'mv', '/usr/bin/git_original', '/usr/bin/git'])

            os.chdir(self.owd)
            self.run_command(['sudo', 'rm', '-rf', '/tmp'])
            self.run_command(['mkdir', '-p', '/tmp'])

    def run_command(self, command):
        if isinstance(command, list):
            command = ' '.join(command)
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=True)
        stdout, stderr = process.communicate()
        stdout = stdout.decode('utf-8').strip()
        stderr = stderr.decode('utf-8').strip()
        return_code = process.returncode
        return process, stdout, stderr, return_code

    def copy(self, src, dest):
        try:
            self.run_command('docker cp {} {}:{}'.format(src, self.container.id, dest))
        except AttributeError:
            shutil.copy(src, dest)

    def test_git_clone(self):
        # git clone twice, first without directory, then with directory
        clone_command = ['git', 'clone', 'https://github.com/guan-kevin/git-submodule-test']
        ls_command = ['ls', 'git-submodule-test']

        try:
            self.container.exec_run(clone_command)
            ls_result = self.container.exec_run(ls_command).decode()
        except AttributeError:
            self.run_command(clone_command)
            _, ls_result, _, _ = self.run_command(ls_command)

        self.assertIn('test.sh', ls_result)

        clone_command = ['git', 'clone', 'https://github.com/guan-kevin/git-submodule-test', 'repo']
        ls_command = ['ls', 'repo']

        try:
            verify_command = ['grep', 'Cache hit', '/home/github/cacher/git-output.log']

            self.container.exec_run(clone_command)
            ls_result = self.container.exec_run(ls_command).decode()
            grep_result = self.container.exec_run(verify_command).decode()
        except AttributeError:
            verify_command = ['grep', '"Cache hit"', '/home/github/cacher/git-output.log']

            self.run_command(clone_command)
            _, ls_result, _, _ = self.run_command(ls_command)
            _, grep_result, _, _ = self.run_command(verify_command)

        self.assertIn('test.sh', ls_result)
        self.assertTrue(len(grep_result.strip()) == len('Cache hit'))

    def test_git_clone_2(self):
        # git clone twice, first with directory, then without directory
        clone_command = ['git', 'clone', 'https://github.com/guan-kevin/git-submodule-test', 'repo']
        ls_command = ['ls', 'repo']

        try:
            self.container.exec_run(clone_command)
            ls_result = self.container.exec_run(ls_command).decode()
        except AttributeError:
            self.run_command(clone_command)
            _, ls_result, _, _ = self.run_command(ls_command)

        self.assertIn('test.sh', ls_result)

        clone_command = ['git', 'clone', 'https://github.com/guan-kevin/git-submodule-test']
        ls_command = ['ls', 'git-submodule-test']

        try:
            verify_command = ['grep', 'Cache hit', '/home/github/cacher/git-output.log']

            self.container.exec_run(clone_command)
            ls_result = self.container.exec_run(ls_command).decode()
            grep_result = self.container.exec_run(verify_command).decode()
        except AttributeError:
            verify_command = ['grep', '"Cache hit"', '/home/github/cacher/git-output.log']

            self.run_command(clone_command)
            _, ls_result, _, _ = self.run_command(ls_command)
            _, grep_result, _, _ = self.run_command(verify_command)

        self.assertIn('test.sh', ls_result)
        self.assertEqual(grep_result.strip(), 'Cache hit')

    def test_git_submodule(self):
        # git clone twice, first without directory, then with directory
        clone_command = ['git', 'clone', 'https://github.com/guan-kevin/git-submodule-test']
        ls_client_command = ['ls', 'git-submodule-test/client']
        ls_common_command = ['ls', 'git-submodule-test/common']

        try:
            submodule_command = ['bash', '-c', 'cd git-submodule-test; git submodule update --init']

            self.container.exec_run(clone_command)
            self.container.exec_run(submodule_command)

            ls_client_result = self.container.exec_run(ls_client_command).decode()
            ls_common_result = self.container.exec_run(ls_common_command).decode()
        except AttributeError:
            submodule_command = 'bash -c "ls; cd git-submodule-test; git submodule update --init; cd .."'

            self.run_command(clone_command)
            self.run_command(submodule_command)

            _, ls_client_result, _, _ = self.run_command(ls_client_command)
            _, ls_common_result, _, _ = self.run_command(ls_common_command)

        self.assertIn('requirements.txt', ls_client_result)
        self.assertIn('requirements.txt', ls_common_result)

        clone_command = ['git', 'clone', 'https://github.com/guan-kevin/git-submodule-test', 'repo']
        ls_client_command = ['ls', 'repo/client']
        ls_common_command = ['ls', 'repo/common']

        try:
            submodule_command = ['bash', '-c', 'cd repo; git submodule update --init']
            verify_command = ['grep', 'Cache hit', '/home/github/cacher/git-output.log']

            self.container.exec_run(clone_command)
            self.container.exec_run(submodule_command)

            ls_client_result = self.container.exec_run(ls_client_command).decode()
            ls_common_result = self.container.exec_run(ls_common_command).decode()

            grep_result = self.container.exec_run(verify_command).decode()
        except AttributeError:
            submodule_command = 'bash -c "ls; cd repo; git submodule update --init; cd .."'
            verify_command = ['grep', '"Cache hit"', '/home/github/cacher/git-output.log']

            self.run_command(clone_command)
            self.run_command(submodule_command)

            _, ls_client_result, _, _ = self.run_command(ls_client_command)
            _, ls_common_result, _, _ = self.run_command(ls_common_command)

            _, grep_result, _, _ = self.run_command(verify_command)

        self.assertIn('requirements.txt', ls_client_result)
        self.assertIn('requirements.txt', ls_common_result)

        self.assertEqual(grep_result.strip(), 'Cache hit\nCache hit')
