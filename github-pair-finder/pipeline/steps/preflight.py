import os

from bugswarm.common import log
from git import GitDB, Repo


def repo_clone_path(repo):
    return os.path.abspath('./intermediates/repos/{}'.format(repo.replace('/', '-')))


class Preflight:
    def process(self, data, context):
        repo = context['repo']
        repo_path = repo_clone_path(repo)

        # Clone repo
        if os.path.isdir(repo_path):
            log.info('Clone of repo {} already exists.'.format(repo))

            # Explicitly set odbt, or else Repo.iter_commits fails with a broken pipe. (I don't know why.)
            # (Possibly related: https://github.com/gitpython-developers/GitPython/issues/427)
            repo_obj = Repo(repo_path, odbt=GitDB)
        else:
            log.info('Cloning repo {}...'.format(repo))
            repo_obj = Repo.clone_from('https://github.com/{}'.format(repo), repo_path, odbt=GitDB)
            log.info('Cloning done.')

        # Fetch refs for all pulls and PRs
        repo_obj.remote('origin').fetch('refs/pull/*/head:refs/remotes/origin/pr/*')

        # Get all shas
        shas = [commit.hexsha for commit in repo_obj.iter_commits(branches='', remotes='')]
        context['shas'] = shas

        # Get head commit
        context['head_commit'] = repo_obj.head.commit.hexsha

        return data
