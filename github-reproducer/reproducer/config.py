import os

from bugswarm.common.credentials import DOCKER_HUB_PASSWORD, DOCKER_HUB_REPO, DOCKER_HUB_USERNAME, \
    DOCKER_REGISTRY_PASSWORD, DOCKER_REGISTRY_REPO, DOCKER_REGISTRY_USERNAME


class Config(object):
    def __init__(self, task):
        self.task = task
        self.stored_repos_dir = 'intermediates/project_repos'
        self.workspace_dir = 'intermediates/workspace'
        self.orig_logs_dir = 'intermediates/orig_logs'
        self.reproduce_tmp_dir = 'reproduce_tmp'
        self.tasks_dir = 'output/tasks'
        self.txt_dir = 'output/txt'
        self.output_dir = 'output'
        self.result_json_dir = 'output/result_json'
        self.current_task_dir = os.path.join(self.tasks_dir, task)
        self.reproduced_logs_dir = 'outout/reproduced_logs'
        self.csv_dir = 'output/csv'  # Deprecated. Was previously, but is no longer, used bythe metadata Packager.
        self.verbose = False
        self.skip_check_disk = False
        self.disk_space_requirement = 50 * 1024**3         # 50 GiB
        self.docker_disk_space_requirement = 50 * 1024**3  # 50 GiB
        self.docker_hub_user = DOCKER_HUB_USERNAME
        self.docker_hub_pass = DOCKER_HUB_PASSWORD
        self.docker_hub_repo = DOCKER_HUB_REPO
        self.docker_registry_user = DOCKER_REGISTRY_USERNAME
        self.docker_registry_pass = DOCKER_REGISTRY_PASSWORD
        self.docker_registry_repo = DOCKER_REGISTRY_REPO
        self.container_cpu_share = 4  # Equivalent to the '--cpus' flag in 'docker run'. 0 for no limit.
        self.container_mem_limit = '16g'
        self.tar_repo_sh = 'reproducer/pipeline/tar_repo.sh'
        self.copy_and_reset_sh = 'reproducer/pipeline/copy_and_reset.sh'
        self.travis_build_sh = 'reproducer/pipeline/travis_build.sh'
        self.build_and_spawn_sh = 'reproducer/pipeline/build_and_spawn.sh'
        self.tarfile_name = 'repo-to-docker.tar'
        self.script_to_run_failed_job = '/usr/local/bin/run_failed.sh'
        self.script_to_run_passed_job = '/usr/local/bin/run_passed.sh'
        self.travis_images_json = 'reproducer/travis_images.json'
