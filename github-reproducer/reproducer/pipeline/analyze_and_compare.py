import os

from bugswarm.common import log
from bugswarm.common.log_downloader import download_log

from reproducer.reproduce_exception import ReproduceError


def analyze_and_compare(job_dispatcher, job, run):
    """
    Analyze jobs, including those that are not reproduced (those that are missing a reproduced log most likely because
    the job encountered an error during reproducing) will still analyze the original log, so we can later insert the
    original log result into the database.
    :return boolean indicating whether the reproduced log was analyzed
    """
    analyzer = job_dispatcher.analyzer
    utils = job_dispatcher.utils

    # Analyze the original log and store the result.
    original_result, original_log_path = _get_original_result(analyzer, utils, job.job_id, job.sha, job.repo)
    job.orig_result = original_result

    # If the reproduced log does not exist, just return. # Otherwise, indicate that the job was reproduced and then
    # proceed to analyze the reproduced log and compare the result with the original log result.
    reproduced_log_path = utils.get_log_path_in_task(job, run)
    if not utils.check_if_log_exist_in_task(job, run):
        return False
    else:
        job.reproduced.value = 1

    # Analyze the reproduced log and store the result.
    reproduced_result = _get_reproduced_result(analyzer, reproduced_log_path, job.job_id, job.sha, job.repo)
    job.reproduced_result = reproduced_result

    match, mismatch_attrs = analyzer.comparer.compare_attributes(reproduced_result, original_result)
    if match:
        job.match.value = True
        log.info('Reproduced log and original log match        ({})'.format(job.job_name))
    else:
        job.match.value = False
        # Store the mismatched attributes in the job and then print the mismatched attributes.
        job.mismatch_attrs = mismatch_attrs
        log.info('Reproduced log and original log do not match ({})'.format(job.job_name))
        log.info('The original log is stored at {}.'.format(original_log_path))
        log.info('The reproduced log is stored at {}.'.format(reproduced_log_path))
        log.info('The mismatched attributes are:')
        for m in mismatch_attrs:
            attr_reproduced = m['reproduced'][:30] if len(str(m['reproduced'])) > 30 else m['reproduced']
            attr_original = m['orig'][:30] if len(str(m['orig'])) > 30 else m['orig']
            compare_string = '(original, reproduced) = ({}, {})'.format(attr_original, attr_reproduced)
            log.info('  {:<40}{}'.format(m['attr'], compare_string))
    return True


def _get_original_result(analyzer, utils, job_id, trigger_sha, repo):
    original_log_path = utils.get_orig_log_path(job_id)

    # If the original log does not exist in the expected location, try to download it to that location. If the log
    # cannot be downloaded, return error.
    if not os.path.isfile(original_log_path):
        log.debug('Original log not found at {}.'.format(original_log_path))
        log.info('Download original log.')
        if not download_log(job_id, original_log_path, repo=repo):
            log.info('Could not download original log.')
            return None, original_log_path

    original_result = analyzer.analyze_single_log(original_log_path, job_id, trigger_sha=trigger_sha, repo=repo)
    if original_result.get('not_in_supported_language') is True:
        raise ReproduceError('Original log was not generated from a job in a supported programming language. '
                             'The primary language was "{}."'.format(original_result['primary_language']))
    return original_result, original_log_path


def _get_reproduced_result(analyzer, reproduced_log_path, job_id, trigger_sha, repo):
    reproduced_result = analyzer.analyze_single_log(reproduced_log_path, job_id, trigger_sha=trigger_sha, repo=repo)
    if reproduced_result.get('not_in_supported_language') is True:
        raise ReproduceError('Reproduced log was not generated from a job in a supported programming language. '
                             'The primary language was "{}."'.format(reproduced_result['primary_language']))
    return reproduced_result
