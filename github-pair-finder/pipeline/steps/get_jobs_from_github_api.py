from datetime import datetime, timedelta
import time

from bugswarm.common import log
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN
from bugswarm.common.github_wrapper import GitHubWrapper
from bugswarm.common.rest_api.database_api import DatabaseAPI
from model.mined_project_builder import MinedProjectBuilder

from .step_exception import StepException

from .step_exception import StepException


def get_pages_with_key(gh: GitHubWrapper, url: str, key: str):
    response, result = gh.get(url)
    all_results = result[key]
    while 'next' in response.links:
        response, result = gh.get(response.links['next']['url'])
        all_results += result[key]
    return all_results


def get_runs_after_cutoffs(gh: GitHubWrapper, repo: str, cutoff_run_id: int, cutoff_date: datetime):
    all_runs = []
    # Using cutoff_date limits the total number of runs to 1000, so we don't use it.
    url = 'https://api.github.com/repos/{}/actions/runs?per_page=100'.format(repo)
    still_finding_runs = True

    while still_finding_runs:
        response, result = gh.get(url)
        runs = result['workflow_runs']
        for i, run in enumerate(runs):
            run_date = datetime.strptime(run['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            if run['id'] <= cutoff_run_id or (cutoff_date is not None and run_date < cutoff_date):
                runs = runs[:i]
                still_finding_runs = False
                break
        all_runs += runs

        if 'next' in response.links:
            url = response.links['next']['url']
        else:
            still_finding_runs = False

    return all_runs


def count(lst, predicate):
    count = 0
    for e in lst:
        if predicate(e):
            count += 1
    return count


class GetJobsFromGitHubAPI:
    def process(self, data, context):
        repo = context['repo']
        gh = context['github_api']

        try:
            last_mined_build_id = context['original_mined_project_metrics']['last_build_mined']['build_id']
        except KeyError:
            last_mined_build_id = 0

        if context['use_cutoff_date']:
            # Maximum log retention period is 400 days for private repos, 90 for public repos.
            # We use 400 days for situations like a private repo going public.
            cutoff_date = datetime.now() - timedelta(days=400)
            log.info('Getting workflow runs for repo', repo, 'with ID >', last_mined_build_id,
                     'after cutoff date', cutoff_date.isoformat())
            runs = get_runs_after_cutoffs(gh, repo, int(last_mined_build_id), cutoff_date)
        else:
            log.info('Getting workflow runs for repo', repo, 'with ID >', last_mined_build_id)
            runs = get_runs_after_cutoffs(gh, repo, int(last_mined_build_id), None)

        if not runs:
            raise StepException('There are no new workflow runs for repo {}.'.format(repo))

        # Get the main language for the repo
        _, languages = gh.get('https://api.github.com/repos/{}/languages'.format(repo))
        if languages == {}:
            raise StepException('No language gotten from repo {}. Exiting pipeline.'.format(repo))
        main_language = max(languages.items(), key=lambda item: item[1])[0].lower()

        # Create the info list for each job
        log.info('Getting jobs for', len(runs), 'runs...')
        start_time = time.time()

        jobs = []
        filtered_runs = []
        latest_run_id = latest_run_number = None

        for i, run in enumerate(runs):
            if i % 50 == 0 and i != 0:
                log.info('Got jobs for', i, 'runs...')

            try:
                # We're only looking for jobs triggered by pushes and pull requests.
                # Other event kinds can cause problems futher down the pipeline.
                if run['event'] not in ['push', 'pull_request']:
                    continue
                # Runs can also have conclusions like "cancelled", "neutral", "timed_out", etc.
                # We don't want to consider them.
                if run['conclusion'] not in ['success', 'failure']:
                    continue

                if latest_run_id is None:
                    latest_run_id = run['id']
                    latest_run_number = run['run_number']

                # Get all jobs for a workflow run
                jobs_for_run = get_pages_with_key(gh, run['jobs_url'], 'jobs')

                for j, job in enumerate(jobs_for_run):
                    try:
                        # Some jobs don't actually have an equivalent entry in the workflow file.
                        # For example, in https://github.com/Adobe-Consulting-Services/acs-aem-commons/actions/runs/2545222818,
                        # none of the "Test report ..." jobs have an entry in their workflow file, even though
                        # they appear in the API. To detect this, check if the job has a label (e.g. ubuntu-latest,
                        # self-hosted)
                        if job['labels'] == '':
                            continue

                        # Get name and index of the first step that failed in this job, if any.
                        # Assumes that only one step can fail, and the rest are skipped. This is not always true!
                        # Note that steps that fail but have `continue-on-error` set to True are considered passing in
                        # the API, and thus in PairFinder as well.
                        failed_step_number = None
                        for s, step in enumerate(job['steps']):
                            if step['conclusion'] == 'failure':
                                failed_step_number = s
                                break

                        job_info = {
                            'job_id': job['id'],
                            'job_number': j + 1,
                            'job_name': job['name'],
                            'build_id': run['id'],
                            'number': run['run_number'],
                            'workflow_id': run['workflow_id'],
                            'workflow_path': run['path'],

                            'event_type': run['event'],
                            'result': job['conclusion'],
                            'finished_at': job['completed_at'],

                            'commit': run['head_sha'],
                            'message': run['head_commit']['message'],
                            'branch': run['head_branch'],
                            'committed_at': run['head_commit']['timestamp'],
                            'committer_name': run['head_commit']['committer']['name'],

                            'failed_step_number': failed_step_number,
                            'steps': job['steps'],

                            'language': main_language,  # How necessary is this for reproducing?
                        }

                        # run['head_repository'] is sometimes null; if it is, assume the branch is in the main repo.
                        # see https://api.github.com/repos/svg/svgo/actions/runs/1607135127
                        if run['head_repository'] is not None:
                            job_info['branch_owner'] = run['head_repository']['owner']['login']
                        else:
                            job_info['branch_owner'] = repo.split('/')[0]

                        for k, v in job_info.items():
                            if k != 'failed_step_number' and v is None:
                                log.warning('job_info["{}"] is None. Skipping the job.'.format(k))
                                continue

                        if run not in filtered_runs:
                            filtered_runs.append(run)

                        jobs.append(job_info)
                    except (KeyError, TypeError) as e:
                        job_id = job.get('id') if isinstance(job, dict) else None
                        log.warning(e)
                        log.warning('Error while mining job {}. Skipping that job.'.format(job_id))

            except (KeyError, TypeError) as e:
                run_id = run.get('id') if isinstance(run, dict) else None
                log.warning(e)
                log.warning('Error while mining run {}. Skipping that run.'.format(run_id))

        log.info('Got', len(jobs), 'jobs total from', len(filtered_runs), 'runs for repo', repo, 'in',
                 time.time() - start_time, 'seconds')

        # If no jobs were found, exit early
        if not jobs:
            api = DatabaseAPI(DATABASE_PIPELINE_TOKEN)
            api.set_latest_build_info_metric(
                repo, 'github', latest_run_number, latest_run_id)
            raise StepException('No new jobs found for repo {}.'.format(repo))

        # Update context
        num_failed_push_runs = count(
            filtered_runs,
            lambda run: run['conclusion'] == 'failure' and run['event'] == 'push')
        num_failed_pr_runs = count(
            filtered_runs,
            lambda run: run['conclusion'] == 'failure' and run['event'] == 'pull_request')
        num_failed_push_jobs = count(
            jobs, lambda job: job['result'] == 'failure' and job['event_type'] == 'push')
        num_failed_pr_jobs = count(
            jobs, lambda job: job['result'] == 'failure' and job['event_type'] == 'pull_request')

        builder: MinedProjectBuilder = context['mined_project_builder']
        orig_metrics = context['original_mined_project_metrics']['progression_metrics']

        builder.builds = len(filtered_runs) + orig_metrics['builds']
        builder.jobs = len(jobs) + orig_metrics['jobs']
        builder.failed_builds = orig_metrics['failed_builds'] + num_failed_push_runs
        builder.failed_jobs = orig_metrics['failed_jobs'] + num_failed_push_jobs
        builder.failed_pr_builds = orig_metrics['failed_pr_builds'] + num_failed_pr_runs
        builder.failed_pr_jobs = orig_metrics['failed_pr_jobs'] + num_failed_pr_jobs
        builder.last_build_mined = {'build_id': latest_run_id, 'build_number': latest_run_number}

        return jobs
