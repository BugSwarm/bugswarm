from typing import Any
from typing import Dict
from typing import List

from bugswarm.common import log

from model.fail_pass_pair import FailPassPair
from model.job_pair import JobPair


class AlignJobPairs:
    def process(self, data: Any, context: dict) -> Dict[str, List[FailPassPair]]:
        log.info('Aligning job pairs.')
        branches = data

        total_jobpairs = 0
        for branch_id, branch_obj in branches.items():
            for buildpair in branch_obj.pairs:
                for failed_job in buildpair.failed_build.jobs:
                    for passed_job in buildpair.passed_build.jobs:
                        # If the failed job and the passed job have the same config, then they are 'aligned.'
                        # We also want to filter out pass-pass job pairs. since some jobs in the failed build may have
                        # passed, we make sure that the failed job did not pass by checking its
                        # 'result' value.

                        # if failed_job.config == passed_job.config and failed_job.result != 0:
                        if (failed_job.config == passed_job.config and
                                failed_job.config is not None and
                                failed_job.result == 'failure' and
                                passed_job.result == 'success'):
                            buildpair.jobpairs.append(JobPair(failed_job, passed_job))
                            total_jobpairs += 1
        log.debug('Aligned', total_jobpairs, 'job pairs.')
        return data
