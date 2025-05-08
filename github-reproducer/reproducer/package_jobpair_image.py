from os.path import isfile, join
import shutil

from bugswarm.common import log
from bugswarm.common.log_downloader import download_log

from reproducer.docker_wrapper import DockerWrapper
from reproducer.model.jobpair import JobPair
from reproducer.utils import Utils
from reproducer.reproduce_exception import ReproduceError, wrap_errors


def package_jobpair_image(utils: Utils, docker: DockerWrapper, jobpair: JobPair, copy_files=False, push=True,
                          cleanup_after=False):
    with wrap_errors('Move build files'):
        _move_build_files(utils, jobpair)
    with wrap_errors('Copy orig logs'):
        _copy_original_logs(utils, jobpair)
    with wrap_errors('Modify build script'):
        _modify_script(utils, jobpair)
    with wrap_errors('Write dockerfile'):
        _write_package_dockerfile(utils, jobpair)

    image_tag = utils.construct_jobpair_image_tag(jobpair)
    full_image_name = utils.construct_full_image_name(image_tag)

    with wrap_errors('Build and push artifact image'):
        docker.build_image(utils.get_jobpair_workspace_dir(jobpair),
                           utils.get_abs_jobpair_dockerfile_path(jobpair),
                           full_image_name)

        if push:
            docker.push_image(image_tag)
        if cleanup_after:
            docker.remove_image(full_image_name)

    with wrap_errors('Copy workspace files'):
        if copy_files:
            _copy_workspace_files(utils, jobpair)


def _move_build_files(utils: Utils, jobpair: JobPair):
    shutil.rmtree(utils.get_jobpair_workspace_dir(jobpair))
    utils.move_build_dirs_into_pair_workspace_dir(jobpair)
    utils.move_dockerfiles_into_pair_workspace_dir(jobpair)
    utils.move_repo_tars_into_pair_workspace_dir(jobpair)


def _copy_original_logs(utils: Utils, jobpair: JobPair):
    for j in jobpair.jobs:
        original_log_path = utils.get_orig_log_path(j.job_id)
        if not isfile(original_log_path) and not download_log(j.job_id, original_log_path, repo=j.repo):
            raise ReproduceError('Could not download the log for job {}.'.format(j.job_id))
    utils.copy_orig_logs_into_pair_workspace_dir(jobpair)


def _modify_script(utils: Utils, jobpair: JobPair):
    for j in jobpair.jobs:
        script_path = join(utils.get_jobpair_workspace_dir(jobpair), j.job_id, 'run.sh')
        if not isfile(script_path):
            log.error('Script file not found at', script_path)
            return 1

        lines = []
        with open(script_path) as f:
            found_build_path = False
            for line in f:
                if not found_build_path and line.startswith('export GITHUB_WORKSPACE='):
                    # Usually is the second line.
                    lines.append('export GITHUB_WORKSPACE={}\n'.format(
                        '/home/github/build/{}/{}'.format(j.f_or_p, j.repo))
                    )
                    found_build_path = True
                else:
                    lines.append(line)

            if not found_build_path:
                raise ReproduceError(
                    'Could not find where GITHUB_WORKSPACE was set in the script for job {}.'.format(j.job_id))

        with open(script_path, 'w') as f:
            for l in lines:
                f.write(l)


def _write_package_dockerfile(utils: Utils, jobpair: JobPair):
    failed_job_id = jobpair.jobs[0].job_id
    passed_job_id = jobpair.jobs[1].job_id

    failed_dockerfile_path = join(utils.get_jobpair_workspace_dir(jobpair), failed_job_id + '-Dockerfile')
    passed_dockerfile_path = join(utils.get_jobpair_workspace_dir(jobpair), passed_job_id + '-Dockerfile')

    with open(failed_dockerfile_path) as f:
        failed_lines = list(map(str.strip, f.readlines()))

    with open(passed_dockerfile_path) as f:
        passed_lines = list(map(str.strip, f.readlines()))

    # Check that both the failed job and the passed job used the same Travis Docker image.
    if failed_lines[0] != passed_lines[0]:
        raise ReproduceError('The failed job and the passed job used different Travis Docker images.')

    job_runner = failed_lines[0].startswith('FROM bugswarm/githubactionsjobrunners')

    # TODO: CentOS, RHEL base image
    lines = [
        failed_lines[0],  # Base image
    ]

    if not job_runner:
        # If we are running in container image, then we need to install the following tools:
        # cat (for build script), node (for custom actions), python3 (for expression handling)
        lines += [
            'RUN apt-get update && apt-get -y install sudo curl coreutils python3 vim',
            'RUN apt-get install -y python-is-python3 || sudo ln -s /usr/bin/python3 /usr/bin/python',
            'RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -',
            'RUN apt-get install -y nodejs'
        ]

    lines += [
        # Remove PPA and clean APT
        'RUN sudo rm -rf /var/lib/apt/lists/*',
        'RUN sudo rm -rf /etc/apt/sources.list.d/*',
        'RUN sudo apt-get clean',

        # Update OpenSSL and libssl to avoid using deprecated versions of TLS (TLSv1.0 and TLSv1.1).
        # TODO: Do we actually only want to do this when deriving from an image that has an out-of-date version of TLS?
        'RUN sudo apt-get update && sudo apt-get -y install --only-upgrade openssl libssl-dev vim',

        'RUN echo "TERM=dumb" >> /etc/environment',
        # Hooks can set environment variable using /etc/reproducer-environment
        'RUN touch /etc/reproducer-environment && chmod 777 /etc/reproducer-environment',

        # Otherwise: docker: Error response from daemon: unable to find user GitHub: no matching entries in passwd file.
        'RUN useradd -ms /bin/bash github',

        # Enable passwordless sudo; see
        # https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners#administrative-privileges
        'RUN echo "ALL ALL=(ALL:ALL) NOPASSWD: ALL" >> /etc/sudoers',

        # Add the repositories.
        'ADD failed.tar /home/github/build/failed/',
        'ADD passed.tar /home/github/build/passed/',

        # Add the original logs.
        'ADD {}-orig.log /home/github/build/'.format(failed_job_id),
        'ADD {}-orig.log /home/github/build/'.format(passed_job_id),

        # Add the build scripts and predefined action.
        'ADD --chown=github:github {}/run.sh /usr/local/bin/run_failed.sh'.format(failed_job_id),
        'ADD --chown=github:github {}/actions /home/github/{}/actions'.format(failed_job_id, failed_job_id),
        'ADD --chown=github:github {}/steps /home/github/{}/steps'.format(failed_job_id, failed_job_id),
        'ADD --chown=github:github {}/helpers /home/github/{}/helpers'.format(failed_job_id, failed_job_id),
        'ADD --chown=github:github {}/event.json /home/github/{}/event.json'.format(failed_job_id, failed_job_id),
        'RUN chmod 777 /usr/local/bin/run_failed.sh',
        'RUN chmod -R 777 /home/github/{}'.format(failed_job_id),

        'ADD --chown=github:github {}/run.sh /usr/local/bin/run_passed.sh'.format(passed_job_id),
        'ADD --chown=github:github {}/actions /home/github/{}/actions'.format(passed_job_id, passed_job_id),
        'ADD --chown=github:github {}/steps /home/github/{}/steps'.format(passed_job_id, passed_job_id),
        'ADD --chown=github:github {}/helpers /home/github/{}/helpers'.format(passed_job_id, passed_job_id),
        'ADD --chown=github:github {}/event.json /home/github/{}/event.json'.format(passed_job_id, passed_job_id),
        'RUN chmod 777 /usr/local/bin/run_passed.sh',
        'RUN chmod -R 777 /home/github/{}'.format(passed_job_id),

        # Let user own the entire /home directory to avoid permission issue.
        # If we are running using our job image, then don't chmod /home/linuxbrew because it is huge.
        # Need to manually remove linuxbrew for now. Next time we update our base images we should remove it directly.
        'RUN rm -rf /home/linuxbrew && chown -R github:github /home',

        # Set the user to use when running the image.
        'USER github',

        # Override ENTRYPOINT so `docker run` works as expected
        'ENTRYPOINT []',
        # Default command: run a shell
        'CMD ["/bin/bash"]',
    ]
    # Append a newline to each line and then concatenate all the lines.
    content = ''.join(map(lambda l: l + '\n', lines))
    package_dockerfile = utils.get_abs_jobpair_dockerfile_path(jobpair)
    with open(package_dockerfile, 'w') as f:
        f.write(content)


def _copy_workspace_files(utils: Utils, jobpair: JobPair):
    outdir = utils.get_jobpair_dir(jobpair.jobs[0])
    shutil.rmtree(outdir)
    shutil.copytree(utils.get_jobpair_workspace_dir(jobpair), outdir)
