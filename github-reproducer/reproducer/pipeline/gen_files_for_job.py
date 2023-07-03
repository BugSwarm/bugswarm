import os
from os.path import isfile

from bugswarm.common.log_downloader import download_log
from reproducer.pipeline.setup_repo import setup_repo
from reproducer.pipeline.setup_repo import tar_repo
# TODO: Add them to the pipeline
# from reproducer.pipeline.modify_build_sh import patch_build_script
from reproducer.pipeline.gen_dockerfile import gen_dockerfile
from reproducer.pipeline.gen_script import gen_script
from reproducer.pipeline.apply_patching import modify_deprecated_links


def gen_files_for_job(job_dispatcher, job, copy_files=False, dependency_solver=False):
    """
    This function generates the files needed to reproduce a job.
    It begins running the steps to reproduce a job. The steps are explained in the comments.
    The steps are mainly calling functions written in the `pipeline` folder.
    Steps:
      Pre-job step: check for skipping
      1. Setup workspace repository: copy, reset, and tar the repository
      2. Ensure .travis.yml exists. Otherwise, skip the job
      3. Download the original log.
      4. Generate the build script with travis-build.
      5. Generate the Dockerfile.
      6. Build the Docker image.
      7. Spawn the Docker container.
      Post-job step: copying files

    :param job_dispatcher:
    :param job:
    :param copy_files:
    :param build_path:
    """
    job_dispatcher.utils.setup_jobpair_dir(job)

    # If all three essential items to build a job are in the task folder, copy them to the workspace folder and return.
    repo_in_task_path = job_dispatcher.utils.get_repo_tar_path_in_task(job)
    build_sh_in_task_path = job_dispatcher.utils.get_build_sh_path_in_task(job)
    dockerfile_in_task_path = job_dispatcher.utils.get_dockerfile_in_task_path(job)
    if isfile(repo_in_task_path) and isfile(build_sh_in_task_path) and isfile(dockerfile_in_task_path):
        # Before copying from the task directory into the workspace directory, make the workspace folder. If this branch
        # is not executed, the directory is created in `setup_repo`.
        os.makedirs(job_dispatcher.utils.get_reproduce_tmp_dir(job), exist_ok=True)
        job_dispatcher.utils.copy_repo_from_task_into_workspace(job)
        job_dispatcher.utils.copy_build_sh_from_task_into_workspace(job)
        job_dispatcher.utils.copy_dockerfile_from_task_into_workspace(job)
        return

    # STEP 1: Clone, copy, reset, the repository.
    setup_repo(job, job_dispatcher.utils, job_dispatcher)
    reproduce_tmp_path = job_dispatcher.utils.get_reproduce_tmp_dir(job)
    os.makedirs(reproduce_tmp_path, exist_ok=True)

    # Apply patching on project's pom.xml
    reproducer_repo_dir = job_dispatcher.utils.get_reproducing_repo_dir(job)
    modify_deprecated_links(reproducer_repo_dir)

    # STEP 2: Download the original log if we do not yet have it.
    original_log_path = job_dispatcher.utils.get_orig_log_path(job.job_id)
    if not isfile(original_log_path):
        download_log(job.job_id, original_log_path, repo=job.repo)

    # STEP 3: Generate the build script with GitHub builder and then modify and patch it.
    build_sh_path = job_dispatcher.utils.get_build_sh_path(job)
    if not isfile(build_sh_path):
        gen_script(job_dispatcher.utils, job, dependency_solver)
        # Attempt to patch any deprecated links in build script
        modify_deprecated_links(build_sh_path)
        # Check if job is java and is jdk7. If so, then patch the build.sh file by adding flags to mvn command to use
        # TLSv1.2 instead of the default TLSv1.0.
        for step in job.config.get('steps', []):
            if 'uses' in step and 'with' in step:
                if step.get('uses').startswith('actions/setup-java') and step.get('with').get('java-version') == 7:
                    # patch_build_script(build_sh_path)
                    pass

    # STEP 3.5: Tar the repository.
    tar_path = job_dispatcher.utils.get_repo_tar_path(job)
    if not isfile(tar_path):
        tar_repo(job, job_dispatcher.utils)

    # STEP 4: Generate the Dockerfile.
    dockerfile_path = job_dispatcher.utils.get_dockerfile_path(job)
    if not isfile(dockerfile_path):
        gen_dockerfile(job, dockerfile_path)

    # Post-job step.
    if copy_files:
        _copy_workspace_files(job_dispatcher.utils, job)


def _copy_workspace_files(utils, job):
    # Copy build directory if it exists.
    if utils.check_if_build_sh_exist(job):
        try:
            utils.copy_build_dir_into_current_task_dir(job)
        except FileExistsError:
            pass

    # Copy the Dockerfile.
    if utils.check_if_dockerfile_exist(job):
        utils.copy_dockerfile_into_current_task_dir(job)

    # Copy the repository as a tar file.
    if utils.check_if_repo_tar_exist(job):
        if not isfile(utils.get_repo_tar_path_in_task(job)):
            utils.copy_repo_tar_into_current_task_dir(job)
