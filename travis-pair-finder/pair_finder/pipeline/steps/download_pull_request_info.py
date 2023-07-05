from typing import Any
from typing import Dict
from typing import Optional

from bugswarm.common import log

from ...model.pull_request import PullRequest
from .step import Step


class DownloadPullRequestInfo(Step):
    def process(self, data: Dict[str, PullRequest], context: dict) -> Optional[Any]:
        repo = context['repo']
        utils = context['utils']

        log.info('Downloading pull request info.')

        pull_requests = data

        for pr_num, pr in pull_requests.items():
            pr_info = utils.github.get_pr_info(repo, pr_num)
            if pr_info is None:
                continue
            num_commits = pr_info['commits']
            pr.num_commits = num_commits

        return data
