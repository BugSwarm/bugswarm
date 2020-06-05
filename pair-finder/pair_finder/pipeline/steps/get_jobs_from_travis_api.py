"""
Download metadata via the Travis API for all jobs for a repository.
"""

import os
import time
import dateutil.parser

from threading import Lock
from typing import Any
from typing import Optional
from typing import Tuple
from requests.exceptions import RequestException
from datetime import datetime

from bugswarm.common import log
from bugswarm.common.json import read_json
from bugswarm.common.json import write_json
from bugswarm.common.travis_wrapper import TravisWrapper

from .step import Step
from .step import StepException
from ...utils import Utils


class GetJobsFromTravisAPI(Step):
    def process(self, data: Any, context: dict) -> Optional[Any]:
        repo = context['repo']
        mined_build_exists = False
        lock = Lock()
        with lock:
            travis = TravisWrapper()

        highest_build_number = 0
        highest_build_number_id = 0
        if context['original_mined_project_metrics']['last_build_mined']['build_number']:
            highest_build_number = context['original_mined_project_metrics']['last_build_mined']['build_number']
            highest_build_number_id = context['original_mined_project_metrics']['last_build_mined']['build_id']
            mined_build_exists = True

        builds_json_file = Utils.get_repo_builds_api_result_file(repo)
        builds_info_json_file = Utils.get_repo_builds_info_api_result_file(repo)
        if os.path.isfile(builds_json_file):
            build_list = read_json(builds_json_file)
        else:
            log.info('Getting the list of builds...')
            start_time = time.time()
            try:
                if not mined_build_exists:
                    # gets all builds for project
                    builds = travis.get_builds_for_repo(repo)
                else:
                    # gets the latest builds and stops mining after reaching our last mined build number
                    builds = travis.get_builds_for_repo(repo, highest_build_number)
            except RequestException:
                error_message = 'Encountered an error while downloading builds for repository {}.'.format(repo)
                raise StepException(error_message)
            build_list = list(builds)
            write_json(builds_json_file, build_list)
            log.info('Got the list of builds in', time.time() - start_time, 'seconds.')

        if os.path.isfile(builds_info_json_file):
            build_list = read_json(builds_info_json_file)
        else:
            log.info('Downloading build info for',
                     len(build_list),
                     'builds... This step may take several minutes for large repositories.')
            start_time = time.time()
            for idx, build in enumerate(build_list):
                build_id = build['id']
                build_number = int(build['number'])
                if build_number > highest_build_number:
                    highest_build_number_id = build_id
                    highest_build_number = build_number
                try:
                    build_info = travis.get_build_info(build_id)
                except RequestException:
                    error_message = 'Encountered an error while downloading build info for build {}.'.format(build_id)
                    raise StepException(error_message)
                build['build_info'] = build_info
                if (idx + 1) % 500 == 0:
                    log.info('Downloaded build info for', idx + 1, 'builds so far...')
            write_json(builds_info_json_file, build_list)
            log.info('Downloaded build info in', time.time() - start_time, 'seconds.')

        # Now that we have data from the Travis API, restructure it so it appears as if it came from the database using
        # the following query:
        #   SELECT j.job_id, j.job_number, j.config, j.result,
        #          b.build_id, b.number, b.finished_at, b.commit, b.branch, b.event_type, b.language,
        #          c.committed_at, c.compare_at, c.committer_name, c.message
        #   FROM jobs j
        #   LEFT JOIN builds b on b.build_id = j.build_id
        #   LEFT JOIN commits c on b.commit = c.sha
        #   WHERE j.repo_id = "<repo_id>"
        jobs = []
        latest_build_date_time = datetime(1970, 1, 1)
        for build in build_list:
            try:
                # build['finished_at'] returns an ISO 8601 time representation. Ex - 2015-07-13T12:40:51Z
                # while context['last_date_mined'] returns an int representing Unix Epoch formatted as: '1580098839'
                # We must convert the ISODate representation to datetime and the Unix Epoch to datetime for comparison
                parsed_time = dateutil.parser.parse(build['finished_at'])
                build_formatted_date = parsed_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
                build_date = datetime.strptime(build_formatted_date, '%a, %d %b %Y %H:%M:%S GMT')
                last_mined_date = datetime.fromtimestamp(context['original_mined_project_metrics']['last_date_mined'])
                if latest_build_date_time < build_date:
                    latest_build_date_time = build_date
                    context['mined_project_builder'].last_date_mined = latest_build_date_time.timestamp()
                if build_date <= last_mined_date:
                    continue
            except (KeyError, TypeError) as e:
                log.info('Build ID:', build['id'], 'contains the following error:')
                log.error(e)
                continue
            for job in build['build_info']['matrix']:
                j = {
                    'job_id': job['id'],
                    'job_number': job['number'],
                    'config': job['config'],
                    'result': job['result'],
                    'build_id': build['id'],
                    'number': build['number'],
                    'finished_at': job['finished_at'],
                    'commit': build['commit'],
                    'message': build['message'],
                    'branch': build['branch'],
                    'event_type': build['build_info']['event_type'],
                    'committed_at': build['build_info']['committed_at'],
                    'compare_at': build['build_info']['compare_url'],
                    'committer_name': build['build_info']['committer_name'],
                }
                if 'language' in job['config']:
                    language = job['config']['language']
                else:
                    log.debug('Language not found in config, defaulting to ruby for job ID {}.'.format(job['id']))
                    language = 'ruby'
                j['language'] = language
                jobs.append(j)

        if not jobs:
            msg = 'Did not get any jobs for {}.'.format(repo)
            raise StepException(msg)

        # Expose mining progression metrics via the context. Other pipeline steps must not change these values.
        # Do not raise a StepException before the context is populated.
        failed_builds, failed_pr_builds = GetJobsFromTravisAPI._count_failed_builds(build_list)
        failed_jobs, failed_pr_jobs = GetJobsFromTravisAPI._count_failed_jobs(build_list)
        context['mined_project_builder'].builds = len(build_list) + \
            context['original_mined_project_metrics']['progression_metrics']['builds']
        context['mined_project_builder'].jobs = len(jobs) + \
            context['original_mined_project_metrics']['progression_metrics']['jobs']
        context['mined_project_builder'].failed_builds = failed_builds + \
            context['original_mined_project_metrics']['progression_metrics']['failed_builds']
        context['mined_project_builder'].failed_jobs = failed_jobs + \
            context['original_mined_project_metrics']['progression_metrics']['failed_jobs']
        context['mined_project_builder'].failed_pr_builds = failed_pr_builds + \
            context['original_mined_project_metrics']['progression_metrics']['failed_pr_builds']
        context['mined_project_builder'].failed_pr_jobs = failed_pr_jobs + \
            context['original_mined_project_metrics']['progression_metrics']['failed_pr_jobs']
        context['mined_project_builder'].last_build_mined['build_id'] = highest_build_number_id
        context['mined_project_builder'].last_build_mined['build_number'] = highest_build_number

        return jobs

    @staticmethod
    def _count_failed_builds(build_list) -> Tuple[int, int]:
        failed_builds = 0
        failed_pr_builds = 0
        for b in build_list:
            if b['build_info']['result'] == 0:
                # The build succeeded, so don't count it.
                continue
            is_pr = b['event_type'] == 'pull_request'
            if is_pr:
                failed_pr_builds += 1
            else:
                failed_builds += 1
        return failed_builds, failed_pr_builds

    @staticmethod
    def _count_failed_jobs(build_list) -> Tuple[int, int]:
        failed_jobs = 0
        failed_pr_jobs = 0
        for b in build_list:
            is_pr = b['event_type'] == 'pull_request'
            for j in b['build_info']['matrix']:
                # This condition accounts for when the Travis API returns a null job result. In those cases, assume the
                # build did not succeed.
                # A brief investigation suggests that the result is null when the job errored. See an example at
                # https://api.travis-ci.org/jobs/49217775. The corresponding Travis page with a GUI is at
                # https://travis-ci.org/gwtbootstrap3/gwtbootstrap3/jobs/49217775.
                if j.get('result') != 0:
                    if is_pr:
                        failed_pr_jobs += 1
                    else:
                        failed_jobs += 1
        return failed_jobs, failed_pr_jobs
