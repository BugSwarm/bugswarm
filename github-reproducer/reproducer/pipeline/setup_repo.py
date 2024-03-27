import distutils.dir_util
import git
import os
import tarfile
import time
import urllib.request
import zipfile

from bugswarm.common import log

from reproducer.reproduce_exception import GitError, RepoSetupError


def setup_repo(job, utils, job_dispatcher):
    to_setup_repo = False
    clone_repo = False
    wait_for_repo_cloned = False
    wait_for_repo_setup = False
    job_id = job.job_id

    if job.repo in job_dispatcher.cloned_repos and job_dispatcher.cloned_repos[job.repo] == -1:
        # Already tried cloning this repository and failed. So skip it.
        raise RepoSetupError('Previously encountered an error while cloning a repository. Skipping.')
    if job_id in job_dispatcher.workspace_locks and job_dispatcher.workspace_locks[job_id] == -1:
        # Already tried setting up this repository and failed. So skip it.
        raise RepoSetupError('Previously encountered an error while setting up a repository. Skipping.')

    # ------------ Clone repository -----------

    job_dispatcher.lock.acquire()
    if job.repo not in job_dispatcher.cloned_repos:
        job_dispatcher.cloned_repos[job.repo] = 0
        clone_repo = True
    elif job_dispatcher.cloned_repos[job.repo] == 0:
        wait_for_repo_cloned = True
    job_dispatcher.lock.release()

    if wait_for_repo_cloned:
        while job_dispatcher.cloned_repos[job.repo] == 0:
            time.sleep(3)

        if job_dispatcher.cloned_repos[job.repo] == -1:
            raise RepoSetupError('Another process failed to clone the repo {}'.format(job.repo))

    if clone_repo:
        try:
            clone_project_repo_if_not_exists(utils, job)
        except KeyboardInterrupt:
            log.error('Caught a KeyboardInterrupt while cloning a repository.')
            raise
        except Exception as e:
            job_dispatcher.cloned_repos[job.repo] = -1
            job_dispatcher.job_center.repos[job.repo].clone_error = True
            job_dispatcher.job_center.repos[job.repo].set_all_jobs_in_repo_to_skip()

            if isinstance(e, git.GitError):
                raise GitError('Encountered an error while cloning a repository: {!r}'.format(e))
            else:
                raise RepoSetupError('Encountered an error while cloning a repository: {!r}'.format(e))
        else:
            job_dispatcher.cloned_repos[job.repo] = 1
            job_dispatcher.job_center.repos[job.repo].has_repo = True

    # -------  setup_repo: Copy, reset, and tar -------

    job_dispatcher.lock.acquire()
    if job_id not in job_dispatcher.workspace_locks:
        job_dispatcher.workspace_locks[job_id] = 0
        to_setup_repo = True
    else:
        if job_dispatcher.workspace_locks[job_id] == 0:
            wait_for_repo_setup = True
    job_dispatcher.lock.release()

    if wait_for_repo_setup:
        while job_dispatcher.workspace_locks[job_id] == 0:
            time.sleep(3)
        if job_dispatcher.workspace_locks[job_id] == -1:
            raise RepoSetupError('Another process failed to set up the repo {}'.format(job.repo))

    if to_setup_repo:
        try:
            if job.resettable is False and job.github_archived is True:
                download_repo(job, utils)
            elif job.resettable is True:
                copy_and_reset_repo(job, utils)
            else:
                raise RepoSetupError('Job is neither resettable nor GitHub archived.')
        except KeyboardInterrupt:
            log.error('Caught a KeyboardInterrupt while setting up a repository.')
            raise
        except Exception as e:
            job_dispatcher.workspace_locks[job_id] = -1
            if isinstance(e, RepoSetupError):
                raise
            if isinstance(e, git.GitError):
                raise GitError('Encountered an error while setting up a repository: {!r}'.format(e))
            raise RepoSetupError('Encountered an error while setting up a repository: {!r}'.format(e))
        else:
            job_dispatcher.workspace_locks[job_id] = 1
    else:
        log.debug('Job', job_id, 'is already set up.')


def clone_project_repo_if_not_exists(utils, job):
    if not utils.check_if_project_repo_exist(job.repo):
        os.makedirs(utils.get_repo_storage_dir(job), exist_ok=True)
        git.Repo.clone_from(utils.construct_github_repo_url(job.repo), utils.get_repo_storage_dir(job))
        repo = git.Repo(utils.get_repo_storage_dir(job))
        with repo.config_writer('repository') as cw:
            cw.add_section('user')
            cw.set('user', 'name', 'BugSwarm')
            cw.set('user', 'email', 'dev.bugswarm@gmail.com')

    with tarfile.open(utils.get_project_storage_repo_tar_path(job), 'w') as tar:
        tar.add(utils.get_repo_storage_dir(job), arcname=job.repo)


def copy_and_reset_repo(job, utils):
    log.info('Copying and resetting the repository.')
    retry_count = 0
    max_retries = 3
    last_error = None

    while True:
        if retry_count > max_retries:
            raise RepoSetupError('Max retries exceeded for untarring repo {}: {}.'.format(job.repo, repr(last_error)))

        try:
            # Copy repository from stored project repositories to the workspace repository directory by untar-ing the
            # storage repository tar file into the workspace directory.
            repo_tar_obj = tarfile.TarFile(name=utils.get_project_storage_repo_tar_path(job))
            utils.clean_workspace_job_dir(job)
            # TODO: This line causes missing or bad subsequent header
            repo_tar_obj.extractall(utils.get_workspace_sha_dir(job))
            break
        except Exception as e:
            last_error = e
            log.info('Failed to extract the repository due to {}'.format(repr(e)))
            retry_count += 1
            time.sleep(5)
            continue

    # git reset the workspace repository.
    repo = git.Repo(utils.get_reproducing_repo_dir(job))

    if job.is_pr:
        # We're in a PR job pair; reset to the merge SHA
        try:
            # git fetch origin <merge-sha>
            # git reset --hard <merge-sha>
            log.info('Resetting to merge SHA {}'.format(job.travis_merge_sha))
            repo.remote().fetch(job.travis_merge_sha)
            repo.head.reset(job.travis_merge_sha, index=True, working_tree=True)
        except git.GitCommandError:
            # Fallback: reset to the  base SHA and merge the head SHA
            # git fetch origin <head-sha>
            # git fetch origin <base-sha>
            # git reset --hard <base-sha>
            # git merge <head-sha>
            log.info('Cannot reset to merge SHA. Resetting to base {} and merging head {}'.format(
                job.base_sha, job.sha))
            repo.remote().fetch(job.sha)
            repo.remote().fetch(job.base_sha)
            repo.head.reset(job.base_sha, index=True, working_tree=True)
            repo.git.merge(job.sha)
    else:
        # git fetch origin <head-sha>
        # git reset --hard <head-sha>
        log.info('Resetting to head SHA {}'.format(job.sha))
        repo.remote().fetch(job.sha)
        repo.head.reset(job.sha, index=True, working_tree=True)

    # Check out all the submodules.
    repo.git.submodule('update', '--init')


def download_repo(job, utils):
    # Make the workspace repository directory.
    # Note: We have no way to check out the correct version of submodule!
    job_archive_dir = utils.get_stored_repo_archives_path(job)
    repo_unzip_name = job.repo.split('/')[1] + '-' + job.sha
    repo_zip_path = utils.get_project_storage_repo_zip_path(job)

    os.makedirs(job_archive_dir, exist_ok=True)
    retry_count = 0
    max_retries = 3
    last_error = None

    while True:
        if retry_count > max_retries:
            raise RepoSetupError(
                'Max retries exceeded for downloading zip file for repo {}: {}.'.format(job.repo, last_error))

        try:
            # Download the repository.
            if not os.path.exists(repo_zip_path):
                if job.is_pr:
                    src = utils.construct_github_archive_repo_sha_url(job.repo, job.travis_merge_sha)
                else:
                    src = utils.construct_github_archive_repo_sha_url(job.repo, job.sha)
                log.debug('Downloading the repository from the GitHub archive at {}.'.format(src))
                urllib.request.urlretrieve(src, repo_zip_path)

            # Copy repository from stored project repositories to the workspace repository directory by
            # untar-ing the storage repository tar file into the workspace directory.
            repo_zip_obj = zipfile.ZipFile(repo_zip_path)
            repo_zip_obj.extractall(job_archive_dir)
            break
        except Exception as e:
            last_error = e
            log.info('Failed to download the repository due to {}'.format(repr(e)))
            retry_count += 1

            if os.path.exists(repo_zip_path):
                os.remove(repo_zip_path)
            time.sleep(5)
            continue

    distutils.dir_util.copy_tree(os.path.join(job_archive_dir, repo_unzip_name),
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
