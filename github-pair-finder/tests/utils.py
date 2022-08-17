import os

from model.build import Build
from model.build_group import BuildGroup
from model.fail_pass_pair import FailPassPair
from model.job import Job
from model.job_pair import JobPair

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


class DataFromDict:
    def __init__(self):
        self.build_cache = {}
        self.job_cache = {}

    def job_from_dict(self, d):
        if d['job_id'] in self.job_cache:
            return self.job_cache[d['job_id']]

        j = Job(None, None, None, None, None, None)
        for k, v in d.items():
            setattr(j, k, v)

        self.job_cache[j.job_id] = j
        return j

    def build_from_dict(self, d):
        if d['build_id'] in self.build_cache:
            return self.build_cache[d['build_id']]

        b = Build(None, None, None, None, None)
        for k, v in d.items():
            if k == 'jobs':
                for job_dict in v:
                    b.jobs.append(self.job_from_dict(job_dict))
            else:
                setattr(b, k, v)

        self.build_cache[b.build_id] = b
        return b

    def jobpair_from_dict(self, d):
        jp = JobPair(None, None)
        for k, v in d.items():
            if k in ['failed_job', 'passed_job']:
                setattr(jp, k, self.job_from_dict(v))
        return jp

    def buildpair_from_dict(self, d):
        bp = FailPassPair(None, None)
        for k, v in d.items():
            if k in ['failed_build', 'passed_build']:
                setattr(bp, k, self.build_from_dict(v))
            elif k == 'jobpairs':
                for pair_dict in v:
                    bp.jobpairs.append(self.jobpair_from_dict(pair_dict))
            else:
                setattr(bp, k, v)
        return bp

    def buildgroup_from_dict(self, d):
        bg = BuildGroup(None, None, None, None)
        for k, v in d.items():
            if k == 'pairs':
                for build_pair in v:
                    bg.pairs.append(self.buildpair_from_dict(build_pair))
            elif k == 'builds':
                for build_dict in v:
                    bg.builds.append(self.build_from_dict(build_dict))
            else:
                setattr(bg, k, v)
        return bg


def pipeline_data_from_dict(d):
    dfd = DataFromDict()
    return {key: dfd.buildgroup_from_dict(build_group) for key, build_group in d.items()}


def to_dict(obj):
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_dict(e) for e in obj]
    if hasattr(obj, '__dict__'):
        return to_dict(vars(obj))
    return obj
