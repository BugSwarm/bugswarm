"""
Generates a Dockerfile for the job we want to reproduce, so we can spawn a container of the image built from that
Dockerfile and then run the job.
"""
from bugswarm.common import log
from reproducer.model.job import Job
from reproducer.pipeline.github.job_image_utils import JobImageUtils
from reproducer.reproduce_exception import ReproduceError


def gen_dockerfile(job: Job, destination: str = None):
    """
    Generates a Dockerfile for reproducing a job.

    This only requires that we know which Travis base image from which to derive the generated Dockerfile.

    :param job: Job object
    :param destination: Path where the generated Dockerfile should be written.
    """
    if not isinstance(job.image_tag, str) or not isinstance(job.runs_on, str):
        raise ReproduceError('Job object is missing image_tag or runs_on.')

    log.info('Use Docker image {} for job runner.'.format(job.image_tag))

    destination = destination or job.job_id + '-Dockerfile'
    _write_dockerfile(destination, job)
    log.debug('Wrote Dockerfile to {}'.format(destination))


def _write_dockerfile(destination: str, job: Job):
    job_id = job.job_id
    bugswarm_job_runner = job.container is None

    # TODO: CentOS, RHEL base image
    lines = [
        'FROM {}'.format(job.image_tag),
    ]

    if not bugswarm_job_runner:
        # If we are running in container image, then we need to install the following tools:
        # cat (for build script), node (for custom actions), python3 (for expression handling)
        bugswarm_base_image = JobImageUtils.get_bugswarm_image_tag(job.runs_on, use_default=False)
        if bugswarm_base_image:
            # GitHub Actions will start container using -v "/opt/hostedtoolcache":"/__t"
            # If we found the original runs-on, we need to copy the /opt/hostedtoolcache from our job_runner image
            # to the new job runner container.
            lines.append('COPY --from={} /opt/hostedtoolcache /opt/hostedtoolcache'.format(bugswarm_base_image))

        lines += [
            'RUN apt-get update && apt-get -y install sudo curl coreutils python3 vim',
            'RUN apt-get install -y python-is-python3 || sudo ln -s /usr/bin/python3 /usr/bin/python',
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
        'RUN sudo apt-get update && sudo apt-get -y install --only-upgrade openssl libssl-dev vim',

        'RUN echo "TERM=dumb" >> /etc/environment',
        # Hooks can set environment variable using /etc/reproducer-environment
        'RUN touch /etc/reproducer-environment && chmod 777 /etc/reproducer-environment',

        # Otherwise: docker: Error response from daemon: unable to find user github: no matching entries in passwd file.
        'RUN useradd -ms /bin/bash github',

        # Enable passwordless sudo; see
        # https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners#administrative-privileges
        'RUN echo "ALL ALL=(ALL:ALL) NOPASSWD: ALL" >> /etc/sudoers',

        # Add the repository.
        'ADD repo-to-docker.tar /home/github/build/',

        # Add the build script and predefined actions.
        'ADD --chown=github:github {}/run.sh /usr/local/bin/'.format(job_id),
        'ADD --chown=github:github {}/actions /home/github/{}/actions'.format(job_id, job_id),
        'ADD --chown=github:github {}/steps /home/github/{}/steps'.format(job_id, job_id),
        'ADD --chown=github:github {}/helpers /home/github/{}/helpers'.format(job_id, job_id),
        'ADD --chown=github:github {}/event.json /home/github/{}/event.json'.format(job_id, job_id),
        'RUN chmod 777 /usr/local/bin/run.sh',
        'RUN chmod -R 777 /home/github/{}'.format(job_id),

        # Let user own the entire /home directory to avoid permission issue.
        # If we are running using our job image, then don't chmod /home/linuxbrew because it is huge.
        # Need to manually remove linuxbrew for now. Next time we update our base images we should remove it directly.
        'RUN rm -rf /home/linuxbrew && chown -R github:github /home',

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
