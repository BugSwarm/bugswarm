"""
Generates a Dockerfile for the job we want to reproduce, so we can spawn a container of the image built from that
Dockerfile and then run the job.
"""
from bugswarm.common import log
from reproducer.model.job import Job
from reproducer.utils import Utils


def gen_dockerfile(image_tag: str, job: Job, utils: Utils, destination: str = None):
    """
    Generates a Dockerfile for reproducing a job.

    This only requires that we know which Travis base image from which to derive the generated Dockerfile.

    :param image_tag: The image tag that the original build used. This image tag will be used as the base image.
    :param job_id: The job ID identifying the original Travis job.
    :param utils: Utils object
    :param destination: Path where the generated Dockerfile should be written.
    """
    log.info('Use Docker image {} for job runner.'.format(image_tag))

    destination = destination or job.job_id + '-Dockerfile'
    _write_dockerfile(destination, image_tag, job.job_id, job.resettable, utils)
    log.debug('Wrote Dockerfile to {}'.format(destination))


def _write_dockerfile(destination: str, base_image: str, job_id: str, resettable: bool, utils: Utils):
    if base_image == '':
        base_image = utils.get_latest_image_tag(job_id)

    job_runner = base_image.startswith('bugswarm/githubactionsjobrunners')

    # TODO: CentOS, RHEL base image
    lines = [
        'FROM {}'.format(base_image),
    ]

    if not job_runner:
        # If we are running in container image, then we need to install the following tools:
        # cat (for build script), node (for custom actions), python3 (for expression handling)
        lines += [
            'RUN apt-get update && apt-get -y install sudo curl coreutils python3',
            'RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -',
            'RUN apt-get install -y nodejs'
        ]

    lines += [
        # If we are not using BugSwarm's job runner, then install sudo (for following commands),
        # cat (for build script), node (for custom actions), and vim (help debug), otherwise install vim only.
        # Remove PPA and clean APT
        'RUN sudo rm -rf /var/lib/apt/lists/*',
        'RUN sudo rm -rf /etc/apt/sources.list.d/*',
        'RUN sudo apt-get clean',

        # Update OpenSSL and libssl to avoid using deprecated versions of TLS (TLSv1.0 and TLSv1.1).
        # TODO: Do we actually only want to do this when deriving from an image that has an out-of-date version of TLS?
        'RUN sudo apt-get update && sudo apt-get -y install --only-upgrade openssl libssl-dev',

        'RUN echo "TERM=dumb" >> /etc/environment',

        # Otherwise: docker: Error response from daemon: unable to find user github: no matching entries in passwd file.
        'RUN useradd -ms /bin/bash github',

        # Enable passwordless sudo; see
        # https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners#administrative-privileges
        'RUN echo "ALL ALL=(ALL:ALL) NOPASSWD: ALL" >> /etc/sudoers',

        # Add the repository.
        'ADD repo-to-docker.tar /home/github/build/',
        'RUN chmod -R 777 /home/github/build' if not resettable else '',

        # Add the build script and predefined actions.
        'ADD --chown=github:github {}/run.sh /usr/local/bin/'.format(job_id),
        'ADD --chown=github:github {}/actions /home/github/{}/actions'.format(job_id, job_id),
        'ADD --chown=github:github {}/steps /home/github/{}/steps'.format(job_id, job_id),
        'ADD --chown=github:github {}/helpers /home/github/{}/helpers'.format(job_id, job_id),
        'ADD --chown=github:github {}/event.json /home/github/{}/event.json'.format(job_id, job_id),
        'RUN chmod 777 /usr/local/bin/run.sh',
        'RUN chmod -R 777 /home/github/{}'.format(job_id),

        # TODO: Do we need linuxbrew (it is huge)?
        # Let user own the entire /home directory to avoid permission issue.
        # If we are running using our job image, then don't chmod /home/linuxbrew because it is huge.
        'RUN chown -R github:github /home /home/github' if job_runner else 'RUN chown -R github:github /home',

        # TODO: Find this doc
        # Set the user to use when running the image. Our Google Drive contains a file that explains why we do this.
        'USER github',

        # Need bash, otherwise: Syntax error: redirection unexpected
        'ENTRYPOINT ["/bin/bash", "-c"]',
        # Run the build script.
        'CMD ["/usr/local/bin/run.sh"]',
    ]
    # Append a newline to each line and then concatenate all the lines.
    content = ''.join(map(lambda l: l + '\n', lines))
    with open(destination, 'w') as f:
        f.write(content)
