import json
import os
import subprocess

from builtins import FileNotFoundError
from typing import List
from typing import Optional

from bugswarm.common import log
from bugswarm.common.json import read_json

from .constants import FILTERED_REASON_KEY
from .constants import ORIGINAL_LOG_DIR


def create_dirs():
    """
    Create needed directories if they do not already exist.
    """
    os.makedirs(ORIGINAL_LOG_DIR, exist_ok=True)


def load_buildpairs(dir_of_jsons: str, repo: str):
    """
    :param dir_of_jsons: A directory containing JSON files of build pairs.
    :param repo: repo_slug name
    :raises json.decoder.JSONDecodeError: When the passed directory contains JSON files with invalid JSON.
    """
    all_buildpairs = []
    count = 0
    task_name = repo.replace('/', '-')
    filename = task_name + '.json'
    try:
        data = read_json(os.path.join(dir_of_jsons, filename))
    except json.decoder.JSONDecodeError:
        log.error('{} contains invalid JSON.'.format(filename))
        return None
    except FileNotFoundError:
        log.error('{} is not found.'.format(filename))
        return None

    all_buildpairs.extend(data)
    if not data:
        log.warning('{} does not contain any build pairs.'.format(filename))
    count += 1
    log.info('Read {} build pairs from {}.'.format(len(all_buildpairs), filename))
    return all_buildpairs


def jobpair_is_filtered(jp):
    """
    Whether the passed job pair has an associated filter reason.
    This function should be used to decide whether to skip a jobpair that has already been filtered.
    Relies on the fact that the default value assocaited with FILTERED_REASON_KEY is None.

    :param jp: The job pair to check.
    :return: True if the job pair has an associated filter reason.
    """
    return bool(jp[FILTERED_REASON_KEY])


def count_jobpairs(buildpairs: List) -> int:
    """
    :param buildpairs: A list of build pairs.
    :return: The number of job pairs in `buildpairs`.
    """
    counts = [len(bp['jobpairs']) for bp in buildpairs]
    return sum(counts)


def count_unfiltered_jobpairs(buildpairs: List) -> int:
    """
    :param buildpairs: A list of build pairs.
    :return: The number of job pairs in `buildpairs` that are unfiltered.
    """
    counts = [len([jp for jp in bp['jobpairs'] if not jobpair_is_filtered(jp)]) for bp in buildpairs]
    return sum(counts)


def get_image_provision_timestamp(log_path: str) -> Optional[str]:
    """
    Examines the Travis build log file at `log_path` to determine when the image used by the build was provisioned.
    :param log_path: The path to the Travis build log. This should be an original build log.
    :return: The image provision timestamp. None if the timestamp cannot be found.
    """
    with open(log_path) as f:
        for line in f:
            if 'Build image provisioning date and time' in line:
                # The next line is the timestamp.
                try:
                    return next(f).strip()
                except StopIteration:
                    return None


def get_orig_log_path(job_id) -> str:
    """
    Get the path of the original log for the job identified by the passed job ID.
    """
    return os.path.join(ORIGINAL_LOG_DIR, '{}-orig.log'.format(job_id))


def log_filter_count(filtered_count: int, reason: str):
    """
    Convenience function to print the number of filtered job pairs.
    """
    log.info('Filtered {:>4} {}.'.format(filtered_count, reason))


def canonical_repo(repo: str) -> str:
    return repo.replace('/', '-')


def _registry_tags_list(repo_name):
    list_of_tags = []
    _, basic_auth, _, _ = _basic_auth()
    if not basic_auth:
        return ''
    rel_repository = repo_name
    command = 'curl -s -H "Authorization: Basic {}" -H \'Accept: application/json\' ' \
              '"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{}:pull" | json ' \
              '.token'.format(basic_auth, rel_repository)
    _, token, stderr, ok = _run_command(command)
    if not ok:
        print('Error: _registry_tags_list', token, stderr)
        return ''

    command = 'curl -s -H "Authorization: Bearer {}" ' \
              '-H "Accept: application/json" "https://index.docker.io/v2/{}/tags/list" | json .tags | json -a' \
        .format(token, rel_repository)
    _, stdout, stderr, ok = _run_command(command)
    list_of_tags = stdout.split('\n')
    if not ok:
        print('Error...', stdout, stderr)
        return ''

    return list_of_tags


def _basic_auth():
    command = 'cat ~/.docker/config.json | json ".auths[\'https://index.docker.io/v1/\'].auth"'
    _, stdout, stderr, ok = _run_command(command)
    if not ok:
        print('Error', stdout, stderr)
        return _, None, None, _
    return _, stdout, stderr, ok


def _run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    return process, stdout, stderr, ok
