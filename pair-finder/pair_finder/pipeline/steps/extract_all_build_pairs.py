from typing import Any
from typing import Dict
from typing import List

from bugswarm.common import log

from ...model.fail_pass_pair import FailPassPair
from .step import Step


class ExtractAllBuildPairs(Step):
    def process(self, data: Any, context: dict) -> Dict[str, List[FailPassPair]]:
        log.info('Finding fail-pass and error-pass build pairs in each branch.')
        branches = data
        count = 0
        for branch_id, branch_obj in branches.items():
            builds = branch_obj.builds
            if len(builds) > 1:
                for b1, b2 in zip(builds, builds[1:]):
                    if (b1.failed() or b1.errored()) and b2.passed():
                        pair = FailPassPair(b1, b2)
                        branch_obj.pairs.append(pair)
                        count += 1
        log.info('Found {} build pairs from {} branches.'
                 .format(count, sum([1 for branch_id, branch_obj in branches.items() if branch_obj.pairs])))
        return data
