from typing import Dict


class MinedProjectBuilder(object):
    def __init__(self):
        self.repo = None
        self.latest_mined_version = None

        # Progression metrics.
        self.builds = None
        self.jobs = None
        self.failed_builds = None
        self.failed_jobs = None
        self.failed_pr_builds = None
        self.failed_pr_jobs = None
        self.mined_build_pairs = None
        self.mined_job_pairs = None
        self.mined_pr_build_pairs = None
        self.mined_pr_job_pairs = None

    def build(self) -> Dict:
        return {
            'repo': self.repo,
            'latest_mined_version': self.latest_mined_version,
            'progression_metrics': {
                'builds': self.builds,
                'jobs': self.jobs,
                'failed_builds': self.failed_builds,
                'failed_jobs': self.failed_jobs,
                'failed_pr_builds': self.failed_pr_builds,
                'failed_pr_jobs': self.failed_pr_jobs,
                'mined_build_pairs': self.mined_build_pairs,
                'mined_job_pairs': self.mined_job_pairs,
                'mined_pr_build_pairs': self.mined_pr_build_pairs,
                'mined_pr_job_pairs': self.mined_pr_job_pairs,
            },
        }
