import argparse
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from bugswarm.common import log
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN, GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper
from bugswarm.common.json import write_json
from bugswarm.common.rest_api.database_api import DatabaseAPI

from model.mined_project_builder import MinedProjectBuilder
from pipeline.pipeline import Pipeline
from pipeline.steps import *


def parse_argv():
    p = argparse.ArgumentParser()

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('-r', '--repo', help='Repo slug. Cannot be used with --repo-file.')
    g.add_argument('--repo-file',
                   help='Path to file containing a newline-separated list of repo slugs. Cannot be used with --repo.')

    p.add_argument('-t', '--threads', type=int, default=1,
                   help='Maximum number of worker threads. Only useful if mining more than one repo. Defaults to '
                        '%(default)s.')
    p.add_argument('--log', default='INFO',
                   help='Log level. Use CRITICAL (least verbose), ERROR, WARNING, INFO (default), '
                        'or DEBUG (most verbose).')

    p.add_argument('--keep-clone', action='store_true',
                   help='Prevent the default cleanup of the cloned repo after running.')
    p.add_argument('--fast', action='store_true', help='Skips repos that already have an output file.')
    p.add_argument('--cutoff-days', type=int, default=90,
                   help='Workflow runs older than <%(dest)s> days will not be mined. Set to 0 to disable the limit. '
                        'Defaults to %(default)s days.')
    p.add_argument('--last-run-override', type=int,
                   help='Override the run ID of the last run that was mined for a repo. The miner will mine all runs '
                        'after the run with the given ID.')

    args = vars(p.parse_args())

    if args['threads'] < 1:
        p.error('-t/--threads cannot be less than 1')

    if args['cutoff_days'] < 0:
        p.error('--cutoff-days must be a positive integer.')

    return args


def count_mined_pairs(build_groups):
    if not build_groups:
        return 0, 0, 0, 0

    mined_push_build_pairs = mined_push_job_pairs = mined_pr_build_pairs = mined_pr_job_pairs = 0
    for group in build_groups.values():
        for build_pair in group.pairs:
            if build_pair.exclude_from_output:
                continue
            # TODO handle PR build pairs
            mined_push_build_pairs += 1
            mined_push_job_pairs += len(build_pair.jobpairs)
    return mined_push_build_pairs, mined_push_job_pairs, mined_pr_build_pairs, mined_pr_job_pairs


def output_json(repo, data, output_path):
    output_pairs = []
    for _, branch_obj in data.items():
        for p in branch_obj.pairs:
            # Exclude pairs that were marked in clean_pairs.py.
            if p.exclude_from_output:
                continue

            failed_build = p.failed_build
            passed_build = p.passed_build

            jobpairs = []
            for jp in p.jobpairs:
                jobpairs.append({
                    'failed_job': {
                        'job_id': jp.failed_job.job_id,
                    },
                    'passed_job': {
                        'job_id': jp.passed_job.job_id,
                    },
                    'failed_step_kind': jp.failed_job.failed_step_kind,
                    'failed_step_command': jp.failed_job.failed_step_command,
                    'build_system': jp.build_system
                })

            pair = {
                'repo': repo,
                'ci_service': 'github',
                'repo_mined_version': p.repo_mined_version,
                'pr_num': -1,
                'merged_at': branch_obj.merged_at,
                'branch': branch_obj.branch_name,
                'base_branch': branch_obj.base_branch,
                'is_error_pass': failed_build.errored(),
                'failed_build': {
                    'build_id': failed_build.build_id,
                    'travis_merge_sha': None,
                    'base_sha': failed_build.base_commit,
                    'head_sha': failed_build.commit,
                    'github_archived': failed_build.github_archived,
                    'resettable': failed_build.resettable,
                    'committed_at': failed_build.committed_at,
                    'message': failed_build.message,
                    'jobs': [{'build_job': '{}.{}'.format(failed_build.build_num, j.job_num),
                              'job_id': j.job_id,
                              'config': j.config or {},
                              'language': j.language}
                             for j in failed_build.jobs],
                    'has_submodules': failed_build.has_submodules
                },
                'passed_build': {
                    'build_id': passed_build.build_id,
                    'travis_merge_sha': None,
                    'base_sha': passed_build.base_commit,
                    'head_sha': passed_build.commit,
                    'github_archived': passed_build.github_archived,
                    'resettable': passed_build.resettable,
                    'committed_at': passed_build.committed_at,
                    'message': passed_build.message,
                    'jobs': [{'build_job': '{}.{}'.format(passed_build.build_num, j.job_num),
                              'job_id': j.job_id,
                              'config': j.config or {},
                              'language': j.language}
                             for j in passed_build.jobs],
                    'has_submodules': passed_build.has_submodules
                },
                'jobpairs': jobpairs,
            }
            output_pairs.append(pair)

    write_json(output_path, output_pairs)


def thread_main(repo, task_name, args):
    hyphenated_repo = repo.replace('/', '-')
    ci_service = 'github'

    output_json_path = os.path.join('output', task_name, f'{hyphenated_repo}.json')
    if args['fast'] and os.path.exists(output_json_path) and os.path.getsize(output_json_path) > 0:
        log.info('Output file for', repo, 'already exists. Skipping.')
        return

    pipeline = Pipeline([
        Preflight(),
        GetJobsFromGitHubAPI(),
        GroupJobs(),
        ExtractAllBuildPairs(),
        ConstructJobConfig(),
        AlignJobPairs(),
        CheckBuildIsResettable(),
        GetBuildSystemInfo(),
        CleanPairs(),
        Postflight(),
    ])
    in_context = {
        'repo': repo,
        'keep_clone': args['keep_clone'],
        'github_api': GitHubWrapper(GITHUB_TOKENS),
        'mined_project_builder': MinedProjectBuilder(),
        'original_mined_project_metrics': MinedProjectBuilder.query_current_metrics(repo, ci_service),
        'utils': None,
        'cutoff_days': args['cutoff_days']
    }

    if args['last_run_override'] is not None:
        in_context['original_mined_project_metrics']['last_build_mined']['build_id'] = args['last_run_override']

    data, out_context = pipeline.run(None, in_context)

    if not data:
        log.info('Skipping', repo, 'since the pipeline exited early.')
        return False

    # Set up mined project statistics
    (mined_push_build_pairs, mined_push_job_pairs,
     mined_pr_build_pairs, mined_pr_job_pairs) = count_mined_pairs(data)
    orig_metrics = out_context['original_mined_project_metrics']['progression_metrics']

    builder: MinedProjectBuilder = out_context['mined_project_builder']
    builder.repo = repo
    builder.ci_service = ci_service
    builder.latest_mined_version = out_context['head_commit']
    builder.mined_build_pairs = orig_metrics['mined_build_pairs'] + mined_push_build_pairs
    builder.mined_job_pairs = orig_metrics['mined_job_pairs'] + mined_push_job_pairs
    builder.mined_pr_build_pairs = orig_metrics['mined_pr_build_pairs'] + mined_pr_build_pairs
    builder.mined_pr_job_pairs = orig_metrics['mined_pr_job_pairs'] + mined_pr_job_pairs

    mined_project = builder.build()

    # Output to database
    log.info('Outputting mined project to database.')
    db = DatabaseAPI(DATABASE_PIPELINE_TOKEN)
    if db.find_mined_project(repo, ci_service).status_code != 200:
        db.upsert_mined_project(mined_project)
    else:
        for k, v in mined_project['progression_metrics'].items():
            db.set_mined_project_progression_metric(repo, ci_service, k, v)
        db.set_latest_build_info_metric(
            repo,
            ci_service,
            mined_project['last_build_mined']['build_number'],
            mined_project['last_build_mined']['build_id'])
    log.info('Done outputting to database.')

    # Output json
    output_json_path = os.path.join('output', task_name, f'{hyphenated_repo}.json')
    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    output_json(repo, data, output_json_path)
    log.info('Wrote output data to', output_json_path)

    original_metrics_path = 'output/original_metrics/{}.json'.format(hyphenated_repo)
    os.makedirs(os.path.dirname(original_metrics_path), exist_ok=True)
    write_json(original_metrics_path, out_context['original_mined_project_metrics'])
    log.info('Wrote original metrics to', original_metrics_path)

    log.info('Finished processing {}!'.format(repo))
    return True


def main():
    args = parse_argv()

    try:
        log.config_logging(args['log'].upper())
    except ValueError:
        log.config_logging('INFO')
        log.warning('Unknown/invalid log level "{}". Defaulting to "INFO".'.format(args['log']))

    if args['repo_file']:
        with open(args['repo_file']) as f:
            repos = [line.strip() for line in f.readlines()]
        task_name = os.path.basename(os.path.splitext(args['repo_file'])[0])
    else:
        repos = [args['repo']]
        task_name = args['repo'].replace('/', '-')

    with ThreadPoolExecutor(max_workers=args['threads']) as exe:
        futures = {exe.submit(thread_main, repo, task_name, args): repo for repo in repos}

    num_successful = 0
    num_skipped = 0
    tracebacks = []
    for future in as_completed(futures):
        repo = futures[future]
        try:
            if future.result():
                num_successful += 1
            else:
                num_skipped += 1
        except Exception:
            tracebacks.append((repo, traceback.format_exc()))

    log.info()
    log.info('=== SUMMARY ===')
    log.info(len(futures), 'repo(s) processed.', num_successful, 'succeeded,', num_skipped, 'got skipped, and',
             len(tracebacks), 'errored.')

    for repo, tb in tracebacks:
        log.error(repo, 'encountered the following exception:')
        for line in tb.splitlines():
            log.error(line)

    if num_successful == 0:
        log.error('Pipeline finished, but no repos were successfully mined.')
        return 1
    log.info('Pipeline finished!')


if __name__ == '__main__':
    sys.exit(main())
