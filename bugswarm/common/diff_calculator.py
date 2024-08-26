import os
import git
import subprocess
import shutil
import re

import charset_normalizer

from bugswarm.common import log


# Cloning repo from github to a folder
def _git_clone_to_folder(project_clone_path, user, project):
    if not os.path.exists(project_clone_path):
        os.makedirs(project_clone_path)
    log.info('cloning repo... {}'.format(project))
    git.Repo.clone_from('https://github.com/{}'.format(user+'/'+project),
                        project_clone_path, odbt=git.GitDB)
    log.info('cloning done')


# Creating passed and failed folder of the repo
def _create_pass_fail_folder(project_clone_path, project):
    passed_path = os.path.join(project_clone_path, 'passed', project)

    if not os.path.exists(passed_path):
        os.makedirs(passed_path)

    src_path = os.path.join(project_clone_path, project)
    shutil.copytree(src_path, passed_path, dirs_exist_ok=True)


# revert to passed and failed sha using git to get passed and failed version
def _git_reset_and_fetch(folder_path, commit_sha):
    try:
        repo = git.Repo(folder_path)
        origin = repo.remote('origin')
        origin.fetch(commit_sha)

        repo.git.reset('--hard', commit_sha)
        log.info('git reset to ', commit_sha)
    except git.GitCommandError as e:
        log.info('An error has occurred ', e)
        raise Exception


def _create_merge_commit(repo_path, base_sha, head_sha):
    try:
        log.info('Merging {} into {}'.format(head_sha, base_sha))
        repo = git.Repo(repo_path)
        base = repo.commit(base_sha)
        head = repo.commit(head_sha)

        # Check out base sha and merge head sha into it
        repo.head.reset(base, index=True, working_tree=True)
        repo.git.merge(head)

        return repo.head.commit.hexsha
    except git.GitCommandError as e:
        log.error('Error while merging {} into {}: {!r}'.format(head_sha, base_sha, e))
        raise


def _normalize_bytes(b: bytes):
    norm_matches = charset_normalizer.from_bytes(b)
    if not norm_matches:
        # Couldn't guess the encoding; fall back to latin1 (guaranteed to not raise an exception)
        # TODO possibly automatically treat these files as binary instead?
        first_line = b.split(b'\n')[0]
        log.warning("Couldn't guess encoding for bytes (first line {}); falling back to 'latin1'".format(first_line))
        return str(b, encoding='latin1')
    return str(norm_matches.best())


def _get_diff_list(passed_commit, failed_commit, passed_path):
    cmd = 'cd {} && git diff {} {}'.format(
        passed_path,
        failed_commit,
        passed_commit
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, check=True)

    diff_bytes_list = []
    for i, line_bytes in enumerate(result.stdout.splitlines(keepends=True)):
        if i == 0 or line_bytes.startswith(b'diff --git'):
            diff_bytes_list.append(b'')
        diff_bytes_list[-1] += line_bytes

    diff_list = [_normalize_bytes(b).splitlines() for b in diff_bytes_list]
    return diff_list


def _fill_up_patch(patch, old_file, new_file, content, added_code_size, deleted_code_size):
    patch['old_file'] = old_file
    patch['new_file'] = new_file
    patch['content'] = content
    patch['added_code_size'] = added_code_size
    patch['deleted_code_size'] = deleted_code_size
    return patch


def _should_force_binary(filename: str):
    return filename.endswith('.pdf')


def _create_patches(diff_list):
    diff_data = []
    plus_count = 0
    minus_count = 0
    for diff in diff_list:
        p = {}
        content = ''
        match = re.match(r'diff --git a/(.*) b/(.*)', diff[0])
        old_file = match.group(1)
        new_file = match.group(2)
        force_binary = _should_force_binary(old_file) or _should_force_binary(new_file)
        compare_line_index = 1

        if diff[compare_line_index].startswith('old mode'):
            compare_line_index = 3
            content += '{}\n{}\n'.format(diff[1], diff[2])

        # can happen if e.g. a file's mode was changed but its contents weren't
        if len(diff) <= compare_line_index:
            p = _fill_up_patch(p, old_file, new_file, content, 0, 0)

        # modified files
        elif diff[compare_line_index].startswith('index'):
            plus_per_file = 0
            minus_per_file = 0
            tripple_minus_or_binary_idx = compare_line_index + 1
            tripple_plus_idx = compare_line_index + 2
            content_start_idx = compare_line_index + 3

            if force_binary or diff[tripple_minus_or_binary_idx].startswith('Binary'):
                content = 'Binary file {} modified'.format(old_file)
                p = _fill_up_patch(p, old_file, new_file, content, 0, 0)
            elif diff[tripple_minus_or_binary_idx].startswith('---') and diff[tripple_plus_idx].startswith('+++'):
                content = content + diff[tripple_minus_or_binary_idx] + '\n' + diff[tripple_plus_idx] + '\n'
                for i in range(content_start_idx, len(diff)):
                    content = content + diff[i] + '\n'
                    if diff[i].startswith('+'):
                        plus_count = plus_count + 1
                        plus_per_file = plus_per_file + 1
                    elif diff[i].startswith('-'):
                        minus_count = minus_count + 1
                        minus_per_file = minus_per_file + 1
                p = _fill_up_patch(p, old_file, new_file, content, plus_per_file, minus_per_file)
            else:
                raise Exception('This diff is invalid due to {}'.format(diff[tripple_minus_or_binary_idx]))

        # added files
        elif diff[compare_line_index].startswith('new file'):
            plus_per_file = 0
            minus_per_file = 0
            p['old_file'] = '/dev/null'
            # added empty files
            if len(diff) == 3:
                content = 'Empty file.'
                p = _fill_up_patch(p, '/dev/null', new_file, content, 0, 0)
            else:
                # added files with contents
                tripple_minus_or_binary_idx = 3
                tripple_plus_idx = 4
                content_start_idx = 5

                if force_binary or diff[tripple_minus_or_binary_idx].startswith('Binary'):
                    content = 'Binary file {} added'.format(new_file)
                    p = _fill_up_patch(p, '/dev/null', new_file, content, 0, 0)
                elif diff[tripple_minus_or_binary_idx].startswith('---') and diff[tripple_plus_idx].startswith('+++'):
                    content = content + diff[tripple_minus_or_binary_idx] + '\n' + diff[tripple_plus_idx] + '\n'
                    for i in range(content_start_idx, len(diff)):
                        content = content + diff[i] + '\n'
                        if diff[i].startswith('+'):
                            plus_count = plus_count + 1
                            plus_per_file = plus_per_file + 1
                    p = _fill_up_patch(p, '/dev/null', new_file, content, plus_per_file, 0)
                else:
                    raise Exception('This diff is invalid due to {}'.format(diff[tripple_minus_or_binary_idx]))

        # deleted files
        elif diff[compare_line_index].startswith('deleted'):
            plus_per_file = 0
            minus_per_file = 0
            if len(diff) == 3:
                content = 'Empty file.'
                p = _fill_up_patch(p, old_file, '/dev/null', content, 0, 0)
            else:
                tripple_minus_or_binary_idx = 3
                tripple_plus_idx = 4
                content_start_idx = 5

                if force_binary or diff[tripple_minus_or_binary_idx].startswith('Binary'):
                    # Binary files /dev/null and b/po.zip differ
                    content = 'Binary file {} deleted'.format(old_file)
                    p = _fill_up_patch(p, old_file, '/dev/null', content, 0, 0)
                elif diff[tripple_minus_or_binary_idx].startswith('---') and diff[tripple_plus_idx].startswith('+++'):
                    # deleted files with contents
                    content = content + diff[tripple_minus_or_binary_idx] + '\n' + diff[tripple_plus_idx] + '\n'
                    for i in range(content_start_idx, len(diff)):
                        content = content + diff[i] + '\n'
                        if diff[i].startswith('-'):
                            minus_count = minus_count + 1
                            minus_per_file = minus_per_file + 1
                    p = _fill_up_patch(p, old_file, '/dev/null', content, 0, minus_per_file)
                else:
                    raise Exception('This diff is invalid due to {}'.format(diff[tripple_minus_or_binary_idx]))

        # renaming
        elif diff[compare_line_index].startswith('similarity'):
            # similarity index 100%
            plus_per_file = 0
            minus_per_file = 0
            match1 = re.match(r'similarity index (.*)%', diff[compare_line_index])
            match_percentage = int(match1.group(1))
            o = old_file
            n = new_file
            tripple_minus_or_binary_idx = compare_line_index + 4
            tripple_plus_idx = compare_line_index + 5
            content_start_idx = compare_line_index + 6

            if match_percentage == 100 or force_binary or diff[tripple_minus_or_binary_idx].startswith('Binary'):
                content = 'File renamed from {} to {}'.format(o, n)
                p = _fill_up_patch(p, old_file, new_file, content, 0, 0)
            elif diff[tripple_minus_or_binary_idx].startswith('---') and diff[tripple_plus_idx].startswith('+++'):
                content = content + diff[tripple_minus_or_binary_idx] + '\n' + diff[tripple_plus_idx] + '\n'
                for i in range(content_start_idx, len(diff)):
                    content = content + diff[i] + '\n'
                    if diff[i].startswith('+'):
                        plus_count = plus_count + 1
                        plus_per_file = plus_per_file + 1
                    elif diff[i].startswith('-'):
                        minus_count = minus_count + 1
                        minus_per_file = minus_per_file + 1
                p = _fill_up_patch(p, old_file, new_file, content, plus_per_file, minus_per_file)
            else:
                raise Exception('This diff is invalid due to {}'.format(diff[tripple_minus_or_binary_idx]))

        else:
            raise Exception('This diff is invalid due to {}'.format(diff[compare_line_index]))

        diff_data.append(p)

    return diff_data, plus_count, minus_count


def gather_diff(failed_sha, passed_sha, repo, repo_clone_path, failed_base_sha=None, passed_base_sha=None):
    """
    Computes `git diff <failed_sha>..<passed_sha>` for the given repo.

    If `failed_base_sha` or `passed_base_sha` are not None, then this function
    will merge those commits into `failed_sha` or `passed_sha` respectively
    before performing the diff. (This is meant to imitate GitHub's PR merge base
    behavior -- see https://github.com/readthedocs/readthedocs.org/issues/6958.)

    :param failed_sha: The failed commit.
    :param passed_sha: The passed commit.
    :param repo: The repo the commits are from.
    :param repo_clone_path: A path on disk to clone the repo to before
        performing the diff. If the path already exists, this function assumes
        the repo has already been cloned there.
    :param failed_base_sha: If not `None`, the commit to merge `failed_sha`
        into before diffing.
    :param passed_base_sha: If not `None`, the commit to merge `passed_sha`
        into before diffing.
    :return:  A dict in the following format::

            {
                'failed_sha': str,
                'passed_sha': str,
                'total_added_code': int,
                'total_deleted_code': int,
                'diff_size': int,
                'patches': [
                    {
                        'old_file': str,
                        'new_file': str,
                        'added_code_size': int,
                        'deleted_code_size': int,
                        'content': str,
                    },
                    ...
                ]
            }
    """
    user, project = repo.split('/')

    if not os.path.exists(repo_clone_path):
        _git_clone_to_folder(repo_clone_path, user, project)

    _git_reset_and_fetch(repo_clone_path, passed_sha)
    _git_reset_and_fetch(repo_clone_path, failed_sha)
    if failed_base_sha:
        _git_reset_and_fetch(repo_clone_path, failed_base_sha)
        failed_sha = _create_merge_commit(repo_clone_path, failed_base_sha, failed_sha)
    if passed_base_sha:
        _git_reset_and_fetch(repo_clone_path, passed_base_sha)
        passed_sha = _create_merge_commit(repo_clone_path, passed_base_sha, passed_sha)

    diffs = _get_diff_list(passed_sha, failed_sha, repo_clone_path)

    patches, plus, minus = _create_patches(diffs)

    return {
        'failed_sha': failed_sha,
        'passed_sha': passed_sha,
        'total_added_code': plus,
        'total_deleted_code': minus,
        'diff_size': plus + minus,
        'patches': patches,
    }


def gather_diff_info(failed_sha, passed_sha, repo, repo_clone_path, failed_base_sha=None, passed_base_sha=None):
    user = repo.split('/')[0]
    project = repo.split('/')[1]
    if not os.path.exists(repo_clone_path):
        _git_clone_to_folder(repo_clone_path, user, project)

    info = {}
    try:
        _git_reset_and_fetch(repo_clone_path, passed_sha)
        _git_reset_and_fetch(repo_clone_path, failed_sha)
        if failed_base_sha:
            _git_reset_and_fetch(repo_clone_path, failed_base_sha)
            failed_sha = _create_merge_commit(repo_clone_path, failed_base_sha, failed_sha)
        if passed_base_sha:
            _git_reset_and_fetch(repo_clone_path, passed_base_sha)
            passed_sha = _create_merge_commit(repo_clone_path, passed_base_sha, passed_sha)

        diffs = _get_diff_list(passed_sha, failed_sha, repo_clone_path)
        diff_, plus, minus = _create_patches(diffs)
        changed_files = []
        for d in diff_:
            changed_files.append(d['new_file'])
        diff_size = plus + minus
        info['metrics'] = {
            'num_of_changed_files': len(changed_files),
            'changes': diff_size,
            'additions': plus,
            'deletions': minus
        }
        info['changed_paths'] = changed_files
        info['error_found'] = 'NONE'
    except Exception as e:
        info['num_of_changed_files'] = -1
        info['changed_paths'] = ['ERROR, CANNOT FULFILL REQUEST']
        info['error_found'] = 'ERROR, {}'.format(e)
        info['metrics'] = {
            'num_of_changed_files': 0,
            'changes': 0,
            'additions': 0,
            'deletions': 0
        }
        log.logging.exception('Could not gather info of {} {}..{} due to an error:'.format(repo, failed_sha,
                                                                                           passed_sha))
    return info
