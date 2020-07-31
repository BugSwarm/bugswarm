import datetime

from typing import Dict

from bugswarm.common import log
from bugswarm.common.json import write_json
from bugswarm.common.rest_api.database_api import DatabaseAPI
from bugswarm.common.credentials import DATABASE_PIPELINE_TOKEN


class OutputManager(object):
    """
    Manage writing the output file and updating the mined projects database collection.
    """
    @staticmethod
    def output(repo: str, output_path: str, branches: Dict):
        total_buildpairs = 0
        resettable_buildpairs = 0
        total_jobpairs = 0
        output_pairs = []
        for _, branch_obj in branches.items():
            for p in branch_obj.pairs:
                # Exclude pairs that were marked in clean_pairs.py.
                if p.exclude_from_output:
                    continue

                failed_build = p.failed_build
                passed_build = p.passed_build

                # For buildpair stats.
                total_buildpairs += 1
                if failed_build.resettable and passed_build.resettable:
                    resettable_buildpairs += 1

                # For jobpair stats.
                total_jobpairs += len(p.jobpairs)

                jobpairs = []
                for jp in p.jobpairs:
                    jobpairs.append({
                        'failed_job': {
                            'job_id': jp.failed_job.job_id,
                        },
                        'passed_job': {
                            'job_id': jp.passed_job.job_id,
                        },
                        'build_system': jp.build_system
                    })

                pair = {
                    'repo': repo,
                    'repo_mined_version': p.repo_mined_version,
                    'pr_num': branch_obj.pr_num,
                    'merged_at': branch_obj.merged_at,
                    'branch': branch_obj.branch_name,
                    'base_branch': branch_obj.base_branch,
                    'is_error_pass': failed_build.errored(),
                    'failed_build': {
                        'build_id': failed_build.build_id,
                        'travis_merge_sha': failed_build.commit if branch_obj.pr_num > 0 else None,
                        'base_sha': failed_build.base_commit,
                        'head_sha': failed_build.trigger_commit,
                        'github_archived': failed_build.github_archived,
                        'resettable': failed_build.resettable,
                        'committed_at': OutputManager._convert_datetime_to_github_timestamp(failed_build.committed_at)
                        if isinstance(failed_build.committed_at, datetime.datetime) else failed_build.committed_at,
                        'message': failed_build.message,
                    },
                    'passed_build': {
                        'build_id': passed_build.build_id,
                        'travis_merge_sha': passed_build.commit if branch_obj.pr_num > 0 else None,
                        'base_sha': passed_build.base_commit,
                        'head_sha': passed_build.trigger_commit,
                        'github_archived': passed_build.github_archived,
                        'resettable': passed_build.resettable,
                        'committed_at': OutputManager._convert_datetime_to_github_timestamp(passed_build.committed_at)
                        if isinstance(passed_build.committed_at, datetime.datetime) else passed_build.committed_at,
                        'message': passed_build.message,
                    },
                    'jobpairs': jobpairs,
                }
                builds = [failed_build, passed_build]
                for i in range(2):
                    build_name = 'failed_build' if i == 0 else 'passed_build'
                    pair[build_name]['jobs'] = []
                    build = builds[i]
                    for j in build.jobs:
                        job = {
                            'build_job': '{}.{}'.format(build.build_num, j.job_num),
                            'job_id': j.job_id,
                            'config': j.config,
                            'language': OutputManager.adjust_language(j.language),
                        }
                        pair[build_name]['jobs'].append(job)

                output_pairs.append(pair)

        # Write output JSON to file.
        log.info('Saving output to', output_path)
        write_json(output_path, output_pairs)
        log.info('Done writing output file.')

        log.info('Total build pairs found:', total_buildpairs)
        log.info('Total job pairs found:', total_jobpairs)
        log.debug('Total resettable build pairs found:', resettable_buildpairs)

    @staticmethod
    def output_to_database(mined_project: Dict):
        # Update the mined projects database collection with the mining progression metrics.
        log.info('Writing mined project to the database.')
        bugswarmapi = DatabaseAPI(token=DATABASE_PIPELINE_TOKEN)
        results = bugswarmapi.find_mined_project(mined_project['repo'])
        if results.status_code != 200:
            bugswarmapi.upsert_mined_project(mined_project)
        else:
            for key, val in mined_project['progression_metrics'].items():
                bugswarmapi.set_mined_project_progression_metric(mined_project['repo'], key, val)
            bugswarmapi.set_latest_build_info_metric(mined_project['repo'],
                                                     mined_project['last_build_mined']['build_number'],
                                                     mined_project['last_build_mined']['build_id'])
        log.info('Done writing to database.')

    @staticmethod
    def adjust_language(lang: str):
        if lang.lower() == 'node_js':
            return 'javascript'
        return lang

    @staticmethod
    def _convert_datetime_to_github_timestamp(dt):
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
