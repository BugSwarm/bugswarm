from model.build import Build
from model.build_group import BuildGroup
from model.job import Job


class GroupJobs:
    """Sorts jobs within their workflow runs (called "builds" in BugSwarm
    nomenclature), and groups builds by their branch and workflow IDs.
    Mostly identical to the Travis pipeline's GroupJobsByBranch, but with some
    Travis-specific code removed (mostly to do with pull request builds).
    """

    def process(self, jobs, context):
        groups: 'dict[str, BuildGroup]' = {}

        for job in jobs:
            workflow_id = job['workflow_id']
            branch_id = job['branch']
            branch_owner = job['branch_owner']
            build_id = job['build_id']
            job_id = job['job_id']

            group_id = '{}~{}~{}'.format(workflow_id, branch_owner, branch_id)

            if group_id not in groups:
                groups[group_id] = BuildGroup(branch_id, branch_owner, workflow_id, job['workflow_path'])
            group = groups[group_id]

            build = group.get_build(build_id)
            if build is None:
                build = Build(build_id,
                              job['number'],
                              job['commit'],
                              job['message'],
                              job['committed_at'])
                group.builds.append(build)

            if not build.get_job(job_id):
                # Config is None for GHA jobs
                j = Job(
                    job_id,
                    job['job_number'],
                    None,
                    job['language'],
                    job['result'],
                    job['job_name'],
                    job['failed_step_number'])
                build.jobs.append(j)

        for group in groups.values():
            group.sort_builds()
            for build in group.builds:
                build.update_status()

        return groups
