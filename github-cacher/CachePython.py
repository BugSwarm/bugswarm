import logging
import os
import re
import sys
import time
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common import log
from bugswarm.common.artifact_processing import utils as procutils
from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.log_downloader import download_log
from utils import PatchArtifactTask, PatchArtifactRunner, CachingScriptError, get_repr_metadata_dict, validate_input


_COPY_DIR = 'from_host'
_COPY_DIR_PYTHON = 'from_host/python'
_JOB_START_SCRIPT = 'patch_and_cache_python.sh'
_JOB_COMPLETE_SCRIPT = 'remove_wrapper_scripts.sh'
_STEP_START_SCRIPT = 'cache_toolcache_python.sh'
_PYPI_CACHE_SERVER_SCRIPT = 'python_cache_server.py'
_APT_CACHE_SERVER_SCRIPT = 'apt_cache_server.py'
_CACHE_SERVER_SETUP_SCRIPT = 'setup_python_cache_server.sh'
_WRAPPER_SCRIPT_DIR = 'wrapper_scripts'
_WRAPPER_SCRIPTS = [('git', 'git.py'), ('wget', 'wget.py'), ('poetry.sh', 'poetry.sh')]
_GITHUB_DIR = '/home/github'

bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)


class PatchArtifactPythonTask(PatchArtifactTask):
    def cache_artifact_dependency(self):
        if self.repr_metadata:
            artifact = self.repr_metadata[self.image_tag]
        # Normal case, outside of reproducer pipeline
        else:
            response = bugswarmapi.find_artifact(self.image_tag)
            if not response.ok:
                raise CachingScriptError('Unable to get artifact data')
            artifact = response.json()

        job_id = {
            'failed': artifact['failed_job']['job_id'],
            'passed': artifact['passed_job']['job_id'],
        }
        repo = artifact['repo']
        self.repo = repo

        self.job_id = job_id
        job_orig_log = self._get_orig_logs()

        docker_image_tag = '{}:{}'.format(self.args.src_repo, self.image_tag)
        original_size = self.pull_image(docker_image_tag)

        self.set_up_cache_server(job_id, job_orig_log, docker_image_tag)
        cached_tag = self.move_dependencies_to_new_container_and_patch(repo, docker_image_tag)

        self._test_cached_image(job_id, job_orig_log, cached_tag)

        # Push image
        latest_layer_size = self.get_last_layer_size(cached_tag)
        self.tag_and_push_cached_image(self.image_tag, cached_tag)
        self.write_output(self.image_tag, 'succeed, {}, {}'.format(original_size, latest_layer_size))

    def _get_orig_logs(self):
        if self.repr_metadata:
            job_orig_log = {}
            for f_or_p in ['failed', 'passed']:
                job_id = self.job_id[f_or_p]
                location = '../github-reproducer/intermediates/orig_logs/{}-orig.log'.format(job_id)
                if not os.path.isfile(location):
                    location = '../pair-filter/original-logs/{}-orig.log'.format(job_id)
                if not os.path.isfile(location) and not download_log(job_id, location, repo=self.repo):
                    raise CachingScriptError('Error getting log for {} job {}'.format(f_or_p, job_id))
                job_orig_log[f_or_p] = location
            return job_orig_log

        job_orig_log = {
            'failed': '{}/orig-failed-{}.log'.format(self.workdir, self.job_id['failed']),
            'passed': '{}/orig-passed-{}.log'.format(self.workdir, self.job_id['passed']),
        }
        for f_or_p in ['failed', 'passed']:
            job_id = str(self.job_id[f_or_p])
            try:
                content = bugswarmapi.get_build_log(job_id)
                with open(job_orig_log[f_or_p], 'w') as f:
                    f.write(content)
            except Exception:
                raise CachingScriptError('Error getting log for {} job {}'.format(f_or_p, job_id))
        return job_orig_log

    def set_up_cache_server(self, job_id, job_orig_log, docker_image_tag):
        for fail_or_pass in ['failed', 'passed']:
            logs = '{}/repr-{}-{}.log'.format(self.workdir, fail_or_pass, job_id[fail_or_pass])
            container_id = self.create_container(docker_image_tag, 'repr', fail_or_pass)

            script_src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR_PYTHON, _PYPI_CACHE_SERVER_SCRIPT)
            script_des = os.path.join(_GITHUB_DIR, _PYPI_CACHE_SERVER_SCRIPT)
            self.copy_file_to_container(container_id, script_src, script_des)

            script_src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _APT_CACHE_SERVER_SCRIPT)
            script_des = os.path.join(_GITHUB_DIR, _APT_CACHE_SERVER_SCRIPT)
            self.copy_file_to_container(container_id, script_src, script_des)

            script_src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR_PYTHON, _CACHE_SERVER_SETUP_SCRIPT)
            pypi_cache_script_des = os.path.join(_GITHUB_DIR, _CACHE_SERVER_SETUP_SCRIPT)
            self.copy_file_to_container(container_id, script_src, pypi_cache_script_des)

            script_src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR_PYTHON, _STEP_START_SCRIPT)
            script_des = os.path.join('usr', 'local', 'bin', _STEP_START_SCRIPT)
            self.copy_file_to_container(container_id, script_src, script_des)

            # Wrapper scripts
            self.add_wrapper_scripts_reproducing(container_id)

            # Set up and run cache server
            self.run_command('docker exec {} bash {} run'.format(container_id, pypi_cache_script_des))

            self.pre_cache_toolcache(container_id)

            build_result = self.run_build_script(container_id, fail_or_pass, logs,
                                                 job_orig_log[fail_or_pass], job_id[fail_or_pass], None,
                                                 repo=self.repo,
                                                 envs=[
                                                     'PIP_INDEX_URL=http://localhost:56765/simple/',
                                                     'PIP_DEFAULT_TIMEOUT=120',
                                                     'UV_DEFAULT_INDEX=http://localhost:56765/simple/',
                                                     'ACTIONS_RUNNER_HOOK_STEP_STARTED='
                                                     '/usr/local/bin/cache_toolcache_python.sh',
                                                     'ACTIONS_RUNNER_HOOK_STEP_COMPLETED='
                                                     '/usr/local/bin/cache_toolcache_python.sh'
                                                 ])
            if not build_result:
                raise CachingScriptError('Cannot reproduce {}'.format(fail_or_pass))

            if not self.cache_toolcache(container_id, fail_or_pass):
                log.error('Unable to cache toolcache.')
            self.cache_node_modules(container_id, fail_or_pass, self.repo)

            # Tar the cacher directory (PyPI and APT)
            self.run_command(
                'docker exec {} bash -c "tar -czf {}/cacher.tgz {}/cacher"'
                .format(container_id, _GITHUB_DIR, _GITHUB_DIR)
            )

            # Copy dependency tar out of container
            tar_file_cont = os.path.join(_GITHUB_DIR, 'cacher.tgz')
            tar_file_host = os.path.join(self.workdir, 'cacher-{}.tgz'.format(fail_or_pass))
            self.copy_file_out_of_container(container_id, tar_file_cont, tar_file_host)

            self.remove_container(container_id)

    def move_dependencies_to_new_container_and_patch(self, repo, docker_image_tag):
        # Create a new container and place files into it
        container_id = self.create_container(docker_image_tag, 'pack')
        # Copy files to the new container
        script_src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR_PYTHON, _CACHE_SERVER_SETUP_SCRIPT)
        script_des = os.path.join(_GITHUB_DIR, _CACHE_SERVER_SETUP_SCRIPT)
        self.copy_file_to_container(container_id, script_src, script_des)

        for fail_or_pass in ['failed', 'passed']:
            self.move_dependencies_into_container(container_id, fail_or_pass)
            # Set up cache server
            _, stdout, stderr, ok = self.run_command('docker exec {} bash {} {}'.format(container_id, script_des,
                                                                                        fail_or_pass))

        src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR_PYTHON, _JOB_START_SCRIPT)
        des = os.path.join('usr', 'local', 'bin', _JOB_START_SCRIPT)
        self.copy_file_to_container(container_id, src, des)

        src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _JOB_COMPLETE_SCRIPT)
        des = os.path.join('usr', 'local', 'bin', _JOB_COMPLETE_SCRIPT)
        self.copy_file_to_container(container_id, src, des)

        # Put wrapper scripts to /usr/bin
        self.add_wrapper_scripts_packing(container_id)

        cached_tag, cached_id = self.docker_commit(
            self.image_tag, container_id, env_str='ACTIONS_RUNNER_HOOK_JOB_STARTED=/usr/local/bin/{} '
            'ACTIONS_RUNNER_HOOK_JOB_COMPLETED=/usr/local/bin/{}'
            .format(_JOB_START_SCRIPT, _JOB_COMPLETE_SCRIPT)
        )
        self.remove_container(container_id)
        return cached_tag

    def _test_cached_image(self, job_id, job_orig_log, cached_tag):
        # Start two runs to test cached image
        test_build_log_path = {
            'failed': '{}/test-failed.log'.format(self.workdir),
            'passed': '{}/test-passed.log'.format(self.workdir),
        }
        for fail_or_pass in ['failed', 'passed']:
            if self.args.disconnect_network_during_test:
                container_id = self.create_container(
                    cached_tag, 'test', fail_or_pass,
                    docker_args='--network none --hostname bugswarmdummy --add-host bugswarmdummy:127.0.0.1')
            else:
                container_id = self.create_container(cached_tag, 'test', fail_or_pass)

            build_result = self.run_build_script(container_id, fail_or_pass, test_build_log_path[fail_or_pass],
                                                 job_orig_log[fail_or_pass], job_id[fail_or_pass], None,
                                                 repo=self.repo)
            if not build_result:
                raise CachingScriptError('Run build script not reproducible for testing {}'.format(fail_or_pass))

            self.verify_tests_result(container_id, fail_or_pass, 'pip', 'pypi-cacher.log')
            self.verify_tests_result(container_id, fail_or_pass, 'git', 'git-output.log')
            self.verify_tests_result(container_id, fail_or_pass, 'wget', 'wget-output.log')
            self.verify_tests_result(container_id, fail_or_pass, 'apt', 'apt-cacher.log')
            self._check_poetry(container_id, fail_or_pass)

    def move_dependencies_into_container(self, container_id, f_or_p):
        for name in os.listdir(self.workdir):
            if not re.fullmatch(r'.*-{}\.(tar|tgz)'.format(f_or_p), name):
                continue
            tar_file_host = '{}/{}'.format(self.workdir, name)
            tar_file_container = '/{}'.format(name)
            self.copy_file_to_container(container_id, tar_file_host, tar_file_container)

    def _check_poetry(self, container_id, fail_or_pass):
        # Search all pyproject.toml files (2 levels max), then check if the file contains [tool.poetry]
        _, stdout, _, _ = self.run_command(
            'docker exec {} find {} -maxdepth 2 -name pyproject.toml -exec cat {{}} \\; | grep "\\[tool.poetry\\]"'
            ' | wc -l'
            .format(container_id, os.path.join(_GITHUB_DIR, 'build', fail_or_pass, self.repo))
        )
        if stdout != '0':
            # project contains poetry settings
            log.debug('{} job contains {} pyproject.toml that use poetry'.format(fail_or_pass, stdout))

            _, stdout, _, _ = self.run_command(
                'docker exec {} cat /etc/reproducer-environment | grep "POETRY_ADDED_REPOSITORY=1" | wc -l'
                .format(container_id)
            )

            if stdout == '0':
                log.warning("Project's pyproject.toml contains poetry, but cacher didn't find any poetry command!")


def main(argv=None):
    log.config_logging(getattr(logging, 'INFO', None))

    argv = argv or sys.argv
    image_tags_file, output_file, args = validate_input(argv, 'python')

    # Remains empty if run outside of reproducer pipeline
    repr_metadata_dict = dict()
    if args.task_json:
        log.info('Writing pairs to reference dict from ReproducedResultsAnalyzer JSON')
        repr_metadata_dict = get_repr_metadata_dict(args.task_json, repr_metadata_dict)

    t_start = time.time()
    PatchArtifactRunner(PatchArtifactPythonTask, image_tags_file, _COPY_DIR, output_file, repr_metadata_dict,
                        args, workers=args.workers).run()
    t_end = time.time()
    log.info('Running patch took {}s'.format(t_end - t_start))


if __name__ == '__main__':
    sys.exit(main())
