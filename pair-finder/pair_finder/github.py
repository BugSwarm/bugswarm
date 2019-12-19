import re

from typing import Dict
from typing import List
from typing import Optional

import requests

from bugswarm.common import log
from bugswarm.common import github_wrapper
from bugswarm.common import credentials


class GitHub(object):
    def __init__(self):
        # Tokens for token switching to minimize the time spent waiting for our GitHub quota to reset.
        self.github_wrapper = github_wrapper.GitHubWrapper(credentials.GITHUB_TOKENS)

    def get_repo_info(self, repo):
        _, result = self.github_wrapper.get('https://api.github.com/repos/{}'.format(repo))
        return result

    def get_commit_info(self, repo, commit):
        _, result = self.github_wrapper.get('https://api.github.com/repos/{}/commits/{}'.format(repo, commit))
        return result

    def get_pr_info(self, repo, pr_num):
        _, result = self.github_wrapper.get('https://api.github.com/repos/{}/pulls/{}'.format(repo, pr_num))
        return result

    @staticmethod
    def get_pr_commits_by_html(repo, pr_num, branch):
        url = 'https://github.com/{}/pull/{}/commits'.format(repo, pr_num)
        r = requests.get(url)
        commits = {}
        build_id_list = []
        if r.status_code == 200:
            for l in r.text.split('\n'):
                if repo + '/builds/' in l and 'travis' in l:
                    build_id = re.findall(r'/builds/(\d+)', l)[-1]  # l.split('/builds/')[1].split('?')[0]
                    build_id_list.append(build_id)
                elif 'class="sha btn' in l:
                    sha = l.split('/commits/')[1].split('"')[0]
                    commits[sha] = build_id_list
                    build_id_list = []
        branch.html_commits = commits
        # return commits

    def get_commit_travis_status_info(self, repo, commit) -> Optional[List]:
        """
        Returns the status object for a travis build associated with a commit.
        Returns None if that does not exist for `commit`.
        """
        _, result = self.github_wrapper.get('https://api.github.com/repos/{}/commits/{}/status'.format(repo, commit))
        if result is None:
            return None
        statuses = result.get('statuses')
        if not statuses:
            log.debug('GitHub returned no statuses for commit', commit)
            return None
        travis_status = [x for x in statuses if self.is_commit_travis_status(x)]
        return travis_status

    def list_pr_commits(self, repo, pr_num) -> List[str]:
        _, result = self.github_wrapper.get('https://api.github.com/repos/{}/pulls/{}/commits'.format(repo, pr_num))
        if result is None:
            return []
        # commits = list(map(lambda x: x['sha'], result))
        # log.info('Found', len(github_pr_commits), 'commits for PR #', branch.pr_num, 'on GitHub')
        return result

    def list_pull_requests(self, repo):
        return self.github_wrapper.get_all_pages(
            'https://api.github.com/repos/{}/pulls?state=all&per_page=100'.format(repo))

    # ---------- GitHub Wrapper Utils ----------

    def is_commit_associated_with_build(self, repo, commit, build_id: int) -> bool:
        commit_build_ids = self.get_build_ids_for_commit(repo, commit)
        for commit_build_id in commit_build_ids:
            if commit_build_id == str(build_id):
                return True
        return False

    @staticmethod
    def is_commit_travis_status(status: Dict) -> bool:
        if 'target_url' in status and status['target_url']:
            return 'travis-ci' in status['target_url']

    def get_commit_date(self, repo, commit) -> Optional[str]:
        result = self.get_commit_info(repo, commit)
        if result is not None:
            return result['commit']['committer']['date']
        return None

    def get_date_for_pr_commit(self, repo, pr_num, commit) -> Optional[str]:
        for pr_commit in self.list_pr_commits(repo, pr_num):
            if pr_commit.startswith(commit):
                return self.get_commit_date(repo, pr_commit)
        return None

    def get_build_ids_for_commit(self, repo, commit) -> List[str]:
        """
        Returns the internal build ID for the build associated with `commit`. None if `commit` did not trigger a build.
        """
        # Get the commit's status.
        statuses = self.get_commit_travis_status_info(repo, commit)
        if not statuses:
            return []
        # Extract the internal build ID.
        build_id_list = [re.findall(r'/(\d+)', s['target_url'])[-1] for s in statuses]
        return build_id_list

    def is_pr_merged(self, repo, pr_num) -> bool:
        pull_requests = self.list_pull_requests(repo)
        pr = next((x for x in pull_requests if x['number'] == pr_num), None)
        if pr is None:
            return False
        return pr['merged_at'] is not None

    # Returns the name of the branch containing the changes for the pull request.
    def get_head_branch_for_pr(self, repo, pr_num) -> Optional[str]:
        pr_info = self.get_pr_info(repo, pr_num)
        if pr_info is None or 'head' not in pr_info or 'label' not in pr_info['head']:
            return None
        # The head branch can be None if the head fork is unknown.
        # See https://api.github.com/repos/gwtbootstrap3/gwtbootstrap3/pulls/370 for an example.
        # In this case we return None and let the caller handle it.
        return pr_info['head']['ref']
