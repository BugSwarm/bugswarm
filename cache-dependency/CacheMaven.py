import logging
import os
import sys
import time

from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN

from bugswarm.common import log
from bugswarm.common.artifact_processing import utils as procutils
from bugswarm.common.rest_api.database_api import DatabaseAPI
from utils import PatchArtifactRunner, PatchArtifactTask, validate_input, CachingScriptError

_COPY_DIR = 'from_host'
_PROCESS_SCRIPT = 'patch_and_cache_maven.py'
_FAILED_BUILD_SCRIPT = '/usr/local/bin/run_failed.sh'
_PASSED_BUILD_SCRIPT = '/usr/local/bin/run_passed.sh'
_TRAVIS_DIR = '/home/travis'

bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)

"""
List of directories that dependencies may be cached to
"""
CACHE_DIRECTORIES = {
    'home-m2': lambda f_or_p, repo: '/home/travis/.m2/',
    'home-gradle': lambda f_or_p, repo: '/home/travis/.gradle/',
    'home-ivy2': lambda f_or_p, repo: '/home/travis/.ivy2/',
    'proj-gradle': lambda f_or_p, repo: '/home/travis/build/{}/{}/.gradle/'.format(f_or_p, repo),
}


class PatchArtifactMavenTask(PatchArtifactTask):
    def cache_artifact_dependency(self):
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

        job_orig_log = {
            'failed': '{}/orig-failed-{}.log'.format(self.workdir, job_id['failed']),
            'passed': '{}/orig-passed-{}.log'.format(self.workdir, job_id['passed']),
        }
        try:
            for f_or_p in ['failed', 'passed']:
                content = bugswarmapi.get_build_log(str(job_id[f_or_p]))
                with open(job_orig_log[f_or_p], 'w') as f:
                    f.write(content)
        except Exception:
            raise CachingScriptError('Error getting log for failed job {}'.format(job_id['failed']))

        docker_image_tag = '{}:{}'.format(self.args.src_repo, self.image_tag)
        original_size = self.pull_image(docker_image_tag)

        # Start a failed build and a passed build to collect cached files
        caching_build_log_path = {
            'failed': '{}/cache-failed.log'.format(self.workdir),
            'passed': '{}/cache-passed.log'.format(self.workdir),
        }
        for fail_or_pass in ['failed', 'passed']:
            container_id = self.create_container(docker_image_tag, 'cache', fail_or_pass)
            src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT)
            des = os.path.join(_TRAVIS_DIR, _PROCESS_SCRIPT)
            self.copy_file_to_container(container_id, src, des)
            self._run_patch_script(container_id, repo, ['add-mvn-local-repo'])
            build_result = self.run_build_script(container_id, fail_or_pass, caching_build_log_path[fail_or_pass],
                                                 job_orig_log[fail_or_pass], job_id[fail_or_pass], build_system)
            if not build_result and not self.args.ignore_cache_error:
                raise CachingScriptError('Run build script not reproducible for caching {}'.format(fail_or_pass))
            for name, path_func in CACHE_DIRECTORIES.items():
                cont_path = path_func(fail_or_pass, repo)
                cont_tar = '{}/{}.tar'.format(_TRAVIS_DIR, name)
                host_tar = '{}/{}-{}.tar'.format(self.workdir, name, fail_or_pass)
                _, stdout, stderr, ok = self.run_command(
                    'docker exec {} tar -cvf {} {}'.format(container_id, cont_tar, cont_path),
                    fail_on_error=False, print_on_error=False)
                if not ok:
                    # Check whether path does not exist
                    _, _, _, ok = self.run_command(
                        'docker exec {} ls -d {}'.format(container_id, cont_path), fail_on_error=False,
                        print_on_error=False)
                    if ok:
                        self.print_error('Cannot tar {}'.format(cont_path), stdout, stderr)
                        raise CachingScriptError('Cannot tar {}'.format(cont_path))
                else:
                    self.copy_file_out_of_container(container_id, cont_tar, host_tar)
            self.remove_container(container_id)

        # Create a new container and place files into it
        container_id = self.create_container(docker_image_tag, 'pack')
        # Run patching script (add localRepository and offline)
        src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT)
        des = os.path.join(_TRAVIS_DIR, _PROCESS_SCRIPT)
        self.copy_file_to_container(container_id, src, des)
        self._run_patch_script(container_id, repo, ['add-mvn-local-repo', 'offline-maven'])
        self.remove_file_from_container(container_id, des)
        # Copy files to the new container
        for fail_or_pass in ['failed', 'passed']:
            container_tar_files = []
            for name, path_func in CACHE_DIRECTORIES.items():
                cont_path = path_func(fail_or_pass, repo)
                cont_tar = '{}/{}.tar'.format(_TRAVIS_DIR, name)
                host_tar = '{}/{}-{}.tar'.format(self.workdir, name, fail_or_pass)
                if self.args.__getattribute__('no_copy_' + name.replace('-', '_')):
                    self.logger.info('Skipping {} because of command line arguments')
                    continue
                if not os.path.exists(host_tar):
                    self.logger.info('{} does not exist'.format(host_tar))
                    continue
                self.copy_file_to_container(container_id, host_tar, cont_tar)
                if self.args.separate_passed_failed:
                    container_tar_files.append(cont_tar)
                    continue
                # Without --separate-passed-failed: untar the tar file now
                _, stdout, stderr, ok = self.run_command(
                    'docker exec {} tar --directory / -xkvf {}'.format(container_id, cont_tar),
                    fail_on_error=False, loglevel=logging.INFO)
                if not ok:
                    # Ignore error because tar's -k may return non-zero values
                    self.logger.info('Tar xkvf failed for {}, {}'.format(fail_or_pass, name))
                self.remove_file_from_container(container_id, cont_tar)
            if self.args.separate_passed_failed:
                # With --separate-passed-failed: untar the tar file at the start of build script
                # This can fix some caching errors when failed and passed caches conflict (e.g. in ~/.gradle/)
                self._add_untar_to_build_script(container_id, fail_or_pass, container_tar_files)
        if not self.args.no_remove_maven_repositories:
            self._remove_container_maven_repositories(container_id, '/home/travis/.m2/')
        # Commit cached image
        cached_tag, cached_id = self.docker_commit(self.image_tag, container_id)
        self.remove_container(container_id)

        # Start two runs to test cached image
        test_build_log_path = {
            'failed': '{}/test-failed.log'.format(self.workdir),
            'passed': '{}/test-passed.log'.format(self.workdir),
        }
        for fail_or_pass in ['failed', 'passed']:
            container_id = self.create_container(cached_tag, 'test', fail_or_pass)
            # When testing here, we by default apply a stricter patch (offline-all-maven, offline-all-gradle)
            if not self.args.no_strict_offline_test:
                src = os.path.join(procutils.HOST_SANDBOX, _COPY_DIR, _PROCESS_SCRIPT)
                des = os.path.join(_TRAVIS_DIR, _PROCESS_SCRIPT)
                self.copy_file_to_container(container_id, src, des)
                self._run_patch_script(container_id, repo, ['offline-all-maven', 'offline-all-gradle'])
            build_result = self.run_build_script(container_id, fail_or_pass, test_build_log_path[fail_or_pass],
                                                 job_orig_log[fail_or_pass], job_id[fail_or_pass], build_system)
            if not build_result:
                raise CachingScriptError('Run build script not reproducible for testing {}'.format(fail_or_pass))

        # Push image
        latest_layer_size = self.get_last_layer_size(cached_tag)
        self.tag_and_push_cached_image(self.image_tag, cached_tag)
        self.write_output(self.image_tag, 'succeed, {}, {}'.format(original_size, latest_layer_size))

    def _run_patch_script(self, container_id, repo, actions):
        _, stdout, stderr, ok = self.run_command(
            'docker exec {} sudo python {}/{} {} {}'.format(container_id, _TRAVIS_DIR, _PROCESS_SCRIPT, repo,
                                                            ' '.join(actions)))

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
        build_script_container = '/usr/local/bin/run_{}.sh'.format(f_or_p)
        build_script_host_old = '{}/run_{}_old.sh'.format(self.workdir, f_or_p)
        build_script_host_new = '{}/run_{}_new.sh'.format(self.workdir, f_or_p)
        self.copy_file_out_of_container(container_id, build_script_container, build_script_host_old)
        assert os.path.exists(build_script_host_old)
        assert not os.path.exists(build_script_host_new)
        with open(build_script_host_old, 'r') as input_file:
            with open(build_script_host_new, 'w') as output_file:
                # Copy the first line
                shebang = input_file.readline()
                assert shebang == '#!/bin/bash\n'
                output_file.write(shebang)
                # Add commands to untar
                output_file.write('# Untar cached dependency files\n')
                for tar_file in tar_files:
                    output_file.write('tar --directory / -xkf {}\n'.format(tar_file))
                # Copy the rest of the input file
                while True:
                    line = input_file.readline()
                    if not line:
                        break
                    output_file.write(line)
        self.copy_file_to_container(container_id, build_script_host_new, build_script_container)
        self.run_command('docker exec {} sudo chown travis:travis {}'.format(container_id, build_script_container))
        self.run_command('docker exec {} sudo chmod 777 {}'.format(container_id, build_script_container))


def main(argv=None):
    log.config_logging(getattr(logging, 'INFO', None))

    argv = argv or sys.argv
    image_tags_file, output_file, args = validate_input(argv, 'maven')

    t_start = time.time()
    PatchArtifactRunner(PatchArtifactMavenTask, image_tags_file, _COPY_DIR, output_file, args,
                        workers=args.workers).run()
    t_end = time.time()
    log.info('Running patch took {}s'.format(t_end - t_start))


if __name__ == '__main__':
    sys.exit(main())
