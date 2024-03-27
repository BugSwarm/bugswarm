import os


def repo_clone_path(repo):
    return os.path.abspath('./intermediates/repos/{}'.format(repo.replace('/', '-')))
