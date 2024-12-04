import logging
import os
import sys
import time

from utils import CachingScriptError, PatchArtifactRunner, PatchArtifactTask, get_repr_metadata_dict, validate_input

from bugswarm.common import log
from bugswarm.common.artifact_processing import utils as procutils
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.log_downloader import download_log
from bugswarm.common.rest_api.database_api import DatabaseAPI

_COPY_DIR = 'from_host'
_COPY_DIR_JAVA = 'from_host/java'
_PROCESS_SCRIPT = 'patch_and_cache_maven.py'
_JOB_START_SCRIPT = 'patch_and_cache_java.sh'
_JOB_COMPLETE_SCRIPT = 'remove_wrapper_scripts.sh'
_GITHUB_DIR = '/home/github'

bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)

"""
List of directories that dependencies may be cached to
"""
CACHE_DIRECTORIES = {
    'home-m2': lambda f_or_p, repo: '/home/github/.m2/',
    'home-gradle': lambda f_or_p, repo: '/home/github/.gradle/',
    'home-ivy2': lambda f_or_p, repo: '/home/github/.ivy2/',
    'proj-gradle': lambda f_or_p, repo: '/home/github/build/{}/{}/.gradle/'.format(f_or_p, repo),
    'proj-gradle-wrapper': lambda f_or_p, repo: '/home/github/build/{}/{}/gradle/wrapper/'.format(f_or_p, repo),
    'proj-maven': lambda f_or_p, repo: '/home/github/build/{}/{}/.mvn/'.format(f_or_p, repo)
    # /opt/hostedtoolcache is handled separately
    # 'actions-toolcache': lambda *_: '/opt/hostedtoolcache',
}


class PatchArtifactMavenTask(PatchArtifactTask):
    def cache_artifact_dependency(self):
        if self.repr_metadata:
            artifact = self.repr_metadata[self.image_tag]
        # Normal case, outside of reproducer pipeline
        else:
            response = bugswarmapi.find_artifact(self.image_tag)
            if not response.ok:
                raise CachingScriptError('Unable to get artifact data')
            artifact = response.json()

        build_system = artifact['build_system']
        job_id = {
            'failed': artifact['failed_job']['job_id'],
            'passed': artifact['passed_job']['job_id'],
        }
        repo = artifact['repo']

        docker_image_tag = '{}:{}'.format(self.args.src_repo, self.image_tag)
        original_size = self.pull_image(docker_image_tag)

        self.repo = repo
        self.build_system = build_system
        self.docker_image_tag = docker_image_tag
        self.job_id = job_id
        job_orig_log = self._get_orig_logs()
        self.job_orig_log = job_orig_log

        # Start a failed build and a passed build to collect cached files
        caching_build_log_path = {
            'failed': '{}/cache-failed.log'.format(self.workdir),
            'passed': '{}/cache-passed.log'.format(self.workdir),
        }
        cached_files = []
        cached_files_always_unpack = []
        wrapper_scripts_status = {'failed': False, 'passed': False}
        for fail_or_pass in ['failed', 'passed']:
            container_id = self.create_container(docker_image_tag, 'cache', fail_or_pass)
            self._run_patch_script(container_id, repo, ['add-mvn-local-repo'])
            self.add_wrapper_scripts_reproducing(container_id)
            self.pre_cache_toolcache(container_id)
            build_result = self.run_build_script(container_id, fail_or_pass, caching_build_log_path[fail_or_pass],
                                                 job_orig_log[fail_or_pass], job_id[fail_or_pass], build_system,
                                                 repo=self.repo)
            if not build_result and not self.args.ignore_cache_error:
                raise CachingScriptError('Run build script not reproducible for caching {}'.format(fail_or_pass))

            cached_files.extend(self._cache_and_copy_files(container_id, fail_or_pass))
            cached_files.extend(self.cache_node_modules(container_id, fail_or_pass, repo))
            cached_files_always_unpack.extend(self.cache_toolcache(container_id, fail_or_pass))
            wrapper_scripts_status[fail_or_pass] = self._cache_wrapper_scripts(container_id, fail_or_pass)

            self.remove_container(container_id)

        # Create a new container and place files into it
        container_id = self.create_container(docker_image_tag, 'pack')
        # Run patching script (add localRepository and offline)
        self._run_patch_script(container_id, repo, ['add-mvn-local-repo', 'offline-maven', 'offline-gradle'])

        src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR_JAVA, _JOB_START_SCRIPT)
        des = os.path.join('usr', 'local', 'bin', _JOB_START_SCRIPT)
        self.copy_file_to_container(container_id, src, des)

        src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _JOB_COMPLETE_SCRIPT)
        des = os.path.join('usr', 'local', 'bin', _JOB_COMPLETE_SCRIPT)
        self.copy_file_to_container(container_id, src, des)

        # Put wrapper scripts to /usr/bin
        self.add_wrapper_scripts_packing(container_id)

        # Copy files to the new container
        for fail_or_pass in ['failed', 'passed']:
            container_tar_files = []

            target_files = [(*entry, False) for entry in cached_files if entry[1] == fail_or_pass]
            target_files.extend((*entry, True) for entry in cached_files_always_unpack if entry[1] == fail_or_pass)

            for name, f_or_p, host_tar, cont_tar, force_unpack in target_files:
                self.copy_file_to_container(container_id, host_tar, cont_tar)
                if self.args.separate_passed_failed and not force_unpack:
                    container_tar_files.append(cont_tar)
                    continue

                # With --no-separate-passed-failed (or if the file should always be unpacked): untar the tar file now
                self.run_command('docker exec {} sudo tar --directory / -xzvf {}'.format(container_id, cont_tar))
                self.remove_file_from_container(container_id, cont_tar)

            if self.args.separate_passed_failed:
                # Without --no-separate-passed-failed: untar the tar file at the start of build script
                # This can fix some caching errors when failed and passed caches conflict (e.g. in ~/.gradle/)
                self._add_untar_to_build_script(container_id, fail_or_pass, container_tar_files)

            if wrapper_scripts_status[fail_or_pass]:
                self._move_cached_wrapper_scripts_from_host_to_pack_container(container_id, fail_or_pass)

        if not self.args.no_remove_maven_repositories:
            self._remove_container_maven_repositories(container_id, '/home/github/.m2/')

        # Commit cached image
        cached_tag, cached_id = self.docker_commit(
            self.image_tag, container_id,
            env_str='ACTIONS_RUNNER_HOOK_JOB_STARTED=/usr/local/bin/{} '
            'ACTIONS_RUNNER_HOOK_JOB_COMPLETED=/usr/local/bin/{}'.format(_JOB_START_SCRIPT, _JOB_COMPLETE_SCRIPT))
        self.remove_container(container_id)

        # Start two runs to test cached image
        for fail_or_pass in ['failed', 'passed']:
            repr_log_path = '{}/test-{}.log'.format(self.workdir, fail_or_pass)
            self._test_cached_image(cached_tag, fail_or_pass, repr_log_path, job_orig_log[fail_or_pass],
                                    job_id[fail_or_pass])

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

    def _cache_and_copy_files(self, container_id, fail_or_pass):
        cached_files = []
        for name, path_func in CACHE_DIRECTORIES.items():
            if getattr(self.args, 'no_copy_' + name.replace('-', '_'), False):
                self.logger.info('Skipping {} because of command line arguments'.format(name))
                continue

            cont_path = path_func(fail_or_pass, self.repo)
            _, _, _, path_exists = self.run_command(
                'docker exec {} ls -d {}'.format(container_id, cont_path), fail_on_error=False, print_on_error=False)
            if not path_exists:
                continue

            cont_tar = '{}/{}-{}.tgz'.format(_GITHUB_DIR, name, fail_or_pass)
            host_tar = '{}/{}-{}.tgz'.format(self.workdir, name, fail_or_pass)
            self.run_command('docker exec {} tar -czvf {} {}'.format(container_id, cont_tar, cont_path))
            self.copy_file_out_of_container(container_id, cont_tar, host_tar)

            cached_files.append((name, fail_or_pass, host_tar, cont_tar))
        return cached_files

    def _cache_wrapper_scripts(self, container_id, fail_or_pass):
        cont_tar = '{}/cacher-{}.tgz'.format(_GITHUB_DIR, fail_or_pass)
        host_tar = '{}/cacher-{}.tgz'.format(self.workdir, fail_or_pass)
        cont_path = '{}/cacher'.format(_GITHUB_DIR)

        _, _, _, path_exists = self.run_command(
            'docker exec {} ls -d {}'.format(container_id, cont_path), fail_on_error=False, print_on_error=False)
        if not path_exists:
            return False

        self.run_command('docker exec {} tar -czf {} {}'.format(container_id, cont_tar, cont_path))
        self.copy_file_out_of_container(container_id, cont_tar, host_tar)
        return True

    def _move_cached_wrapper_scripts_from_host_to_pack_container(self, container_id, fail_or_pass):
        # Cached wrapper scripts, time to move them back to the container
        # 1: Move file from host to container
        cont_tar = '{}/cacher-{}.tgz'.format(_GITHUB_DIR, fail_or_pass)
        host_tar = '{}/cacher-{}.tgz'.format(self.workdir, fail_or_pass)
        self.copy_file_to_container(container_id, host_tar, cont_tar)

    def _test_cached_image(self, image_tag, fail_or_pass, repr_log_path, orig_log_path, job_id):
        if self.args.disconnect_network_during_test:
            container_id = self.create_container(
                image_tag,
                'test',
                fail_or_pass,
                docker_args='--network none --hostname bugswarmdummy --add-host bugswarmdummy:127.0.0.1')
        else:
            container_id = self.create_container(image_tag, 'test', fail_or_pass)

        if not self.args.no_strict_offline_test:
            # When testing here, we by default apply a stricter patch (offline-all-maven, offline-all-gradle)
            self._run_patch_script(container_id, self.repo, ['offline-all-maven', 'offline-all-gradle'])

        build_result = self.run_build_script(container_id, fail_or_pass, repr_log_path, orig_log_path, job_id,
                                             self.build_system, repo=self.repo)
        if not build_result:
            raise CachingScriptError('Run build script not reproducible for testing {}'.format(fail_or_pass))

        self.verify_tests_result(container_id, fail_or_pass, 'git', 'git-output.log')
        self.verify_tests_result(container_id, fail_or_pass, 'wget', 'wget-output.log')

    def _run_patch_script(self, container_id, repo, actions):
        src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT)
        des = os.path.join(_GITHUB_DIR, _PROCESS_SCRIPT)
        self.copy_file_to_container(container_id, src, des)
        self.run_command('docker exec {} sudo python3 {} {} {}'.format(container_id, des, repo, ' '.join(actions)))
        self.remove_file_from_container(container_id, des)

    def _remove_container_maven_repositories(self, container_id, m2_path):
        """
        Remove `_remote.repositories` and `_maven.repositories` files in container
        `m2_path` should be `~/.m2/`
        """
        _, stdout, stderr, ok = self.run_command(
            r'docker exec {} find {} \( -name _maven.repositories -o -name _remote.repositories \) -exec rm -v {{}} \;'
            .format(container_id, m2_path), print_on_error=False, fail_on_error=False)
        # Ignore errors

    def _add_untar_to_build_script(self, container_id, f_or_p, tar_files):
        """
        * Copy build script to `run_<failed-or-passed>_old.sh`.
        * Add a few lines to untar tar_files.
        * Save the new script to `run_<failed-or-passed>_new.sh`.
        * Copy back to the container.
        """
        if not tar_files:
            return

        build_script_container = '/usr/local/bin/run_{}.sh'.format(f_or_p)
        build_script_host_old = '{}/run_{}_old.sh'.format(self.workdir, f_or_p)
        build_script_host_new = '{}/run_{}_new.sh'.format(self.workdir, f_or_p)
        self.copy_file_out_of_container(container_id, build_script_container, build_script_host_old)
        assert os.path.exists(build_script_host_old)

        # assert not os.path.exists(build_script_host_new)
        with open(build_script_host_old, 'r') as input_file:
            with open(build_script_host_new, 'w') as output_file:
                # Copy the first line
                shebang = input_file.readline()
                # assert shebang == '#!/bin/bash\n'
                output_file.write(shebang)
                # Add commands to untar
                output_file.write('# Untar cached dependency files\n')
                output_file.write('echo "Untarring dependencies (this may take a few seconds)"\n')
                for tar_file in tar_files:
                    output_file.write('sudo tar --directory / -xzf {}\n'.format(tar_file))
                # Copy the rest of the input file
                lines = input_file.read()
                output_file.write(lines)
        self.copy_file_to_container(container_id, build_script_host_new, build_script_container)
        self.run_command('docker exec {} sudo chown github:github {}'.format(container_id, build_script_container))
        self.run_command('docker exec {} sudo chmod 777 {}'.format(container_id, build_script_container))


def main(argv=None):
    log.config_logging(getattr(logging, 'INFO', None))

    argv = argv or sys.argv
    image_tags_file, output_file, args = validate_input(argv, 'maven')

    # Remains empty if run outside of reproducer pipeline
    repr_metadata_dict = dict()
    # Task JSON path will be an empty string by default
    if args.task_json:
        log.info('Writing pairs to reference dict from ReproducedResultsAnalyzer JSON')
        repr_metadata_dict = get_repr_metadata_dict(args.task_json, repr_metadata_dict)
    t_start = time.time()
    PatchArtifactRunner(PatchArtifactMavenTask, image_tags_file, _COPY_DIR, output_file, repr_metadata_dict,
                        args, workers=args.workers).run()
    t_end = time.time()
    log.info('Running patch took {}s'.format(t_end - t_start))


if __name__ == '__main__':
    sys.exit(main())
