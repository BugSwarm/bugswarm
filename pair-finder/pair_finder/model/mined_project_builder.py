from typing import Dict
from datetime import datetime
from bugswarm.common import log
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.rest_api.database_api import DatabaseAPI


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
        self.last_date_mined = self.set_current_date()

    def build(self) -> Dict:
        return {
            'repo': self.repo,
            'latest_mined_version': self.latest_mined_version,
            'last_date_mined': self.last_date_mined,
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
    def query_current_metrics(repo):
        log.info('Attempting to query metrics from database for {}'.format(repo))
        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        results = bugswarmapi.find_mined_project(repo)
        if results.status_code != 200:
            log.info('Repository: {} has yet to be mined. Continuing.'.format(repo))
            return {
                'repo': '',
                'latest_mined_version': '',
                'last_date_mined': 'Mon, 01 Jan 1970 00:00:00 GMT',
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

    def set_current_date(self):
        today = datetime.today()
        formatted_date = today.strftime('%a, %d %b %Y %H:%M:%S GMT')
        return formatted_date
