import os
import subprocess
import yaml

from bugswarm.common.json import write_json
from bugswarm.common.github_wrapper import GitHubWrapper
from bugswarm.common.shell_wrapper import ShellWrapper

from bugswarm.common.credentials import GITHUB_TOKENS

from reproducer.reproduce_exception import ReproduceError


def gen_script(utils, job, dependence_solver):
    """
    Invoke travis-build to generate the build script.
    """
    build_sh = os.path.join('reproduce_tmp', job.job_id + '.sh')
    reproducing_dir = utils.get_reproducing_repo_dir(job)

    if dependence_solver:
        from bugswarm.dependency_solver.dependency_solver import fix_dict
        pip_patch_result = os.path.join(utils.get_jobpair_dir(job), '{}-pip-patch.json'.format(job.job_id))
        commit_time = job.build.commit_time

        if not commit_time:
            github_wrapper = GitHubWrapper(GITHUB_TOKENS)
            _, commit_json = github_wrapper.get('https://api.github.com/repos/{}/git/commits/{}'
                                                .format(job.repo, job.travis_merge_sha))
            commit_time = commit_json['committer']['date']

        yaml_path = os.path.join(reproducing_dir, '.travis.yml')
        yaml_dict = job.config
        fixed_yaml_dict, pip_patch, apt_patch = fix_dict(reproducing_dir, yaml_dict, commit_time)
        with open(yaml_path, 'w+') as f:
            yaml.dump(fixed_yaml_dict, f)

        if pip_patch:
            write_json(pip_patch_result, pip_patch)
        # update travis compile path based on https://github.com/travis-ci/travis-build/pull/1137
        travis_command = '~/.travis/travis-build/bin/travis compile > {}'.format(build_sh)
    else:
        # default travis compile should include build number and job number to resolve the matrix
        travis_command = '~/.travis/travis-build/bin/travis compile {} > {}'.format(job.build_job, build_sh)
    cd_command = 'cd {}'.format(reproducing_dir)
    _, stderr, returncode = ShellWrapper.run_commands(cd_command, travis_command,
                                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    if returncode != 0:
        raise ReproduceError(
            'Encountered an error while generating the build script with travis-build: {}.'.format(stderr))
