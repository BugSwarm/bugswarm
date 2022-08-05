import datetime
import json
import os
import shutil
import subprocess

from collections import OrderedDict
from typing import Dict
from typing import Optional
from typing import Tuple

from bugswarm.common import log
from bugswarm.common.json import read_json
from bugswarm.common.json import write_json
from bugswarm.common.shell_wrapper import ShellWrapper
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.rest_api.database_api import DatabaseAPI

from .github import GitHub
from .travis import Travis

# Please update .gitignore to reflect any changes to these constants.
CLONE_DIR = 'intermediates/clones'
HISTORY_DIR = 'intermediates/histories'
LOG_DIR = 'intermediates/logs'
OUTPUT_DIR = 'output'
ORIGNAL_METRICS_DIR = 'output/original_metrics'
API_RESULT_DIR = 'intermediates/api-results'
BUGSWARMAPI = DatabaseAPI(DATABASE_PIPELINE_TOKEN)


class Utils(object):
    def __init__(self):
        self.github = GitHub()
        self.travis = Travis()

    @staticmethod
    def create_dirs(task_name):
        # Create needed directories if they do not already exist.
        os.makedirs(CLONE_DIR, exist_ok=True)
        os.makedirs(HISTORY_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(API_RESULT_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(ORIGNAL_METRICS_DIR, exist_ok=True)
        task_dir = os.path.join(OUTPUT_DIR, task_name)
        os.makedirs(task_dir, exist_ok=True)

    @staticmethod
    def write_empty_json(repo, task_name):
        write_json(Utils.output_file_path_from_repo(repo, task_name), [])

    @staticmethod
    def get_github_commits_json_file(repo):
        return os.path.join(API_RESULT_DIR, Utils._canonical_repo(repo) + '_github.json')

    @staticmethod
    def get_repo_builds_api_result_file(repo):
        return os.path.join(API_RESULT_DIR, Utils._canonical_repo(repo) + '_builds.json')

    @staticmethod
    def get_repo_builds_info_api_result_file(repo):
        return os.path.join(API_RESULT_DIR, Utils._canonical_repo(repo) + '_builds_info.json')

    @staticmethod
    def get_virtual_commits_info_json_file(repo):
        return os.path.join(API_RESULT_DIR, Utils._canonical_repo(repo) + '_virtual.json')

    @staticmethod
    def get_html_commits_json_file(repo):
        return os.path.join(API_RESULT_DIR, Utils._canonical_repo(repo) + '_html.json')

    @staticmethod
    def get_pr_list_json_file(repo):
        return os.path.join(API_RESULT_DIR, Utils._canonical_repo(repo) + '_pr.json')

    # True if the repo appears to be private or deleted.
    def repo_is_private_or_removed(self, repo) -> bool:
        repo_info = self.github.get_repo_info(repo)
        return not repo_info or repo_info.get('private') is True

    # Returns True if the clone succeeded.
    @staticmethod
    def clone_repo(repo: str) -> bool:
        # We use the git clone exit code to determine if the clone succeeded. But we need to distinguish between fatal
        # errors (repository not found) and circumstances that prevent cloning (clone destination directory already
        # exists and is not empty). But git returns the same exit code for both errors and unexpected events. So, in
        # order to make the distinction, we manually check for cases like the preexistence of the clone destination.
        repo_path = Utils._canonical_repo_path(repo)
        if os.path.isdir(repo_path) and os.listdir(repo_path):
            # The clone destination directory already exists, so we can return early and indicate to the caller that the
            # clone succeeded.
            log.info('Clone of', repo, 'seems to already exist.')
            return True

        clone_command = 'git clone https://github.com/{}.git {} > /dev/null 2>&1'.format(repo, repo_path)
        log.info('Cloning', repo, 'into', repo_path)
        _, _, returncode = ShellWrapper.run_commands(clone_command, stdout=subprocess.PIPE, shell=True)
        return returncode == 0

    @staticmethod
    def get_git_log_path(repo: str) -> str:
        return os.path.join(Utils._canonical_repo_path(repo), 'git_log.txt')

    @staticmethod
    def store_git_log(repo: str) -> bool:
        repo_path = Utils._canonical_repo_path(repo)
        if os.path.isfile(Utils.get_git_log_path(repo)):
            log.info('git log of', repo, 'already exists.')
            return True
        command_1 = 'cd {}'.format(repo_path)
        command_2 = 'git fetch origin refs/pull/*/head:refs/remotes/origin/pr/* > /dev/null 2>&1'
        command_3 = 'TZ=UTC git log --branches --remotes --pretty=format:"%H %cd" --date="format-local:' \
                    '%Y-%m-%dT%H:%M:%SZ" >> git_log.txt'
        log.info('Processing git log', repo, 'into', repo_path)
        _, _, returncode = ShellWrapper.run_commands(command_1, command_2, command_3,
                                                     stdout=subprocess.PIPE, shell=True)
        return returncode == 0

    @staticmethod
    def read_sha_from_git_log(repo: str) -> Dict:
        shas = {}
        with open(Utils.get_git_log_path(repo)) as f:
            for l in f:
                split_line = l.strip().split()
                if len(split_line) == 1:
                    # The git log is displaying a commit with timestamp set to the start of Unix epoch time. For commits
                    # with this timestamp, the git log prints the SHA but keeps the timestamp column blank. So manually
                    # set the timestamp to the start of Unix epoch time.
                    sha = split_line[0]
                    timestamp = '1970-01-01T00:00:00Z'
                else:
                    sha, timestamp = split_line
                shas[sha] = Utils.convert_api_date_to_datetime(timestamp)
        return OrderedDict(sorted(shas.items(), key=lambda t: t[1], reverse=True))

    @staticmethod
    def get_pr_commit_base(repo: str, commit: str, base_branch: str, trigger_commit_timestamp: str) -> Optional[str]:
        # Change into the repo directory and then find the latest commit before the commit date.
        repo_path = Utils._canonical_repo_path(repo)
        cd_command = 'cd {}'.format(repo_path)
        # # Super hack.
        # commit_date = self.github.get_commit_date(repo, commit)
        # if commit_date is None:
        #     return None
        # git_command = 'git rev-list -n 1 --skip 1 --before="{}" --branches="{}"'.format(trigger_commit_timestamp,
        #                                                                                 base_branch)
        git_command = 'git rev-list -n 1 --skip 1 --before="{}" {}'.format(trigger_commit_timestamp, base_branch)
        result, _, _ = ShellWrapper.run_commands(cd_command, git_command, stdout=subprocess.PIPE, shell=True)
        return result

    @staticmethod
    def get_parents_of_commit(repo: str, commit: str, base_branch: str) -> Optional[str]:
        repo_path = Utils._canonical_repo_path(repo)
        cd_command = 'cd {}'.format(repo_path)
        git_command = 'git rev-list {}..master --first-parent --reverse'.format(commit)
        result, _, _ = ShellWrapper.run_commands(cd_command, git_command, stdout=subprocess.PIPE, shell=True)
        return result

    @staticmethod
    def get_branch_of_sha(repo: str, commit: str) -> Optional[str]:
        # Change into the repo directory and then find the latest commit before the commit date.
        repo_path = Utils._canonical_repo_path(repo)
        cd_command = 'cd {}'.format(repo_path)
        git_command = 'git branch --contains {}'.format(commit)
        result, _, _ = ShellWrapper.run_commands(cd_command, git_command, stdout=subprocess.PIPE, shell=True)
        return result

    @staticmethod
    def clean_bad_json_files(task_name):
        log.info('Cleaning bad JSON files.')
        count = 0
        task_dir = os.path.join(OUTPUT_DIR, task_name)
        for file in os.listdir(task_dir):
            if '.json' in file:
                filepath = os.path.join(task_dir, file)
                try:
                    read_json(filepath)
                except (json.decoder.JSONDecodeError, UnicodeDecodeError):
                    os.remove(filepath)
                    log.info('Removing', filepath)
                    count += 1
        log.info('Removed', count, 'bad JSON files.')

    @staticmethod
    def remove_repo_clone(repo: str):
        repo_path = Utils._canonical_repo_path(repo)
        log.info('Removing clone of', repo)
        shutil.rmtree(repo_path)

    @staticmethod
    def output_file_path_from_repo(repo: str, task_name: str) -> str:
        filename = Utils._canonical_repo(repo) + '.json'
        task_dir = os.path.join(OUTPUT_DIR, task_name)
        return os.path.join(task_dir, filename)

    @staticmethod
    def output_metrics_path_from_repo(repo: str, task_name: str) -> str:
        filename = Utils._canonical_repo(repo) + '.json'
        return os.path.join(ORIGNAL_METRICS_DIR, filename)

    @staticmethod
    def log_file_path_from_repo(repo: str) -> str:
        filename = Utils._canonical_repo(repo) + '.log'
        return os.path.join(LOG_DIR, filename)

    @staticmethod
    def convert_api_date_to_datetime(date_str: str) -> datetime:
        return datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')

    @staticmethod
    def get_latest_commit_for_repo(repo: str) -> str:
        repo_path = Utils._canonical_repo_path(repo)
        cd_command = 'cd {}'.format(repo_path)
        git_command = 'git rev-parse HEAD'
        result, _, _ = ShellWrapper.run_commands(cd_command, git_command, stdout=subprocess.PIPE, shell=True)
        return result

    @staticmethod
    def count_mined_pairs_in_branches(branches: Optional[Dict]) -> Tuple[int, int, int, int]:
        if not branches:
            return 0, 0, 0, 0

        mined_build_pairs = 0
        mined_job_pairs = 0
        mined_pr_build_pairs = 0
        mined_pr_job_pairs = 0
        for _, branch_obj in branches.items():
            for p in branch_obj.pairs:
                # Exclude pairs that were marked in clean_pairs.py.
                if p.exclude_from_output:
                    continue
                if branch_obj.pr_num == -1:
                    mined_build_pairs += 1
                    mined_job_pairs += len(p.jobpairs)
                else:
                    mined_pr_build_pairs += 1
                    mined_pr_job_pairs += len(p.jobpairs)
        return mined_build_pairs, mined_job_pairs, mined_pr_build_pairs, mined_pr_job_pairs

    @staticmethod
    def canonical_task_name_from_repo(repo: str):
        return repo.replace('/', '-')

    @staticmethod
    def is_repo_previously_mined(repo: str):
        current_mining_repo = repo.lower()
        projects = BUGSWARMAPI.list_mined_projects()
        for project in projects:
            if current_mining_repo == project['repo'].lower() and (
                    'ci_service' not in project or project['ci_service'] == 'travis'):
                return repo != project['repo'], project['repo']
        return False, None

    # ---------- Private Utils ----------

    @staticmethod
    def _canonical_repo_path(repo: str) -> str:
        return os.path.join(CLONE_DIR, Utils._canonical_repo(repo))

    @staticmethod
    def _canonical_repo(repo: str) -> str:
        return repo.replace('/', '-')
