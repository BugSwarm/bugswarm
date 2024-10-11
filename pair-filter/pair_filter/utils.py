import json
import os
import re
import subprocess
from builtins import FileNotFoundError
from typing import List, Optional

from bugswarm.common import log
from bugswarm.common.credentials import GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper
from bugswarm.common.json import read_json

from .constants import FILTERED_REASON_KEY, ORIGINAL_LOG_DIR


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


def get_matrix_param(param: str, config: dict):
    def dict_key_to_lower(d):
        return dict((k.lower(), dict_key_to_lower(v)) for k, v in d.items()) if isinstance(d, dict) else d

    param = param.lower()
    config = dict_key_to_lower(config)  # Convert all keys to lowercase first.

    try:
        result = config['strategy']['matrix']
    except KeyError:
        return ''

    for key in param.split('.'):
        result = result[key] if isinstance(result, dict) and key in result else ''
    return result


def build_uses_submodules(repo: str, build: dict) -> bool:
    """
    If a build has the `has_submodules` key, returns that. Otherwise, queries the GitHub API.

    :returns: Whether the given build uses submodules.
    :raises: `RuntimeError` if there was an error querying the API.
    """
    try:
        return build['has_submodules']
    except KeyError:
        log.error('Build does not have "has_submodules" key. Fetching info from GitHub API.')

    gh = GitHubWrapper(GITHUB_TOKENS)

    # Get commit object
    head_sha = build['head_sha']
    commit_url = 'https://api.github.com/repos/{}/commits/{}'.format(repo, head_sha)
    _, commit = gh.get(commit_url)
    if commit is None:
        # Using RuntimeError because defining a new exception class is overkill.
        raise RuntimeError('Could not get a commit object from the URL "{}".'.format(commit_url))

    # Get root tree of repo
    tree_url = commit['commit']['tree_url']
    _, tree = gh.get(tree_url)
    if tree is None:
        raise RuntimeError('Could not get a tree object from the URL "{}".'.format(tree_url))

    # Look for a .gitmodules file in the repo root
    for item in tree['tree']:
        if item['type'] == 'blob' and item['path'] == '.gitmodules':
            return True
    return False


def find_cleartext_tokens(target_dict: dict, redact=False):
    """
    Given a dict taken from a job's config, return all keys that (a)
    seem to be tokens/passwords, and (b) do not use the secrets context
    (i.e., have the token stored in clear text).

    :param target_dict: The dict to examine.
    :param redact: If `True`, replace all cleartext tokens with the
        string "**REDACTED**".
    :returns: The list of keys that have cleartext tokens.
    """
    if not isinstance(target_dict, dict):
        return []

    # Matches anything in ${{ }}, as long as it has "secrets.*" in it
    secrets_re = re.compile(r'\${{[^}]*(secrets\.\w+|github\.token|env\.GITHUB_TOKEN)[^}]*}}', flags=re.I)
    # Suspicious token names
    token_re = re.compile(r'token|password|passwd?', flags=re.I)
    # Test for empty tokens or dummy tokens a la "testDBPassword", "dummy_token", etc
    false_positive_re = re.compile(r'token|password|dummy|^\s*$', flags=re.I)
    matched_keys = []
    for varname, value in target_dict.items():
        # Coerce the value to a string using GHA's rules
        # Doesn't correctly handle dict or list, but afaik GHA doesn't allow those types in envs or inputs.
        if value is None:
            value = ''
        elif isinstance(value, bool):
            value = str(value).lower()
        else:
            value = str(value)

        # Search the entire token string for a secret. It's fine if part of the value is exposed, as long as there's
        # some part that's hidden.
        if token_re.search(varname) and not secrets_re.search(value) and not false_positive_re.search(value):
            log.debug('Key', varname, 'seems to contain a cleartext token!')
            matched_keys.append(varname)

    if redact:
        for key in matched_keys:
            target_dict[key] = '**REDACTED**'

    return matched_keys


def get_github_actions_pr_data(job_id):
    path = get_orig_log_path(job_id)
    with open(path) as f:
        # Remove timestamp from the start of each line
        log_lines = [line[29:] for line in f.read().splitlines()]

    flag = False
    pr_num = base_sha = head_sha = merge_sha = None

    for lineno, line in enumerate(log_lines):
        if line == '##[group]Checking out the ref':
            flag = True
            continue
        if not flag:
            continue
        if line.startswith('##[group] Run'):
            # actions/checkout has finished
            break

        if m := re.match(r"Note: switching to 'refs/remotes/pull/(\d+)/merge'", line):
            pr_num = int(m.group(1))
        elif m := re.match(r'HEAD is now at \S+ Merge (\S+) into (\S+)', line):
            head_sha = m.group(1)
            base_sha = m.group(2)
        elif pr_num is not None and line == "[command]/usr/bin/git log -1 --format='%H'":
            merge_sha = log_lines[lineno + 1][1:-1]
            break
        elif pr_num is not None and line == '[command]/usr/bin/git log -1 --format=%H':
            merge_sha = log_lines[lineno + 1]
            break

    result = (pr_num, base_sha, head_sha, merge_sha)

    # Sanity check: either no elements in `result` are None (PR job), or all are None (push job)
    if any(result) and not all(result):
        raise RuntimeError(
            'Job {}: GHA PR data is invalid: (PR, base SHA, head SHA, merge SHA) == {}'.format(job_id, result))

    # Check that the SHAs are all actual SHAs
    if pr_num:
        sha_regex = r'[0-9a-f]{40}$'
        if not re.match(sha_regex, base_sha):
            raise RuntimeError('Job {}: base SHA is invalid: {!r}'.format(job_id, base_sha))
        if not re.match(sha_regex, head_sha):
            raise RuntimeError('Job {}: head SHA is invalid: {!r}'.format(job_id, head_sha))
        if not re.match(sha_regex, merge_sha):
            raise RuntimeError('Job {}: merge SHA is invalid: {!r}'.format(job_id, merge_sha))

    return pr_num, base_sha, head_sha, merge_sha


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
