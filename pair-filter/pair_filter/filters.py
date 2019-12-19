from typing import List
from typing import Tuple

from bugswarm.common import log
from bugswarm.common.json import read_json
from bugswarm.common.log_downloader import download_log
from bugswarm.common import filter_reasons as reasons

from . import utils
from .constants import FILTERED_REASON_KEY
from .constants import PARSED_IMAGE_TAG_KEY
from .constants import TRAVIS_IMAGES_JSON
from .constants import DOCKERHUB_IMAGES_JSON
from .image_chooser import ExactImageChooserByTime
from .image_chooser import ExactImageChooserByTag
from .image_chooser import ExactImageChooserByCommitSHA


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
                if not download_log(job_id, orig_log_path):
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
