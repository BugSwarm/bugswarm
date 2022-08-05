from .job import Job
from reproducer.utils import Utils


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

            # Find image tag from buildpair JSON.
            # TODO: Find out why we only care about the first pair?
            jobpairs = buildpair.json_data['jobpairs']
            failed_job = jobpairs[0]['failed_job']
            passed_job = jobpairs[0]['passed_job']
            # Job objects are made for each job in a build. We only want to look for the image_tag if it is the failing
            # or passing job.
            config = Utils.replace_matrix(j['config'])

            if j['job_id'] == failed_job['job_id']:
                # image_tag = failed_job['heuristically_parsed_image_tag']
                # Replace matrix
                image_tag = config['runs-on']
            elif j['job_id'] == passed_job['job_id']:
                # image_tag = passed_job['heuristically_parsed_image_tag']
                image_tag = config['runs-on']
            else:
                image_tag = None

            # Create the Job object. If the reproduced result and analyzed result are already in the JSON file, which
            # means this job has been reproduced before, add those results to the Job object.
            job_obj = Job(self, j['build_job'], j['job_id'], j['language'], config, image_tag)
            job_obj.reproduced_result = j.get('reproduced_result')
            job_obj.orig_result = j.get('orig_result')
            self.jobs.append(job_obj)
