from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from bugswarm.common import log

from ...model.build import Build
from ...model.job import Job

from ...model.branch import Branch
from .step import Step
from .step import StepException


class GroupJobsByBranch(Step):
    def process(self, data: Any, context: dict) -> Dict[str, List[Branch]]:
        repo = context['repo']
        utils = context['utils']

        log.info('Grouping builds and jobs by branch.')

        # Mapping from branch ID to Branch object.
        branches = {}

        for job in data:
            if job['event_type'] == 'pull_request':
                if job['compare_at'] and '/pull/' in job['compare_at']:
                    pr_num = int(job['compare_at'].split('/pull/')[1])
                    branch_name = utils.github.get_head_branch_for_pr(repo, str(pr_num))
                else:
                    log.debug('job_id =', job['job_id'], 'compare_at =', job['compare_at'])
                    log.error('Job was triggered from a pull request, but cannot get pr_num from compare_at.')
                    raise StepException
            else:
                branch_name = job['branch']
                # Sentinel pr_num to indicate a non-PR branch.
                pr_num = -1
                # If Travis returns a null branch name for the job or if we cannot get a head branch name for a pull
                # request job, then ignore the job. See the method documentation for GitHub.get_head_branch_for_pr for
                # more information on the latter case.
                if not branch_name:
                    log.info('Ignoring job {} (in build {}) since it is missing a head branch name.'
                             .format(job['job_id'], job['build_id']))
                    continue
            GroupJobsByBranch._append_job_to_branch(branches, branch_name, job, pr_num)

        for branch_id, branch_obj in branches.items():
            branch_obj.sort_builds()
        for branch_id, branch_obj in branches.items():
            for build in branch_obj.builds:
                build.update_status()
        return branches

    @staticmethod
    def _append_job_to_branch(branches: Dict, branch_name: Optional[str], job: Dict, pr_num: int):
        branch_id = Branch.construct_branch_id(branch_name, pr_num)
        if branch_id not in branches:
            branches[branch_id] = Branch(branch_name, pr_num)

        build = branches[branch_id].get_build(job['build_id'])
        if not build:
            build = Build(job['build_id'],
                          job['number'],
                          job['commit'],
                          job['message'],
                          job['committed_at'],
                          job['committer_name'],
                          job['finished_at'])
            branches[branch_id].builds.append(build)

        j = build.get_job(job['job_id'])
        if not j:
            # Travis returns the job_number in the form '<build_num>.<job_num>'.
            # So split on the period to extract the job number.
            job_num = job['job_number'].split('.')[-1]
            # Depending on how the project's .travis.yml was written, the Travis API returns the language as a string or
            # a list of strings:
            #   { ..., language: 'java', ... }
            #   vs.
            #   { ..., language: ['java'], ... }
            # We are not sure if the second form can have multiple languages in the list. Regardless, if we have the
            # second form, then we take the first language in the list.
            if isinstance(job['language'], list):
                language = job['language'][0]
            else:
                language = job['language']
            j = Job(job['job_id'], job_num, job['config'], language, job['result'])
            build.jobs.append(j)
