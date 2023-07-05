import logging
import os
import re
import sys
import time
from packaging import version

from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from python_log_parser import parse_log

from bugswarm.common import log
from bugswarm.common.artifact_processing import utils as procutils
from bugswarm.common.rest_api.database_api import DatabaseAPI
from utils import PatchArtifactTask, PatchArtifactRunner, validate_input, CachingScriptError

_COPY_DIR = 'from_host'
_PROCESS_SCRIPT = 'patch_and_cache_python.py'
_DEPENDENCY_DOWNLOAD_SCRIPT = 'download_python_dependencies.sh'
_PIP_INSTALL_WRAPPER_SCRIPT = 'pip_install_wrapper.sh'
_FAILED_BUILD_SCRIPT = '/usr/local/bin/run_failed.sh'
_PASSED_BUILD_SCRIPT = '/usr/local/bin/run_passed.sh'
_TRAVIS_DIR = '/home/travis'

bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)


class PatchArtifactPythonTask(PatchArtifactTask):
    def cache_artifact_dependency(self):
        response = bugswarmapi.find_artifact(self.image_tag)
        if not response.ok:
            raise CachingScriptError('Unable to get artifact data')

        artifact = response.json()
        job_id = {
            'failed': artifact['failed_job']['job_id'],
            'passed': artifact['passed_job']['job_id'],
        }
        repo = artifact['repo']

        job_orig_log = {
            'failed': '{}/orig-failed-{}.log'.format(self.workdir, job_id['failed']),
            'passed': '{}/orig-passed-{}.log'.format(self.workdir, job_id['passed']),
        }
        for f_or_p in ['failed', 'passed']:
            try:
                content = bugswarmapi.get_build_log(str(job_id[f_or_p]))
                with open(job_orig_log[f_or_p], 'w') as f:
                    f.write(content)
            except Exception:
                raise CachingScriptError(
                    'Error getting log for {} job {}'.format(f_or_p, job_id[f_or_p]))

        docker_image_tag = '{}:{}'.format(self.args.src_repo, self.image_tag)
        original_size = self.pull_image(docker_image_tag)

        if self.args.parse_original_log or self.args.parse_new_log:
            self.parse_log_download_dependencies(job_id, job_orig_log, docker_image_tag)
        else:
            self.pip_freeze_download_dependencies(repo, job_id, job_orig_log, docker_image_tag)

        cached_tag = self.move_dependencies_to_new_container_and_patch(repo, docker_image_tag)

        # Start two runs to test cached image
        test_build_log_path = {
            'failed': '{}/test-failed.log'.format(self.workdir),
            'passed': '{}/test-passed.log'.format(self.workdir),
        }
        for fail_or_pass in ['failed', 'passed']:
            container_id = self.create_container(cached_tag, 'test', fail_or_pass)
            build_result = self.run_build_script(container_id, fail_or_pass, test_build_log_path[fail_or_pass],
                                                 job_orig_log[fail_or_pass], job_id[fail_or_pass], None)
            if not build_result:
                raise CachingScriptError('Run build script not reproducible for testing {}'.format(fail_or_pass))

        # Push image
        latest_layer_size = self.get_last_layer_size(cached_tag)
        self.tag_and_push_cached_image(self.image_tag, cached_tag)
        self.write_output(self.image_tag, 'succeed, {}, {}'.format(original_size, latest_layer_size))

    def parse_log_download_dependencies(self, job_id, job_orig_log, docker_image_tag):
        # Reproduce the artifact if needed
        logs_to_parse = {}
        for fail_or_pass in ['failed', 'passed']:
            if self.args.parse_new_log:
                logs_to_parse[fail_or_pass] = '{}/repr-{}-{}.log'.format(self.workdir, fail_or_pass,
                                                                         job_id[fail_or_pass])
                container_id = self.create_container(docker_image_tag, 'repr', fail_or_pass)
                build_result = self.run_build_script(container_id, fail_or_pass, logs_to_parse[fail_or_pass],
                                                     job_orig_log[fail_or_pass], job_id[fail_or_pass], None)
                if not build_result:
                    raise CachingScriptError('Cannot reproduce {}'.format(fail_or_pass))
            else:
                logs_to_parse[fail_or_pass] = job_orig_log[fail_or_pass]

        # Download cached files
        for fail_or_pass in ['failed', 'passed']:
            pip_packages = get_dependencies(logs_to_parse[fail_or_pass])
            self.download_dependencies_intermediate_container(fail_or_pass, pip_packages, docker_image_tag)

    def pip_freeze_download_dependencies(self, repo, job_id, job_orig_log, docker_image_tag):
        for fail_or_pass in ['failed', 'passed']:
            build_script = _PASSED_BUILD_SCRIPT if fail_or_pass == 'passed' else _FAILED_BUILD_SCRIPT
            logs = '{}/repr-{}-{}.log'.format(self.workdir, fail_or_pass, job_id[fail_or_pass])
            container_id = self.create_container(docker_image_tag, 'repr', fail_or_pass)
            dep_download_log = '{}/{}-dep-download.log'.format(self.workdir, fail_or_pass)

            # Move pip wrapper script into the container
            script_src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PIP_INSTALL_WRAPPER_SCRIPT)
            script_des = os.path.join('usr', 'local', 'bin', _PIP_INSTALL_WRAPPER_SCRIPT)
            self.copy_file_to_container(container_id, script_src, script_des)

            # Move patch script into the container and run it
            des = self.move_patch_script_into_container(container_id)
            self._run_patch_script(container_id, repo, fail_or_pass, mode='download')
            self.remove_file_from_container(container_id, des)

            # Reproduce the artifact
            # Keep the virtualenv downloads so they can be backed up as well
            _, stdout, stderr, ok = self.run_command('docker exec {} sudo sed -i "/rm.* py.*\\.tar\\.bz2/d" {}'
                                                     .format(container_id, build_script))
            build_result = self.run_build_script(container_id, fail_or_pass, logs,
                                                 job_orig_log[fail_or_pass], job_id[fail_or_pass], None)
            if not build_result:
                raise CachingScriptError('Cannot reproduce {}'.format(fail_or_pass))

            # Get Python version number
            _, stdout, stderr, ok = self.run_command('docker exec {} grep -o -m 1 "/virtualenv/.*/bin/activate" {}'
                                                     .format(container_id, build_script))
            python_version_match = re.search(r'/virtualenv/(.*)/bin/activate', stdout)
            python_version = ''
            if python_version_match:
                python_version = python_version_match.group(1)
            else:
                raise CachingScriptError('Could not find python environment for {}'.format(fail_or_pass))

            # Copy pip freeze script to the container
            script_src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _DEPENDENCY_DOWNLOAD_SCRIPT)
            script_des = os.path.join(_TRAVIS_DIR, _DEPENDENCY_DOWNLOAD_SCRIPT)
            self.copy_file_to_container(container_id, script_src, script_des)

            # Run script to get dependency list and download them
            _, stdout, stderr, ok = self.run_command('docker exec {} bash {} {} 2>&1'
                                                     .format(container_id, script_des, fail_or_pass))
            if not ok:
                raise CachingScriptError('Pip download script failed for {}'.format(fail_or_pass))
            with open(dep_download_log, 'a') as f:
                f.write(stdout)

            # Copy dependency tar out of container
            tar_file_host = '{}/requirements-{}-{}.tar'.format(self.workdir, fail_or_pass, python_version)
            self.copy_file_out_of_container(container_id, _TRAVIS_DIR + '/requirements.tar', tar_file_host)

            self.remove_container(container_id)

    def move_dependencies_to_new_container_and_patch(self, repo, docker_image_tag):
        # Create a new container and place files into it
        container_id = self.create_container(docker_image_tag, 'pack')
        # Copy files to the new container
        for fail_or_pass in ['failed', 'passed']:
            self.move_dependencies_into_container(container_id, fail_or_pass)

        # Run patching script (add offline)
        des = self.move_patch_script_into_container(container_id)

        for fail_or_pass in ['failed', 'passed']:
            self._run_patch_script(container_id, repo, fail_or_pass)

        self.remove_file_from_container(container_id, des)
        # Commit cached image
        cached_tag, cached_id = self.docker_commit(self.image_tag, container_id)
        self.remove_container(container_id)
        return cached_tag

    def _run_patch_script(self, container_id, repo, f_or_p, mode='install'):
        _, stdout, stderr, ok = self.run_command(
            'docker exec {} sudo python {}/{} {} {} {}'.format(container_id, _TRAVIS_DIR, _PROCESS_SCRIPT, repo,
                                                               f_or_p, mode))

    def download_dependencies_intermediate_container(self, f_or_p, pip_packages, docker_image_tag):
        """
        Download Python dependencies in a newly created container.
        Files are saved in `requirements-<f_or_p>-<python_version>.tar`
            e.g. requirements-failed-python2.7.1.tar
        """
        # Note: this script was originally written by mounding Docker volumes.
        # However, volumes does not work in spawner. So we use tar instead.

        for python_version, value in pip_packages.items():
            # Create container
            matched = re.fullmatch(r'(python)([0-9\.]*)', python_version)
            if not matched:
                raise CachingScriptError('Unknown python_version: {}'.format(python_version))
            python, python_ver = matched.groups()
            if not python_ver:  # just 'python'
                raise CachingScriptError('Python version not specified')
            # For python<=2.6 and <=3.1, Docker does not provide official images.
            # It looks like Travis CI does not support python<=2.5 and <=3.1:
            #   https://docs.travis-ci.com/user/languages/python/#python-versions .
            # The solution for 2.6 is to use python provided in Travis CI's virtualenv.
            #   See https://docs.travis-ci.com/user/languages/python/#travis-ci-uses-isolated-virtualenvs
            #   e.g. ~/virtualenv/python2.6/bin/pip install nose --no-deps --download=/tmp
            if python_ver == '2.6':  # python2.6
                # e.g. bugswarm/images:numpy-numpy-100031171
                # e.g. bugswarm/images:web2py-web2py-54526374
                # Here we directly spawn the BugSwarm image and use the pip in the virtual environment
                # To avoid complicated things in activating the virtual environment, we simply call the pip
                # binary in the virtual environment (i.e. not a standard approach).
                cache_dir_container = '/home/travis/pypkg'
                tar_file_container = '/home/travis/requirements.tar'
                python_image_name = docker_image_tag
                pip = '/home/travis/virtualenv/python2.6/bin/pip'
            else:  # python3.6, python2.7.1, python3, etc.
                # Use Docker's official Python slim containers (e.g. 'python:3.6-slim')
                cache_dir_container = '/pypkg'
                tar_file_container = '/requirements.tar'
                python_image_name = '{}:{}-slim'.format(python, python_ver)
                pip = 'pip'
            container_id = self.create_container(python_image_name, python_ver, f_or_p)
            # Download to container
            self.run_command('docker exec {} mkdir {}'.format(container_id, cache_dir_container))
            default_pip_version = None
            if 'default' in value:
                default_pip = value['default']
                self.run_docker_pip_command(container_id, 'install {}'.format(default_pip), pip=pip)
                default_pip_version = default_pip.split('==')[1]
            for package in value.get('packages', []):
                if package.split('==')[0] == 'pip':  # switch to the corresponding pip version
                    pip_command = 'install {}'.format(package)
                    default_pip_version = package.split('==')[1]
                    self.run_docker_pip_command(container_id, pip_command, pip=pip)
                if default_pip_version and version.parse(default_pip_version) < version.parse('8.0.0'):
                    pip_command = 'install {} --no-deps --download="{}"'.format(package, cache_dir_container)
                else:
                    pip_command = 'download --no-deps {} -d {}'.format(package, cache_dir_container)
                self.run_docker_pip_command(container_id, pip_command, pip=pip)
            # Create tar file
            # TODO: fail_on_error=False
            _, stdout, stderr, ok = self.run_command(
                'docker exec {} tar -cvf {} -C {} .'.format(container_id, tar_file_container,
                                                            cache_dir_container))
            tar_file_host = '{}/requirements-{}-{}.tar'.format(self.workdir, f_or_p, python_version)
            self.copy_file_out_of_container(container_id, tar_file_container, tar_file_host)
            self.remove_container(container_id)

    def run_docker_pip_command(self, container_id, command, pip='pip', **kwargs):
        """
        Run a pip command in a container.
        container_id: The container id to run on.
        command: The command string after "pip", not escaped (e.g. 'install jkl -d "/tmp"').
        pip: The pip binary. By default "pip", but can be an absolute path, can start with 'sudo'.
        **kwargs: other arguments for run_command()
        """
        return self.run_command('docker exec {} {} {}'.format(container_id, pip, command), **kwargs)

    def move_dependencies_into_container(self, container_id, f_or_p):
        cache_dir_container = '/home/travis/build/{}/requirements'.format(f_or_p)
        self.run_command('docker exec {} mkdir {}'.format(container_id, cache_dir_container))
        for name in os.listdir(self.workdir):
            if not re.fullmatch(r'requirements-{}-.+\.tar'.format(f_or_p), name):
                continue
            tar_file_host = '{}/{}'.format(self.workdir, name)
            tar_file_container = '/{}'.format(name)
            self.copy_file_to_container(container_id, tar_file_host, tar_file_container)
            self.run_command('docker exec {} tar xvf {} -C {}'.format(container_id, tar_file_container,
                                                                      cache_dir_container))
            self.remove_file_from_container(container_id, tar_file_container)
        self.run_command('docker exec -t {} sudo chown -R travis:travis {}'.format(container_id, cache_dir_container))

    def move_patch_script_into_container(self, container_id):
        src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT)
        des = os.path.join(_TRAVIS_DIR, _PROCESS_SCRIPT)
        self.copy_file_to_container(container_id, src, des)
        return des


def get_dependencies(log_path):
    pip_install_list = parse_log(log_path)
    return pip_install_list


def main(argv=None):
    log.config_logging(getattr(logging, 'INFO', None))

    argv = argv or sys.argv
    image_tags_file, output_file, args = validate_input(argv, 'python')
    repr_metadata_dict = dict()  # This arg for PatchArtifactRunner only used in Java at the moment

    t_start = time.time()
    PatchArtifactRunner(PatchArtifactPythonTask, image_tags_file, _COPY_DIR, output_file, repr_metadata_dict,
                        args, workers=args.workers).run()
    t_end = time.time()
    log.info('Running patch took {}s'.format(t_end - t_start))


if __name__ == '__main__':
    sys.exit(main())
