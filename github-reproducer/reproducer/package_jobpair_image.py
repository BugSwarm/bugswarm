from os.path import isfile
from os.path import join

from bugswarm.common import log
from bugswarm.common.log_downloader import download_log

from reproducer.docker_wrapper import DockerWrapper
from reproducer.model.jobpair import JobPair
from reproducer.utils import Utils
from reproducer.reproduce_exception import ReproduceError


def package_jobpair_image(utils: Utils, docker: DockerWrapper, jobpair: JobPair):
    _copy_repo_tar(utils, jobpair)
    _copy_original_log(utils, jobpair)
    _modify_script(utils, jobpair)
    _write_package_dockerfile(utils, jobpair)

    image_tag = utils.construct_jobpair_image_tag(jobpair)
    full_image_name = utils.construct_full_image_name(image_tag)

    docker.build_image(utils.get_abs_jobpair_dir(jobpair.jobs[0]),
                       utils.get_abs_jobpair_dockerfile_path(jobpair),
                       full_image_name)

    docker.push_image(image_tag)

    _clean_after_package(utils, docker, jobpair, full_image_name)


def _copy_repo_tar(utils: Utils, jobpair: JobPair):
    for j in jobpair.jobs:
        if not utils.get_repo_tar_path_in_task(j):
            raise ReproduceError('Cannot find the repository tar file to copy for {}.'.format(j.job_id))
        utils.copy_repo_tar_from_storage_into_jobpair_dir(j)


def _copy_original_log(utils: Utils, jobpair: JobPair):
    for j in jobpair.jobs:
        original_log_path = utils.get_orig_log_path(j.job_id)
        if not download_log(j.job_id, original_log_path, repo=j.repo):
            raise ReproduceError('Error while copying the original log for {}.'.format(j.job_id))
        utils.copy_orig_log_into_jobpair_dir(j)


def _modify_script(utils: Utils, jobpair: JobPair):
    for j in jobpair.jobs:
        script_path = join(utils.get_jobpair_dir(jobpair.jobs[0]), j.job_id, 'run.sh')
        if not isfile(script_path):
            log.error('Script file not found at', script_path)
            return 1

        lines = []
        with open(script_path) as f:
            found_build_path = False
            for line in f:
                if not found_build_path and line.startswith('export BUILD_PATH='):
                    # Usually is the second line.
                    lines.append('export BUILD_PATH={}\n'.format('/home/github/build/{}/{}'.format(j.is_failed, j.repo)))
                    found_build_path = True
                else:
                    lines.append(line)

            if not found_build_path:
                raise ReproduceError('found_build_path is False for {}'.format(j.job_id))

        with open(join(utils.get_jobpair_dir(jobpair.jobs[0]), j.job_id, 'run.sh'), 'w') as f:
            for l in lines:
                f.write(l)


def _write_package_dockerfile(utils: Utils, jobpair: JobPair):
    failed_job_id = jobpair.jobs[0].job_id
    passed_job_id = jobpair.jobs[1].job_id

    failed_dockerfile_path = join(utils.get_jobpair_dir(jobpair.jobs[0]), failed_job_id + '-Dockerfile')
    passed_dockerfile_path = join(utils.get_jobpair_dir(jobpair.jobs[1]), passed_job_id + '-Dockerfile')

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
        # cat (for build script), node (for custom actions)
        lines += [
            'RUN apt-get update && apt-get -y install sudo curl coreutils',
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
        'RUN sudo apt-get update && sudo apt-get -y install --only-upgrade openssl libssl-dev',

        'RUN echo "TERM=dumb" >> /etc/environment',

        # Otherwise: docker: Error response from daemon: unable to find user GitHub: no matching entries in passwd file.
        'RUN useradd -ms /bin/bash github',

        # TODO: Do we need linuxbrew (it is huge)?
        # Let user own the entire /home directory to avoid permission issue.
        # If we are running using our job image, then don't chmod /home/linuxbrew because it is huge.
        'RUN chown github:github /home /home/github' if job_runner else 'RUN chown -R github:github /home',

        # Add the repositories.
        'ADD failed.tar /home/github/build/failed/',
        'ADD passed.tar /home/github/build/passed/',
        'RUN chown -R github:github /home/github/build/',

        # Add the original logs.
        'ADD {}-orig.log /home/github/build/'.format(failed_job_id),
        'ADD {}-orig.log /home/github/build/'.format(passed_job_id),

        # Add the build scripts and predefined action.
        'ADD --chown=github:github {}/run.sh /usr/local/bin/run_failed.sh'.format(failed_job_id),
        'ADD --chown=github:github {}/actions /home/github/{}/actions'.format(failed_job_id, failed_job_id),
        'ADD --chown=github:github {}/steps /home/github/{}/steps'.format(failed_job_id, failed_job_id),
        'RUN chmod 777 /usr/local/bin/run_failed.sh',
        'RUN chmod -R 777 /home/github/{}'.format(failed_job_id),

        'ADD --chown=github:github {}/run.sh /usr/local/bin/run_passed.sh'.format(passed_job_id),
        'ADD --chown=github:github {}/actions /home/github/{}/actions'.format(passed_job_id, passed_job_id),
        'ADD --chown=github:github {}/steps /home/github/{}/steps'.format(passed_job_id, passed_job_id),
        'RUN chmod 777 /usr/local/bin/run_passed.sh',
        'RUN chmod -R 777 /home/github/{}'.format(passed_job_id),

        # Set the user to use when running the image.
        'USER github',

        # Need bash, otherwise: Syntax error: redirection unexpected
        'ENTRYPOINT ["/bin/bash"]',
    ]
    # Append a newline to each line and then concatenate all the lines.
    content = ''.join(map(lambda l: l + '\n', lines))
    package_dockerfile = utils.get_abs_jobpair_dockerfile_path(jobpair)
    with open(package_dockerfile, 'w') as f:
        f.write(content)


def _clean_after_package(utils: Utils, docker: DockerWrapper, jobpair: JobPair, image_name: str):
    for j in jobpair.jobs:
        # Remove repo.
        Utils.remove_file(utils.get_tar_file_in_jobpair_dir(j))
        # Remove original log.
        Utils.remove_file(utils.get_orig_log_path_in_jobpair_dir(j))
    # Remove image
    # docker.remove_image_in_shell(image_name)
