import json
from typing import Dict

from bugswarm.common import log
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.rest_api.database_api import DatabaseAPI


class MinedProjectBuilder(object):
    def __init__(self):
        self.repo = None
        self.ci_service = None
        self.latest_mined_version = None
        self.last_build_mined = {
            'build_id': 0,
            'build_number': 0
        }

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
            'ci_service': self.ci_service,
            'latest_mined_version': self.latest_mined_version,
            'last_build_mined': self.last_build_mined,
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

    @staticmethod
    def query_current_metrics(repo: str, ci_service: str) -> dict:
        log.info('Attempting to query metrics from database for {}'.format(repo))
        bugswarmapi: DatabaseAPI = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        results = bugswarmapi.find_mined_project(repo, ci_service)
        if results.status_code != 200:
            log.info('Repository: {} has yet to be mined. Continuing.'.format(repo))
            return {
                'repo': repo,
                'ci_service': ci_service,
                'latest_mined_version': '',
                'last_build_mined': {
                    'build_id': 0,
                    'build_number': 0
                },
                'progression_metrics': {
                    'builds': 0,
                    'jobs': 0,
                    'failed_builds': 0,
                    'failed_jobs': 0,
                    'failed_pr_builds': 0,
                    'failed_pr_jobs': 0,
                    'mined_build_pairs': 0,
                    'mined_job_pairs': 0,
                    'mined_pr_build_pairs': 0,
                    'mined_pr_job_pairs': 0,
                },
            }
        return results.json()
