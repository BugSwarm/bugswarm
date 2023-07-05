import time
import os
import threading

from typing import Any
from typing import Dict
from typing import Optional

from bugswarm.common import log
from bugswarm.common.json import read_json
from bugswarm.common.json import write_json

from ...model.pull_request import PullRequest
from .step import Step


class DownloadPullRequestCommits(Step):
    def __init__(self):
        super().__init__()
        self.repo = None
        self.utils = None
        self.branches = None

    def get_commit_info_for_virtual_commit(self):
        start_time = time.time()
        virtual_commits_info = {}
        virtual_commits_info_json_file = self.utils.get_virtual_commits_info_json_file(self.repo)
        has_json_file = os.path.isfile(virtual_commits_info_json_file)
        if has_json_file:
            virtual_commits_info = read_json(virtual_commits_info_json_file)

        for _, branch_obj in self.branches.items():
            if not branch_obj.pairs:
                continue
            for pair in branch_obj.pairs:
                builds = [pair.failed_build, pair.passed_build]
                for b in builds:
                    if has_json_file:
                        if b.commit in virtual_commits_info:
                            b.virtual_commit_info = virtual_commits_info[b.commit]
                    else:
                        c = self.utils.github.get_commit_info(self.repo, b.commit)
                        if c:
                            virtual_commits_info[b.commit] = c
                            b.virtual_commit_info = c
        if not has_json_file:
            write_json(virtual_commits_info_json_file, virtual_commits_info)
        log.info('Got commit info for virtual commits in', time.time() - start_time, 'seconds.')

    def get_commits_from_github_api(self):
        start_time = time.time()
        github_commits = {}
        get_github_commits = True
        github_commits_json_file = self.utils.get_github_commits_json_file(self.repo)
        if os.path.isfile(github_commits_json_file):
            github_commits = read_json(github_commits_json_file)
            get_github_commits = False

        for _, branch_obj in self.branches.items():
            if branch_obj.pr_num != -1:  # Whether it is a PR branch.
                # Get commits from the GitHub API.
                if get_github_commits:
                    github_commits[str(branch_obj.pr_num)] = self.utils.github.list_pr_commits(self.repo,
                                                                                               str(branch_obj.pr_num))
                branch_obj.github_commits = github_commits[str(branch_obj.pr_num)]
                # for commit in github_commits[str(branch.pr_num)]:
                #     commit['build_ids'] = self.utils.github.get_build_ids_for_commit(self.repo, commit['sha'])

        write_json(github_commits_json_file, github_commits)
        log.info('Got pull request commits (via GitHub API calls) in', time.time() - start_time, 'seconds.')

    def get_pr_commits_by_parsing_html(self):
        start_time = time.time()
        html_commits_json_file = self.utils.get_html_commits_json_file(self.repo)
        html_commits = {}
        if os.path.isfile(html_commits_json_file):
            html_commits = read_json(html_commits_json_file)
            for _, branch_obj in self.branches.items():
                if branch_obj.pr_num != -1:  # if it's a PR branch
                    branch_obj.html_commits = html_commits[str(branch_obj.pr_num)]
        else:
            threads = [threading.Thread(target=self.utils.github.get_pr_commits_by_html,
                                        args=(self.repo, str(branch_obj.pr_num), branch_obj))
                       for _, branch_obj in self.branches.items()]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            for _, branch_obj in self.branches.items():
                if branch_obj.pr_num != -1:  # if it's a PR branch
                    html_commits[branch_obj.pr_num] = branch_obj.html_commits
            write_json(html_commits_json_file, html_commits)
            log.info('Got pull request commits (via HTML parsing) in', time.time() - start_time, 'seconds.')

    def process(self, data: Dict[str, PullRequest], context: dict) -> Optional[Any]:
        self.repo = context['repo']
        self.utils = context['utils']
        self.branches = data
        start_time = time.time()

        self.get_commit_info_for_virtual_commit()
        # self.get_commits_from_github_api()  # base approach
        # self.get_pr_commits_by_parsing_html()

        log.info('Got pull request commits in', time.time() - start_time, 'seconds.')
        return data
