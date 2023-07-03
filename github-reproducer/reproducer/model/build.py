from .job import Job


class Build(object):
    def __init__(self, buildpair, build_info, is_failed):
        self.buildpair = buildpair
        self.build_id = build_info['build_id']
        self.base_sha = build_info['base_sha']
        self.head_sha = build_info['head_sha']
        self.travis_merge_sha = build_info['travis_merge_sha']
        self.resettable = build_info['resettable']
        self.github_archived = build_info['github_archived']
        self.commit_time = build_info['committed_at']
        self.is_failed = is_failed
        self.jobs = []
        for j in build_info['jobs']:
            # This is an edge case due to an implementation detail of the Travis API. Sometimes, the build_job format is
            # build_num.build_num.job_num in which case we change it to build_num.job_num.
            components = j['build_job'].split('.')
            if len(components) == 3:
                j['build_job'] = '.'.join([components[0], components[2]])

            config = j['config']

            # Create the Job object. If the reproduced result and analyzed result are already in the JSON file, which
            # means this job has been reproduced before, add those results to the Job object.
            job_obj = Job(self, j['build_job'], j['job_id'], j['language'], config)
            job_obj.reproduced_result = j.get('reproduced_result')
            job_obj.orig_result = j.get('orig_result')
            self.jobs.append(job_obj)
