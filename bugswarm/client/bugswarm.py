import json
import logging
import os

import click

from bugswarm.common import log
from bugswarm.common.rest_api.database_api import DatabaseAPI

from . import docker
from .command import MyCommand


@click.group()
@click.version_option(message='The BugSwarm Client, version %(version)s')
def cli():
    """A command line interface for the BugSwarm dataset."""
    # Configure logging.
    log.config_logging(getattr(logging, 'INFO', None))


@cli.command(cls=MyCommand)
@click.option('--image-tag', required=True,
              type=str,
              help='The artifact image tag.')
@click.option('--use-sandbox/--no-use-sandbox', default=False,
              help='Whether to set up a directory that is shared by the host and container.')
@click.option('--pipe-stdin/--no-pipe-stdin', default=False,
              help='If enabled, the contents of stdin are executed inside the container. '
                   'This option supports heredocs in shells that support them. '
                   'Disabled by default.')
@click.option('--rm/--no-rm', default=True,
              help='If enabled, artifact containers will be cleaned up automatically after use. '
                   'Disable this behavior if you want to inspect the container filesystem after use. '
                   'Enabled by default.')
def run(image_tag, use_sandbox, pipe_stdin, rm):
    """Start an artifact container."""
    # If the script does not already have sudo privileges, then explain to the user why the password prompt will appear.
    if os.getuid() != 0:
        log.info('Docker requires sudo privileges.')
    docker.docker_run(image_tag, use_sandbox, pipe_stdin, rm)


@cli.command(cls=MyCommand)
@click.option('--image-tag', required=True,
              type=str,
              help='The artifact image tag.')
@click.option('--token', required=False,
              type=str,
              help='An optional authentication token for the BugSwarm database. '
                   'Please visit www.bugswarm.org/contact/ to request a token.')
def show(image_tag, token):
    """Display artifact metadata."""
    token = token or ''
    bugswarmapi = DatabaseAPI(token=token)
    response = bugswarmapi.find_artifact(image_tag, error_if_not_found=False)
    if not response.ok:
        log.info('No artifact metadata found for image tag {}.'.format(image_tag))
    else:
        artifact = response.json()
        # Print without the INFO prefix so the output is easier to parse.
        print(json.dumps(artifact, sort_keys=True, indent=4))
