import os
import re
from typing import List, Tuple

from bugswarm.common import filter_reasons as reasons
from bugswarm.common import log
from bugswarm.common.json import read_json
from bugswarm.common.log_downloader import download_log

from . import utils
from .constants import (DOCKERHUB_IMAGES_JSON, FILTERED_REASON_KEY,
                        PARSED_IMAGE_TAG_KEY, TRAVIS_IMAGES_JSON)
from .image_chooser import (ExactImageChooserByCommitSHA,
                            ExactImageChooserByTag, ExactImageChooserByTime)


def filter_no_sha(pairs) -> int:
    filtered = 0
    for p in pairs:
        has_sha = p['failed_build']['head_sha'] and p['passed_build']['head_sha']
        if not has_sha:
            for jp in p['jobpairs']:
                if not utils.jobpair_is_filtered(jp):
                    filtered += 1
                    jp[FILTERED_REASON_KEY] = reasons.NO_HEAD_SHA
    utils.log_filter_count(filtered, 'jobpairs that have no head SHA')
    return filtered


def filter_expired_logs(pairs) -> int:
    log.debug('Filtering jobs with expired logs.')

    MAX_UNAVAILABLE_COUNT = 5

    filtered = 0
    repo = pairs[0]['repo'] if pairs else None
    sorted_job_ids = sorted(
        [(j['job_id'], jp) for p in pairs for jp in p['jobpairs'] for j in [jp['failed_job'], jp['passed_job']]],
        reverse=True,
        key=lambda tup: tup[0])

    running_unavailable_count = 0
    for job_id, jp in sorted_job_ids:
        if utils.jobpair_is_filtered(jp):
            continue

        if running_unavailable_count == MAX_UNAVAILABLE_COUNT:
            filtered += 1
            jp[FILTERED_REASON_KEY] = reasons.NO_ORIGINAL_LOG
            continue

        orig_log_path = utils.get_orig_log_path(job_id)
        if not os.path.exists(orig_log_path) and not download_log(job_id, orig_log_path, repo=repo):
            filtered += 1
            running_unavailable_count += 1
            jp[FILTERED_REASON_KEY] = reasons.NO_ORIGINAL_LOG
        else:
            running_unavailable_count = 0

        if running_unavailable_count == MAX_UNAVAILABLE_COUNT:
            log.info(
                MAX_UNAVAILABLE_COUNT,
                'jobs in a row have unavailable logs. Assuming the rest are also unavailable.')

    utils.log_filter_count(filtered, 'jobpairs with at least one expired log')
    return filtered


def filter_logs_too_large(pairs) -> int:
    SIZE_LIMIT = 16 * 2 ** 20  # 16 MiB; largest that can be stored in a MongoDB BSON document
    SIZE_LIMIT_STR = '16 MiB'  # Just used for logging

    filtered = 0
    for p in pairs:
        for jp in p['jobpairs']:
            if utils.jobpair_is_filtered(jp):
                continue

            # Assumes the logs have already been downloaded
            failed_log_path = utils.get_orig_log_path(jp['failed_job']['job_id'])
            passed_log_path = utils.get_orig_log_path(jp['passed_job']['job_id'])

            if os.path.getsize(failed_log_path) >= SIZE_LIMIT or os.path.getsize(passed_log_path) >= SIZE_LIMIT:
                filtered += 1
                jp[FILTERED_REASON_KEY] = reasons.ORIGINAL_LOG_TOO_LARGE

    utils.log_filter_count(filtered, 'jobpairs with an original log over {} in size'.format(SIZE_LIMIT_STR))
    return filtered


def filter_non_exact_images(pairs: List) -> Tuple[int, int, int, int]:
    """
    Check if all jobs in this pair (from both the failed and passed build) used images that are available.

    If an image is found to match the job pair then it gets added to the job pair.

    This function assumes the language specified in the Travis configuration does not change between the failed and
    passed builds.

    Returns a 4-tuple of filter counts. The tuple members represent the following:
    1. The number of pairs filtered due to original log not found
    2. The number of pairs filtered due to an error reading the original log
    3. The number of pairs filtered due to no image provision timestamp in the original log
    4. The number of pairs filtered due to usage of a non-exact Docker image.
    """
    log.debug('To detect non-exact pairs, we first extract the used images from the original logs.')

    travis_images = read_json(TRAVIS_IMAGES_JSON)
    provisioned_strs = []
    for language in travis_images:
        provisioned_strs += travis_images[language].values()

    dockerhub_images = read_json(DOCKERHUB_IMAGES_JSON)
    filtered = 0
    no_original_log = 0
    error_reading_original_log = 0
    no_image_provision_timestamp = 0
    inaccessible_image = 0
    exact_jobs = 0
    images_we_have = {}
    images_we_dont_have = {}

    log.debug('Analyzing original logs to extract used images.')
    processed = 0
    for p in pairs:
        config = p['failed_build']['jobs'][0]['config']

        # Travis defaults to the Ruby image if the language is not specified.
        # See https://github.com/travis-ci/travis-ci/issues/4895.
        language = config.get('language') or 'ruby'

        # Multiple languages can be specified by using a list. In this case, we take the first language in the list.
        # We should eventually consider supporting the behavior mentioned in
        # https://stackoverflow.com/a/44054333/5007059 if it becomes officially supported.
        if isinstance(language, list):
            language = language[0]

        if language == 'java':
            language = 'jvm'

        for jp in p['jobpairs']:
            # If the job pair has already been filtered, skip it.
            if utils.jobpair_is_filtered(jp):
                continue

            jobs = [jp['failed_job'], jp['passed_job']]
            for j in jobs:
                processed += 1

                job_id = j['job_id']
                orig_log_path = utils.get_orig_log_path(job_id)
                if not os.path.exists(orig_log_path) and not download_log(job_id, orig_log_path):
                    no_original_log += 1
                    jp[FILTERED_REASON_KEY] = reasons.NO_ORIGINAL_LOG
                    continue

                # Try to find the image by timestamp. If found, add it to the job pair.
                try:
                    chooser = ExactImageChooserByTime(orig_log_path, travis_images, language)
                    orig_log_image_provision_timestamp = chooser.find_image_datetime_from_log()
                    image = chooser.get_image_tag()
                    if image is not None:
                        j[PARSED_IMAGE_TAG_KEY] = image
                except OSError:
                    # The original log file was not found.
                    error_reading_original_log += 1
                    jp[FILTERED_REASON_KEY] = reasons.ERROR_READING_ORIGINAL_LOG
                    continue

                if not orig_log_image_provision_timestamp:
                    # Jobs older than 01/2015 did not use Docker, so the build log does not contain an image provision
                    # timestamp.
                    no_image_provision_timestamp += 1
                    jp[FILTERED_REASON_KEY] = reasons.NO_IMAGE_PROVISION_TIMESTAMP
                    continue

                # Try to find image by tag. If found, add it to the job pair.
                if not image:
                    chooser = ExactImageChooserByTag(orig_log_path)
                    image = chooser.get_image_tag()
                    if image is not None:
                        j[PARSED_IMAGE_TAG_KEY] = image
                # Try to find image by GCE commit SHA. If found, add it to the job pair.
                if not image:
                    chooser = ExactImageChooserByCommitSHA(orig_log_path, dockerhub_images)
                    image = chooser.get_image_tag()
                    if image is not None:
                        j[PARSED_IMAGE_TAG_KEY] = image

                # 'tr_build_image' is the attribute containing the provision timestamp extracted from a build log.
                if orig_log_image_provision_timestamp not in provisioned_strs and image is None:
                    # This image is inaccessible.
                    inaccessible_image += 1
                    if orig_log_image_provision_timestamp not in images_we_dont_have and image is None:
                        images_we_dont_have[orig_log_image_provision_timestamp] = 1
                    else:
                        images_we_dont_have[orig_log_image_provision_timestamp] += 1
                    jp[FILTERED_REASON_KEY] = reasons.INACCESSIBLE_IMAGE
                else:
                    exact_jobs += 1
                    if orig_log_image_provision_timestamp not in images_we_have:
                        images_we_have[orig_log_image_provision_timestamp] = 1
                    else:
                        images_we_have[orig_log_image_provision_timestamp] += 1

            if utils.jobpair_is_filtered(jp):
                filtered += 1

    # Print the images we have and do not have and how many times they are used by these jobs.
    log.debug('Stats about images that we have:')
    for k in images_we_have:
        log.debug('{} jobs use an image provisioned on {}.'.format(k, images_we_have[k]))
    log.debug('Stats about images that we do not have:')
    for k in images_we_dont_have:
        log.debug('{} jobs use an unavabilable image provisioned on {}.'.format(k, images_we_dont_have[k]))
    log.debug('Total exact jobs:', exact_jobs)
    log.debug('Total non-exact jobs:', inaccessible_image)
    log.debug('Jobs with missing logs:', no_original_log)
    utils.log_filter_count(filtered, 'jobpairs that use non-exact images')
    return no_original_log, error_reading_original_log, no_image_provision_timestamp, inaccessible_image


def filter_unavailable(pairs) -> int:
    """
    A pair is unavailable if both are true:
    - the trigger or base commit of the failed or passed build is not found in the project's git log
    - the trigger commit or base commit is not archived by GitHub.
    PairFinder sets the 'resettable' and 'github_archived' attributes, which are used to check the conditions above.
    """
    filtered = 0
    for p in pairs:
        failed_build = p['failed_build']
        passed_build = p['passed_build']
        failed_build_available = failed_build['resettable'] or failed_build['github_archived']
        passed_build_available = passed_build['resettable'] or passed_build['github_archived']
        if not failed_build_available or not passed_build_available:
            for jp in p['jobpairs']:
                if not utils.jobpair_is_filtered(jp):
                    filtered += 1
                    jp[FILTERED_REASON_KEY] = reasons.NOT_AVAILABLE
    utils.log_filter_count(filtered, 'jobpairs that are unavailable')
    return filtered


def filter_same_commit(pairs) -> int:
    """
    In rare cases, pairs where the failed build and passed build have the same trigger commit can be mined in rare
    cases such as when a Travis build is manually restarted or re-triggered by a developer.
    """
    filtered = 0
    for p in pairs:
        if p['failed_build']['head_sha'] == p['passed_build']['head_sha']:
            for jp in p['jobpairs']:
                if not utils.jobpair_is_filtered(jp):
                    filtered += 1
                    jp[FILTERED_REASON_KEY] = reasons.SAME_COMMIT_PAIR
                    # For debug purposes:
                    # log.debug('Print the pairs with the same commit to investigate.')
                    # log.debug('<failed_build_id>  <pass_build_id>  <their_same_commit_sha>')
                    # log.debug(p['failed_build']['build_id'],
                    #           p['passed_build']['build_id'], p['failed_build']['head_sha'])
    utils.log_filter_count(filtered, 'jobpairs that are same-commit pairs')
    return filtered


def filter_unavailable_github_runner(pairs) -> int:
    MATRIX_VALUE_REGEX = re.compile(r'\${{\s*matrix\.([^\s}]+)\s*}}')
    SUPPORTED_RUNNERS = ['ubuntu-latest', 'ubuntu-22.04', 'ubuntu-20.04', 'ubuntu-18.04']
    filtered = 0

    for p in pairs:
        job_id_to_config = {j['job_id']: j['config'] for j in p['failed_build']['jobs'] + p['passed_build']['jobs']}
        for jp in p['jobpairs']:
            if utils.jobpair_is_filtered(jp):
                continue
            for job in (jp['failed_job'], jp['passed_job']):
                config = job_id_to_config[job['job_id']]
                runners = config['runs-on']

                if isinstance(runners, str):
                    m = re.match(MATRIX_VALUE_REGEX, runners)
                    if m and isinstance(utils.get_matrix_param(m[1], config), list):
                        runners = utils.get_matrix_param(m[1], config)
                    else:
                        runners = [runners]

                # TODO Add the ability to handle more complicated replacements.
                # According to https://docs.github.com/en/actions/learn-github-actions/contexts#context-availability,
                # jobs.<job-id>.runs-on can access the `github`, `needs`, `strategy`,
                # `matrix`, and `inputs` contexts. This only handles the `matrix` context.
                runners = [re.sub(MATRIX_VALUE_REGEX,
                                  lambda m: utils.get_matrix_param(m[1], config),
                                  runner).lower() for runner in runners]

                should_filter = False
                if 'self-hosted' in runners:
                    # TODO: determine whether the container is (1) accessible and (2) can be run on linux
                    # (use `docker manifest inspect`?)
                    should_filter = 'container' not in config or 'windows' in runners or 'macos' in runners
                else:
                    should_filter = any(runner not in SUPPORTED_RUNNERS for runner in runners)

                if should_filter:
                    jp[FILTERED_REASON_KEY] = reasons.UNAVAILABLE_RUNNER
                    filtered += 1
                    break

    utils.log_filter_count(filtered, 'jobpairs using an unsupported github actions runner')
    return filtered


def filter_unresettable_with_submodules(pairs) -> int:
    filtered = 0

    for p in pairs:
        repo = p['repo']
        for build in (p['failed_build'], p['passed_build']):
            try:
                should_be_filtered = (not build['resettable'] and build['github_archived']
                                      and utils.build_uses_submodules(repo, build))
                if should_be_filtered:
                    for jp in p['jobpairs']:
                        if not utils.jobpair_is_filtered(jp):
                            filtered += 1
                            jp[FILTERED_REASON_KEY] = reasons.UNRESETTABLE_WITH_SUBMODULES
                    break
            except KeyError as e:
                log.error('KeyError in build {}: {}'.format(build['build_id'], e))
            except RuntimeError as e:
                log.error(e)

    utils.log_filter_count(filtered, 'jobpairs for un-resettable commits with submodules')

    return filtered


def filter_unredacted_tokens(pairs) -> int:
    filtered = 0

    for p in pairs:
        redacted_job_ids = set()
        # Technically we only need to iterate the failed build, since each job in a pair has identical config,
        # but this doesn't hurt.
        for build in (p['failed_build'], p['passed_build']):
            for job in build['jobs']:
                job_id = job['job_id']

                # TODO: This does not currently search workflow-level envs.
                if utils.find_cleartext_tokens(job['config'].get('env', {}), redact=True):
                    redacted_job_ids.add(job_id)

                for step in job['config'].get('steps', []):
                    if utils.find_cleartext_tokens(step.get('env', {}), redact=True):
                        redacted_job_ids.add(job_id)
                    if utils.find_cleartext_tokens(step.get('with', {}), redact=True):
                        redacted_job_ids.add(job_id)

        for jp in p['jobpairs']:
            if not utils.jobpair_is_filtered(jp) and (
                jp['failed_job']['job_id'] in redacted_job_ids
                or jp['passed_job']['job_id'] in redacted_job_ids
            ):
                filtered += 1
                jp[FILTERED_REASON_KEY] = reasons.UNREDACTED_TOKEN

    utils.log_filter_count(filtered, 'jobpairs that seem to use cleartext tokens/passwords')
    return filtered


def filter_unsupported_workflow(pairs) -> int:
    filtered = 0

    for p in pairs:
        redacted_job_ids = set()
        # Technically we only need to iterate the failed build, since each job in a pair has identical config,
        # but this doesn't hurt.
        for build in (p['failed_build'], p['passed_build']):
            for job in build['jobs']:
                job_id = job['job_id']
                config = job['config']

                # job.env is a dictionary
                if not isinstance(config.get('env', {}), dict):
                    redacted_job_ids.add(job_id)
                    continue

                # job.defaults is a dictionary & job.defaults.run is a dictionary
                if not isinstance(config.get('defaults', {}), dict):
                    redacted_job_ids.add(job_id)
                    continue
                elif 'run' in config.get('defaults', {}) and not isinstance(config.get('defaults', {})['run'], dict):
                    redacted_job_ids.add(job_id)
                    continue

                # job.steps.env and job.steps.with are dictionaries.
                for step in job['config'].get('steps', []):
                    if not isinstance(step.get('env', {}), dict):
                        redacted_job_ids.add(job_id)
                        break
                    if not isinstance(step.get('with', {}), dict):
                        redacted_job_ids.add(job_id)
                        break

        for jp in p['jobpairs']:
            if not utils.jobpair_is_filtered(jp) and (
                jp['failed_job']['job_id'] in redacted_job_ids
                or jp['passed_job']['job_id'] in redacted_job_ids
            ):
                filtered += 1
                jp[FILTERED_REASON_KEY] = reasons.UNSUPPORTED_WORKFLOW

    utils.log_filter_count(filtered, 'jobpairs using unsupported workflow syntax')
    return filtered


def filter_first_step_not_checkout_action(pairs) -> int:
    filtered = 0

    for p in pairs:
        redacted_job_ids = set()
        for build in (p['failed_build'], p['passed_build']):
            for job in build['jobs']:
                job_id = job['job_id']
                steps = job['config'].get('steps', [])
                if len(steps) == 0:
                    redacted_job_ids.add(job_id)
                    continue

                first_step = steps[0]
                if not first_step.get('uses', '').startswith('actions/checkout'):
                    # First step is not a checkout action
                    redacted_job_ids.add(job_id)
                    continue

                if 'with' in first_step:
                    params = first_step['with']
                    if 'path' in params:
                        # The job checks out the repo at a specific path; we don't support this
                        redacted_job_ids.add(job_id)
                        continue
                    if 'repository' in params and params['repository'] != p['repo']:
                        # The first checkout action is for a repo other than the pair's repo
                        redacted_job_ids.add(job_id)
                        continue

        for jp in p['jobpairs']:
            if not utils.jobpair_is_filtered(jp) and (
                jp['failed_job']['job_id'] in redacted_job_ids
                or jp['passed_job']['job_id'] in redacted_job_ids
            ):
                filtered += 1
                jp[FILTERED_REASON_KEY] = reasons.FIRST_STEP_NOT_CHECKOUT

    utils.log_filter_count(filtered, 'jobpairs whose first step is not actions/checkout or uses unsupported params')
    return filtered


def filter_jobs_not_from_same_pr(pairs) -> int:
    """
    The GitHub Actions API does not reveal what PR a job is associated with if that PR has been
    closed. Therefore, while the Travis miner can automatically group jobs together by PR number,
    the GitHub Actions miner can only approximate that by grouping jobs from the same branch that
    were triggered by a PR. Once we have a job's log, however, we can scan through it to get its PR
    info, and ensure that the failed and passed jobs come from the same PR.
    """
    filtered = 0

    for p in pairs:
        for jp in p['jobpairs']:
            if utils.jobpair_is_filtered(jp):
                continue

            # (pr_num, base_sha, head_sha, merge_sha)
            failed_pr_data = utils.get_github_actions_pr_data(jp['failed_job']['job_id'])
            passed_pr_data = utils.get_github_actions_pr_data(jp['passed_job']['job_id'])
            f_pr_num, f_base_sha, _, f_merge_sha = failed_pr_data
            p_pr_num, p_base_sha, _, p_merge_sha = passed_pr_data

            if f_pr_num is None and p_pr_num is None:
                # Not a PR job.
                continue
            if f_pr_num != p_pr_num:
                # Jobs from different PRs! Filter the pair.
                filtered += 1
                jp[FILTERED_REASON_KEY] = reasons.JOBS_FROM_DIFFERENT_PRS
            else:
                # Jobs are from the same PR, so set the PR data for the build pair.
                # (I know this is beyond the scope of the PairFilter, but it's easiest to do this here.)
                p['pr_num'] = f_pr_num
                p['failed_build']['base_sha'] = f_base_sha
                p['passed_build']['base_sha'] = p_base_sha
                p['failed_build']['travis_merge_sha'] = f_merge_sha
                p['passed_build']['travis_merge_sha'] = p_merge_sha

    utils.log_filter_count(filtered, 'jobpairs where the failed and passed jobs are from different PRs')
    return filtered


def filter_failed_during_checkout_action(pairs) -> int:
    """
    Filters out jobpairs that failed during their checkout action. Since we handle checkouts
    manually in the GitHub Actions Reproducer, we aren't able to replicate these correctly. Plus,
    they sometimes trip up the `filter_jobs_not_from_same_pr` filter (since the checkout log is
    incomplete).
    """
    filtered = 0

    for p in pairs:
        for jp in p['jobpairs']:
            if utils.jobpair_is_filtered(jp):
                continue

            if jp['failed_step_kind'] == 'uses' and jp['failed_step_command'].startswith('actions/checkout'):
                filtered += 1
                jp[FILTERED_REASON_KEY] = reasons.JOB_FAILED_DURING_CHECKOUT

    utils.log_filter_count(filtered, 'jobpairs where the failed job failed during the checkout action')
    return filtered
