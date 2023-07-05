from multiprocessing import Value


class JobPair(object):
    def __init__(self,
                 repo_slug,
                 failed_job,
                 passed_job,
                 match=None,
                 match_over_runs=None,
                 stable=None,
                 match_history=None,
                 failed_job_match_history=None,
                 passed_job_match_history=None):
        self.repo_slug = repo_slug
        # Job objects representing the failed and passed jobs.
        self.jobs = [failed_job, passed_job]
        self.jobpair_name = str(failed_job.job_id) + '-' + str(passed_job.job_id)
        self.match = Value('i', match) if match else Value('i', 0)
        # self.match_over_runs = match_over_runs if match_over_runs else 0
        # self.stable = stable if stable else False
        self.match_history = match_history if match_history else {}
        self.is_errorpass = False
        self.failed_job_match_history = failed_job_match_history if failed_job_match_history else {}
        self.passed_job_match_history = passed_job_match_history if passed_job_match_history else {}
        self.reproduced = Value('i', 0)
        self.skip = False
        self.err_reason = 'NA'
        self.buildpair_name = ''  # Will be initialized in PairCenter.init_names().
        self.full_name = ''  # Will be initialized in PairCenter.init_names().

    def __str__(self):
        return 'JobPair(' + str(self.full_name) + ')'

    def __repr__(self):
        return 'JobPair(' + str(self.full_name) + ')'
