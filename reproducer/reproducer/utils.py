import collections
import os
import shutil
import subprocess
import time

from bugswarm.common import log
from bugswarm.common import utils as bugswarmutils
from bugswarm.common.shell_wrapper import ShellWrapper


class Utils(object):
    def __init__(self, config):
        self.config = config
        self.start_time = time.time()

    # --------------------------------------------
    # -------- General helper functions ----------
    # --------------------------------------------

    def copytree(self, src, dst, symlinks=False, ignore=None):
        if not os.path.exists(dst):
            os.makedirs(dst)
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                self.copytree(s, d, symlinks, ignore)
            else:
                if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                    shutil.copy2(s, d)

    @staticmethod
    def remove_file(filename):
        try:
            os.remove(filename)
        except FileNotFoundError:
            # Intentionally let the caller handle other types of exceptions.
            pass

    # --------------------------------------------
    # ---------- Setup helper functions ----------
    # --------------------------------------------

    def directories_setup(self):
        os.makedirs(self.config.current_task_dir, exist_ok=True)
        os.makedirs(self.config.stored_repos_dir, exist_ok=True)

    def setup_jobpair_dir(self, job):
        log.debug(self.get_jobpair_dir(job))
        os.makedirs(self.get_jobpair_dir(job), exist_ok=True)

    # --------------------------------------------
    # ------ Subprocess helper functions ---------
    # --------------------------------------------

    @staticmethod
    def construct_github_repo_url(repo):
        return 'https://github.com/{}.git'.format(repo)

    @staticmethod
    def construct_github_archive_repo_sha_url(repo, sha):
        return 'https://github.com/{}/archive/{}.zip'.format(repo, sha)

    def get_repo_storage_dir(self, job):
        return os.path.join(self.config.stored_repos_dir, job.repo)

    @staticmethod
    def is_travis_installed():
        command = 'travis'
        result, _, _ = ShellWrapper.run_commands(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        return 'Usage: travis COMMAND' in result

    def clone_project_repo(self, repo):
        owner, project_name = repo.split('/')
        owner_dir = self.get_repo_owner_dir(owner)
        os.makedirs(owner_dir, exist_ok=True)
        destination = os.path.join(self.config.stored_repos_dir, repo)
        clone_command = 'git clone {} {}'.format(Utils.construct_github_repo_url(repo), destination)
        _, _, returncode = ShellWrapper.run_commands(clone_command, shell=True)
        return returncode

    def fetch_pr_data(self, job):
        owner, project_name = job.repo.split('/')
        # owner_dir = self.get_repo_owner_dir(owner)
        command = 'cd {} ;'.format(self.get_stored_repo_path(job))
        command += 'git fetch origin refs/pull/*/head:refs/remotes/origin/pr/* ;'
        ShellWrapper.run_commands(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    def remove_current_task_dir(self):
        command = 'rm -rf {}'.format(self.config.current_task_dir)
        log.debug(command)
        ShellWrapper.run_commands(command, shell=True)

    # --------------------------------------------
    # ---- Check file exists helper functions ----
    # --------------------------------------------

    def check_if_project_repo_exist(self, repo):
        user, project = repo.split('/')
        owner_dir = self.get_repo_owner_dir(user)
        if os.path.isdir(owner_dir):
            return os.path.isdir(os.path.join(owner_dir, project))

    def check_if_repo_dir_exists(self, job):
        return os.path.isdir(self.get_reproducing_repo_dir(job))

    def check_if_travis_build_log_exist(self, job):
        return os.path.isfile(self.get_travis_build_log_path(job))

    def check_if_repo_tar_exist(self, job):
        return os.path.isfile(self.get_repo_tar_path(job))

    def check_if_log_exist_in_task(self, job, run=None):
        return os.path.isfile(self.get_log_path_in_task(job, run))

    def check_if_log_exist(self, job):
        return os.path.isfile(self.get_log_path(job))

    def check_if_build_sh_exist(self, job):
        return os.path.isfile(self.get_build_sh_path(job))

    def check_if_dockerfile_exist(self, job):
        return os.path.isfile(self.get_dockerfile_path(job))

    # --------------------------------------------
    # -------- Get path helper functions ---------
    # --------------------------------------------

    def get_stored_repo_path(self, job):
        return os.path.join(self.config.stored_repos_dir, job.repo)

    def get_repo_owner_dir(self, owner):
        return os.path.join(self.config.stored_repos_dir, owner)

    def get_workspace_sha_dir(self, job):
        return os.path.join(self.config.workspace_dir, job.job_id, job.sha)

    def get_reproducing_repo_dir(self, job):
        return os.path.join(self.config.workspace_dir, job.job_id, job.sha, job.repo)

    def get_reproduce_tmp_dir(self, job):
        return os.path.join(self.get_reproducing_repo_dir(job), self.config.reproduce_tmp_dir)

    @staticmethod
    def construct_log_name(job):
        return '{}.log'.format(job.job_id)

    @staticmethod
    def construct_patch_name(job):
        return '{}-pip-patch.json'.format(job.job_id)

    def get_log_path(self, job):
        return os.path.join(self.get_reproduce_tmp_dir(job), Utils.construct_log_name(job))

    def get_travis_build_log_path(self, job):
        filename = '{}-travis.log'.format(job.job_id)
        return os.path.join(self.get_reproduce_tmp_dir(job), filename)

    def get_project_storage_repo_tar_path(self, job):
        return os.path.join(self.get_stored_repo_path(job), 'repo.tar')

    def get_project_storage_repo_zip_path(self, job):
        return os.path.join(self.get_stored_repo_path(job), 'repo-' + job.sha + '.zip')

    def get_repo_tar_path(self, job):
        return os.path.join(self.get_reproduce_tmp_dir(job), self.config.tarfile_name)

    def get_repo_tar_path_in_task(self, job):
        filename = 'failed.tar' if job.is_failed == 'failed' else 'passed.tar'
        return os.path.join(self.get_tar_file_storage_dir_in_task(job), filename)

    def copy_repo_from_task_into_workspace(self, job):
        shutil.copy(self.get_repo_tar_path_in_task(job), self.get_repo_tar_path(job))

    @staticmethod
    def construct_dockerfile_name(job):
        return '{}-Dockerfile'.format(job.job_id)

    def get_dockerfile_path(self, job, reproduce_tmp_path=None):
        if not reproduce_tmp_path:
            reproduce_tmp_path = self.get_reproduce_tmp_dir(job)
        return os.path.join(reproduce_tmp_path, Utils.construct_dockerfile_name(job))

    def get_dockerfile_in_task_path(self, job):
        return os.path.join(self.get_jobpair_dir(job), Utils.construct_dockerfile_name(job))

    def copy_dockerfile_from_task_into_workspace(self, job):
        shutil.copy(self.get_dockerfile_in_task_path(job), self.get_dockerfile_path(job))

    @staticmethod
    def construct_build_sh_name(job):
        return '{}.sh'.format(job.job_id)

    def get_build_sh_path(self, job, reproduce_tmp_path=None):
        if not reproduce_tmp_path:
            reproduce_tmp_path = self.get_reproduce_tmp_dir(job)
        return os.path.join(reproduce_tmp_path, Utils.construct_build_sh_name(job))

    def get_build_sh_path_in_task(self, job):
        return os.path.join(self.get_jobpair_dir(job), Utils.construct_build_sh_name(job))

    def copy_build_sh_from_task_into_workspace(self, job):
        shutil.copy(self.get_build_sh_path_in_task(job), self.get_build_sh_path(job))

    def get_abs_jobpair_dockerfile_path(self, jobpair):
        dockerfile_name = '{}-Dockerfile'.format(jobpair.jobpair_name)
        return os.path.abspath(os.path.join(self.get_jobpair_dir(jobpair.jobs[0]), dockerfile_name))

    def get_orig_travis_log_path(self, job):
        filename = '{}-orig.log'.format(job.job_id)
        return os.path.join(self.get_reproduce_tmp_dir(job), filename)

    def get_jobpair_dir(self, job, run=None):
        if run:
            task_dir = "{}_run{}".format(self.config.current_task_dir, run)
            return os.path.join(task_dir, job.buildpair_name, job.jobpair_name)
        else:
            return os.path.join(self.config.current_task_dir, job.buildpair_name, job.jobpair_name)

    def get_abs_jobpair_dir(self, job):
        return os.path.abspath(self.get_jobpair_dir(job))

    def get_log_path_in_task(self, job, run=None):
        return os.path.join(self.get_jobpair_dir(job, run), Utils.construct_log_name(job))

    def get_patch_path_in_task(self, job, run=None):
        return os.path.join(self.get_jobpair_dir(job, run), Utils.construct_patch_name(job))

    def get_travis_build_log_path_in_task(self, job):
        filename = '{}-travis.log'.format(job.job_id)
        return os.path.join(self.get_jobpair_dir(job), filename)

    def get_tar_file_storage_dir_in_task(self, job):
        return os.path.join(self.config.current_task_dir, job.buildpair_name, 'repo_tarfiles')

    def get_tar_file_in_jobpair_dir(self, job):
        filename = 'failed.tar' if job.is_failed == 'failed' else 'passed.tar'
        return os.path.join(self.get_jobpair_dir(job), filename)

    def get_orig_log_path(self, job_id):
        filename = '{}-orig.log'.format(job_id)
        return os.path.join(self.config.orig_logs_dir, filename)

    def get_orig_log_path_in_jobpair_dir(self, job):
        return os.path.join(self.get_jobpair_dir(job), '{}-orig.log'.format(job.job_id))

    @staticmethod
    def get_custom_build_log_path(job, custom_repo_dir):
        return os.path.join(custom_repo_dir, 'reproduce_tmp', Utils.construct_log_name(job))

    def get_error_reason_file_path(self):
        return os.path.join(self.config.current_task_dir, 'error_reason.json')

    # --------------------------------------------
    # ---------- Copy helper functions -----------
    # --------------------------------------------

    def copy_logs_into_current_task_dir(self, job):
        if self.check_if_log_exist(job):
            self.copy_log_into_current_task_dir(job)

    def copy_log_into_current_task_dir(self, job):
        shutil.copy(self.get_log_path(job), self.get_jobpair_dir(job))

    def copy_orig_log_into_current_task_dir(self, job):
        shutil.copy(self.get_orig_travis_log_path(job), self.get_jobpair_dir(job))

    def copy_build_sh_into_current_task_dir(self, job):
        shutil.copy(self.get_build_sh_path(job), self.get_jobpair_dir(job))

    def copy_travis_build_log_into_current_task_dir(self, job):
        shutil.copy(self.get_travis_build_log_path(job), self.get_jobpair_dir(job))

    def copy_dockerfile_into_current_task_dir(self, job):
        shutil.copy(self.get_dockerfile_path(job), self.get_jobpair_dir(job))

    def copy_repo_tar_into_current_task_dir(self, job):
        os.makedirs(self.get_tar_file_storage_dir_in_task(job), exist_ok=True)
        shutil.copy(self.get_repo_tar_path(job), self.get_repo_tar_path_in_task(job))

    def copy_repo_tar_from_storage_into_jobpair_dir(self, job):
        shutil.copy(self.get_repo_tar_path_in_task(job), self.get_jobpair_dir(job))

    def copy_orig_log_into_jobpair_dir(self, job):
        shutil.copy(self.get_orig_log_path(job.job_id), self.get_jobpair_dir(job))

    def copy_build_sh(self, job):
        build_sh = os.path.join(self.get_reproducing_repo_dir(job), 'reproduce_tmp', 'build.sh')
        dst = os.path.join(self.get_jobpair_dir(job), 'repo', 'reproduce_tmp', job.build_job)
        os.makedirs(dst, exist_ok=True)
        shutil.copy(build_sh, dst)

    # --------------------------------------------
    # ---------- Other helper functions ----------
    # --------------------------------------------

    def check_is_bad_log(self, job, file_path=None):
        file_path = file_path or self.get_log_path(job)
        first = True
        if os.path.isfile(file_path):
            try:
                with open(file_path) as f:
                    for l in f:
                        if first:
                            if '"docker logs" requires exactly 1 argument.' in l:
                                return True
                        if 'port is already allocated.' in l:
                            return True
            except UnicodeDecodeError:
                log.debug('UnicodeDecodeError while check_is_bad_log')
        return False

    @staticmethod
    def check_is_bad_travis_build_log(file):
        known_errors = ['repository not known', 'undefined method']
        if os.path.isfile(file):
            with open(file) as f:
                for l in f:
                    for err in known_errors:
                        if err in l:
                            return False
        return True

    @staticmethod
    def get_buildpair_from_pair_name(pair_center, pair_name):
        for r in pair_center.repos:
            for bp in pair_center.repos[r].buildpairs:
                if bp.buildpair_name == pair_name:
                    return bp

    @staticmethod
    def has_failed_test(buildpair):
        for j in buildpair.builds[0].jobs:
            if j.reproduced_result:
                if j.reproduced_result['tr_log_num_tests_failed'] != 'NA':
                    if j.reproduced_result['tr_log_num_tests_failed'] > 0:
                        return True
        return False

    def construct_path_to_store_custom_build_logs(self, job):
        return os.path.join(self.get_jobpair_dir(job), 'custom')

    @staticmethod
    def construct_mmm_count(pair_center):
        return '-'.join(map(str, [len(pair_center.get_buildpair_matching(1)),
                                  len(pair_center.get_buildpair_matching(2)),
                                  len(pair_center.get_buildpair_matching(3))]))

    @staticmethod
    def construct_aaa_count(pair_center):
        return '-'.join(map(str, [len(pair_center.get_jobpair_matching(1)),
                                  len(pair_center.get_jobpair_matching(2)),
                                  len(pair_center.get_jobpair_matching(3))]))

    # The following two methods determine an artifact's Docker image tag.

    @staticmethod
    def construct_jobpair_image_tag(jobpair) -> str:
        """
        Construct a Docker image tag from a Jobpair object.
        :param jobpair: Jobpair object
        :return: Docker image tag
        """
        return bugswarmutils.get_image_tag(jobpair.repo_slug, jobpair.jobs[0].job_id)

    @staticmethod
    def construct_jobpair_image_tag_from_dict(jobpair, slug) -> str:
        """
        Construct a Docker image tag from a dict representation of a jobpair and a repo slug.
        :param jobpair: A dict representation of a jobpair
        :param slug: The repo slug for the project from which the jobpair originates.
        :return: Docker image tag
        """
        return bugswarmutils.get_image_tag(slug, jobpair['failed_job']['job_id'])

    def construct_full_image_name(self, image_tag):
        return '{}:{}'.format(self.config.dockerhub_repo, image_tag)

    @staticmethod
    def check_disk_space_available():
        total_b, used_b, free_b = shutil.disk_usage('.')
        available = free_b / total_b
        if available < 0.2:
            percent = str(round(available * 100, 2))
            log.warning('Inadequate disk space available for reproducing: {}%.'.format(percent))
            return False
        return True

    def remove_project_repos_dir(self):
        log.info('Removing project_repos directory.')
        command = 'rm -rf {} 2> /dev/null'.format(self.config.stored_repos_dir)
        ShellWrapper.run_commands(command, shell=True)

    def clean_workspace_job_dir(self, job):
        log.info('cleaning workspace job directory.')
        command = 'rm -rf {}'.format(self.get_workspace_sha_dir(job))
        ShellWrapper.run_commands(command, shell=True)

    def remove_workspace_dir(self):
        log.info('Removing workspace directory.')
        command = 'rm -rf {} 2> /dev/null'.format(self.config.workspace_dir)
        ShellWrapper.run_commands(command, shell=True)

    def clean_disk_usage(self, job_dispatcher, docker):
        docker.remove_all_images()
        self.remove_project_repos_dir()
        job_dispatcher.workspace_locks = job_dispatcher.manager.dict()
        job_dispatcher.cloned_repos = job_dispatcher.manager.dict()

    @staticmethod
    def deep_copy(tags):
        new_tags = {}
        for k, v in tags.items():
            new_tags[k] = v
        return new_tags

    def get_reproduced_logs(self):
        if not os.path.isdir(self.config.reproduced_logs_dir):
            log.info('Cannot find', self.config.reproduced_logs_dir)
            return {}

        reproduced_logs = collections.defaultdict(list)
        for filename in os.listdir(self.config.reproduced_logs_dir):
            # Actual filename example: testdeploy_j187615034.1.56qumdwtpyrnw5glxbb2ogykf-2c3a0cf689ea.log
            split = filename.split('.')
            job_id = split[0]  # Do some parsing?
            run_number = int(split[1])
            reproduced_logs[job_id].append(run_number)
        return reproduced_logs

    @staticmethod
    def get_analyzer_version() -> str:
        stdout, stderr, returncode = ShellWrapper.run_commands('cd .. && git rev-parse HEAD',
                                                               stdout=subprocess.PIPE,
                                                               shell=True)
        if returncode:
            msg = 'Error getting analyzer version: {}'.format(stderr)
            log.error(msg)
            raise IOError(msg)
        return stdout

    @staticmethod
    def get_reproducer_version() -> str:
        stdout, stderr, returncode = ShellWrapper.run_commands('git rev-parse HEAD', stdout=subprocess.PIPE, shell=True)
        if returncode:
            msg = 'Error getting reproducer version: {}'.format(stderr)
            log.error(msg)
            raise IOError(msg)
        return stdout
