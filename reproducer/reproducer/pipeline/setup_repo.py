import distutils.dir_util
import git
import os
import tarfile
import time
import urllib.request
import zipfile

from bugswarm.common import log

from reproducer.reproduce_exception import ReproduceError


def setup_repo(job, utils, job_dispatcher):
    to_setup_repo = False
    clone_repo = False
    wait_for_repo_cloned = False
    wait_for_repo_setup = False
    build_id = job.build.build_id

    if job.repo in job_dispatcher.cloned_repos and job_dispatcher.cloned_repos[job.repo] == -1:
        # Already tried cloning this repository and failed. So skip it.
        raise ReproduceError('Previously encountered an error while cloning a repository. Skipping.')
    if build_id in job_dispatcher.workspace_locks and job_dispatcher.workspace_locks[build_id] == -1:
        # Already tried setting up this repository and failed. So skip it.
        raise ReproduceError('Previously encountered an error while setting up a repository. Skipping.')

    # ------------ Clone repository -----------

    job_dispatcher.lock.acquire()
    if job.repo not in job_dispatcher.cloned_repos:
        job_dispatcher.cloned_repos[job.repo] = 0
        clone_repo = True
    else:
        if job_dispatcher.cloned_repos[job.repo] == 0:
            wait_for_repo_cloned = True
    job_dispatcher.lock.release()

    if wait_for_repo_cloned:
        while job_dispatcher.cloned_repos[job.repo] == 0:
            time.sleep(3)

        if job_dispatcher.cloned_repos[job.repo] == -1:
            raise ReproduceError('already error in cloning repo')

    if clone_repo:
        try:
            clone_project_repo_if_not_exists(utils, job)
        except KeyboardInterrupt:
            log.error('Caught a KeyboardInterrupt while cloning a repository.')
        except Exception:
            job_dispatcher.cloned_repos[job.repo] = -1
            job_dispatcher.job_center.repos[job.repo].clone_error = True
            job_dispatcher.job_center.repos[job.repo].set_all_jobs_in_repo_to_skip()
            raise ReproduceError('Encountered an error while cloning a repository.')
        else:
            job_dispatcher.cloned_repos[job.repo] = 1
            job_dispatcher.job_center.repos[job.repo].has_repo = True

    # -------  setup_repo: Copy, reset, and tar -------

    job_dispatcher.lock.acquire()
    if build_id not in job_dispatcher.workspace_locks:
        job_dispatcher.workspace_locks[build_id] = 0
        to_setup_repo = True
    else:
        if job_dispatcher.workspace_locks[build_id] == 0:
            wait_for_repo_setup = True
    job_dispatcher.lock.release()

    if wait_for_repo_setup:
        while job_dispatcher.workspace_locks[build_id] == 0:
            time.sleep(3)
        if job_dispatcher.workspace_locks[build_id] == -1:
            raise ReproduceError('already error in setup_repo')

    if to_setup_repo:
        try:
            if job.resettable is False and job.github_archived is True:
                download_repo(job, utils)
            elif job.resettable is True:
                copy_and_reset_repo(job, utils)
            else:
                raise ReproduceError('Job is neither resettable nor GitHub archived.')
        except KeyboardInterrupt:
            log.error('Caught a KeyboardInterrupt while setting up a repository.')
            raise
        except Exception as e:
            job_dispatcher.workspace_locks[build_id] = -1
            raise ReproduceError('Encountered an error while setting up a repository: {}'.format(e))
        else:
            job_dispatcher.workspace_locks[build_id] = 1
    else:
        log.debug('Job', job.job_id, 'is already set up.')

    # Lastly, check if .travis.yml exists in the repository. If not, skip.
    if not os.path.isfile(os.path.join(job_dispatcher.utils.get_reproducing_repo_dir(job), '.travis.yml')):
        raise ReproduceError('Cannot find .travis.yml in repository. Skipping.')


def clone_project_repo_if_not_exists(utils, job):
    if not utils.check_if_project_repo_exist(job.repo):
        os.makedirs(utils.get_repo_storage_dir(job), exist_ok=True)
        git.Repo.clone_from(utils.construct_github_repo_url(job.repo), utils.get_repo_storage_dir(job))
        utils.fetch_pr_data(job)


def copy_and_reset_repo(job, utils):
    log.info('Copying and resetting the repository.')

    # Copy repository from stored project repositories to the workspace repository directory by untar-ing the storage
    # repository tar file into the workspace directory.
    with tarfile.open(utils.get_project_storage_repo_tar_path(job), 'w') as tar:
        tar.add(utils.get_repo_storage_dir(job), arcname=job.repo)
    repo_tar_obj = tarfile.TarFile(name=utils.get_project_storage_repo_tar_path(job))
    utils.clean_workspace_job_dir(job)
    repo_tar_obj.extractall(utils.get_workspace_sha_dir(job))
    # git reset the workspace repository.
    repo = git.Repo(utils.get_reproducing_repo_dir(job))
    if job.is_pr:
        repo.git.reset('--hard', job.base_sha)
        repo.git.merge(job.sha)
    else:
        log.debug('Resetting repository to', job.sha, 'for job id', str(job.job_id) + '.')
        repo.git.reset('--hard', job.sha)


def download_repo(job, utils):
    # Make the workspace repository directory.
    os.makedirs(utils.get_stored_repo_path(job), exist_ok=True)

    # Download the repository.
    if job.is_pr:
        # Correct job sha is necessary for correct file path generation.
        job.sha = job.travis_merge_sha

    src = utils.construct_github_archive_repo_sha_url(job.repo, job.sha)
    repo_unzip_name = job.repo.split('/')[1] + '-' + job.sha

    log.info('Downloading the repository from the GitHub archive at {}.'.format(src))
    urllib.request.urlretrieve(src, utils.get_project_storage_repo_zip_path(job))

    # Copy repository from stored project repositories to the workspace repository directory by untar-ing the storage
    # repository tar file into the workspace directory.
    repo_zip_obj = zipfile.ZipFile(utils.get_project_storage_repo_zip_path(job))
    repo_zip_obj.extractall(utils.get_stored_repo_path(job))

    distutils.dir_util.copy_tree(os.path.join(utils.get_stored_repo_path(job), repo_unzip_name),
                                 utils.get_reproducing_repo_dir(job))
    distutils.dir_util.copy_tree(os.path.join(utils.get_repo_storage_dir(job), '.git'),
                                 os.path.join(utils.get_reproducing_repo_dir(job), '.git'))


def tar_repo(job, utils, dir_to_be_tar=None):
    if not dir_to_be_tar:
        dir_to_be_tar = utils.get_reproducing_repo_dir(job)
        reproduce_tmp_path = utils.get_reproduce_tmp_dir(job)
    else:
        reproduce_tmp_path = os.path.join(dir_to_be_tar, 'reproduce_tmp')
    tar_dst_path = os.path.join(reproduce_tmp_path, utils.config.tarfile_name)

    # Archive the repository into a tar file.
    tar_file_tmp_path = os.path.join(dir_to_be_tar, utils.config.tarfile_name)
    with tarfile.open(tar_file_tmp_path, 'w') as tar:
        tar.add(dir_to_be_tar, arcname=job.repo)
        # Omitting arcname=os.path.basename(source_dir) will maintain the entire path structure of source_dir in the tar
        # file. (In most situations, that's probably inconvenient.)

    # Make reproduce_tmp folder in workspace repository directory.
    os.makedirs(reproduce_tmp_path, exist_ok=True)

    # Move the tar file into the reproduce_tmp directory.
    os.rename(tar_file_tmp_path, tar_dst_path)
