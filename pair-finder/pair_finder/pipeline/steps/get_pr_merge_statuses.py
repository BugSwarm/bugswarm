import os
import time
from typing import Any
from typing import Dict
from typing import Optional

from bugswarm.common import log
from bugswarm.common.json import read_json
from bugswarm.common.json import write_json
from .step import Step
from .step import StepException
from ...model.branch import Branch


class GetPullRequestMergeStatuses(Step):
    def process(self, data: Dict[str, Branch], context: dict) -> Optional[Any]:
        repo = context['repo']
        utils = context['utils']

        branches = data

        # Get the merge state of each pull request.
        log.info('Getting merge state for all pull requests.')

        start_time = time.time()
        pr_list_json_file = utils.get_pr_list_json_file(repo)
        pr_dict = {}
        if os.path.isfile(pr_list_json_file):
            try:
                pr_dict = read_json(pr_list_json_file)
            except ValueError:
                os.remove(pr_list_json_file)
                raise StepException
        else:
            pr_entities = utils.github.list_pull_requests(repo)
            for pr_entity in pr_entities:
                pr_dict[str(pr_entity['number'])] = pr_entity
            write_json(pr_list_json_file, pr_dict)

        for branch_id, branch_obj in branches.items():
            if branch_obj.pr_num != -1:  # Whether the branch is a pull request branch.
                if str(branch_obj.pr_num) in pr_dict:
                    branch_obj.merged_at = pr_dict[str(branch_obj.pr_num)]['merged_at']
                    branch_obj.base_branch = pr_dict[str(branch_obj.pr_num)]['base']['ref']
                    branch_obj.pr_info = pr_dict[str(branch_obj.pr_num)]

        log.debug('Got merge state for all pull requests in', time.time() - start_time, 'seconds.')
        return branches
