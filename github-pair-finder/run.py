import json
import os
import sys

import argparse

from bugswarm.common import log
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN, GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper
from bugswarm.common.json import read_json, write_json
from bugswarm.common.rest_api.database_api import DatabaseAPI

from model.mined_project_builder import MinedProjectBuilder
from pipeline.pipeline import Pipeline
from pipeline.steps import *


def parse_argv():
    p = argparse.ArgumentParser()
    p.add_argument('repo', help='The repo to mine.')
    p.add_argument(
        'last_run_id',
        type=int,
        nargs='?',
        help='''The cutoff workflow run ID. All mined workflow runs will have been run
                after <last-run>. In the real pipeline, this is obtained from the database.''')
    p.add_argument('-o', '--out-file', default='out_data.json',
                   help='The file to write the output data to. Default: out_data.json')
    p.add_argument('--no-cutoff-date', action='store_true',
                   help='Flag that removes the 400-day mining limit (aka workflow runs older than 400 days can be mined).')

    args = p.parse_args()
    return args.repo, args.last_run_id, args.out_file, args.no_cutoff_date


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


def get_head_commit(gh: GitHubWrapper, repo):
    _, result = gh.get('https://api.github.com/repos/{}/commits'.format(repo))
    return result[0]['sha']


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
                },
                'jobpairs': jobpairs,
            }
            output_pairs.append(pair)

    write_json(output_path, output_pairs)


def main():
    log.config_logging('INFO')

    repo, last_run, out_file, no_cutoff_date = parse_argv()
    ci_service = 'github'

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
        'keep_clone': False,
        'github_api': GitHubWrapper(GITHUB_TOKENS),
        'mined_project_builder': MinedProjectBuilder(),
        'original_mined_project_metrics': MinedProjectBuilder.query_current_metrics(repo, ci_service),
        'utils': None,
        'use_cutoff_date': not no_cutoff_date,
    }

    if last_run is not None:
        in_context['original_mined_project_metrics']['last_build_mined']['build_id'] = last_run

    data, out_context = pipeline.run(None, in_context)

    if not data:
        log.info('Skipping', repo, 'since the pipeline exited early.')
        return

    # Set up mined project statistics
    head_commit = get_head_commit(out_context['github_api'], repo)
    (mined_push_build_pairs, mined_push_job_pairs,
     mined_pr_build_pairs, mined_pr_job_pairs) = count_mined_pairs(data)
    orig_metrics = out_context['original_mined_project_metrics']['progression_metrics']

    builder: MinedProjectBuilder = out_context['mined_project_builder']
    builder.repo = repo
    builder.ci_service = ci_service
    builder.latest_mined_version = head_commit
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
    output_json(repo, data, out_file)
    log.info('Wrote output data to', out_file)

    original_metrics_path = 'output/original_metrics/{}.json'.format(repo.replace('/', '-'))
    os.makedirs(os.path.dirname(original_metrics_path), exist_ok=True)
    write_json(original_metrics_path, out_context['original_mined_project_metrics'])
    log.info('Wrote original metrics to', original_metrics_path)

    log.info('Pipeline finished!')


if __name__ == '__main__':
    sys.exit(main())
