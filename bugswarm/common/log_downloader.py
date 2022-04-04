import os
import time
import urllib.request

from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from typing import List
from typing import Union
from urllib.error import URLError

from bugswarm.common import log

_DEFAULT_RETRIES = 3


def download_log(job_id: Union[str, int],
                 destination: str,
                 overwrite: bool = True,
                 retries: int = _DEFAULT_RETRIES) -> bool:
    """
    Downloads a Travis job log and stores it at destination.

    :param job_id: Travis job ID, as a string or integer, identifying a job whose log to download.
    :param destination: Path where the log should be stored.
    :param overwrite: Whether the file at `destination`, if it already exists, should be replaced.
    :param retries: The number of times to retry the log download if it fails. Defaults to 3, in which case the network
                    will be accessed up to 4 (3 + 1) times.
    :param overwrite: Whether to overwrite a file at `destination` if one already exists. If `overwrite` is False and a
                      file already exists at `destination`, FileExistsError is raised. Defaults to True.
    :raises ValueError:
    :raises FileExistsError: When a file at `destination` already exists and `overwrite` is False.
    :return: True if the download succeeded.
    """
    if not job_id:
        raise ValueError
    if not destination:
        raise ValueError
    if os.path.isfile(destination) and not overwrite:
        log.error('The log for job', job_id, 'already exists locally.')
        raise FileExistsError

    job_id = str(job_id)
    travis_log_link = 'https://api.travis-ci.org/jobs/{}/log.txt'.format(job_id)
    content = _get_log_from_url(travis_log_link, retries)

    if not content:
        travis_log_link = 'https://api.travis-ci.com/v3/job/{}/log.txt'.format(job_id)
        content = _get_log_from_url(travis_log_link, retries)
        # If this endpoint fails, the log is not on either endpoint and does not exist
        if not content:
            return False

    with open(destination, 'wb') as f:
        f.write(content)
    return True


def download_logs(job_ids: List[Union[str, int]],
                  destinations: List[str],
                  overwrite: bool = True,
                  num_workers: int = 5,
                  retries: int = _DEFAULT_RETRIES) -> bool:
    """
    Downloads one or more Travis job logs in parallel and stores them at the given destinations.
    This function calls `download_log` and raises the first exception it catches from that function, if any.

    If you only need to download a single Travis job log, use the `download_log` function.

    :param job_ids: A list of Travis job IDs, as strings or integers, identifying jobs whose logs to download.
    :param destinations: A list of paths where the logs should be stored. The path at index `i` corresponds to the log
                         downloaded for the job ID at index `i` in `job_ids`. Thus, `job_ids` and `destinations` must be
                         the same length.
    :param overwrite: Same as the argument for `download_log`.
    :param num_workers: Number of workers to download logs. Defaults to the maximum of 5.
    :param retries: Same as the argument for `download_log`.
    :raises ValueError:
    :raises FileExistsError: When a file already exists at the given destination and `overwrite` is False.
    :return: True if all downloads succeeded.
    """
    if not job_ids:
        raise ValueError
    if not destinations:
        raise ValueError
    if not len(job_ids) == len(destinations):
        log.error('The job_ids and destinations arguments must be of equal length.')
        raise ValueError

    num_workers = min(num_workers, len(job_ids))
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_job_id = {executor.submit(download_log, job_id, dst, overwrite, retries): job_id
                            for job_id, dst in zip(job_ids, destinations)}

    succeeded = 0
    for future in as_completed(future_to_job_id):
        try:
            # The result will be True if the download succeeded. Otherwise, future.result() will raise an exception or
            # return False.
            ok = future.result()
        except Exception:
            raise
        else:
            if ok:
                succeeded += 1

    return succeeded == len(job_ids)


def _get_log_from_url(log_url: str, max_retries: int, retry_count: int = 0):
    sleep_duration = 3  # Seconds.
    try:
        with urllib.request.urlopen(log_url) as url:
            result = url.read()
            log.info('Downloaded log from {}.'.format(log_url))
            return result
    except URLError as e:
        log.error('Could not download log from {}.'.format(log_url, e.reason))
        return None
    except ConnectionResetError:
        if retry_count == max_retries:
            log.warning('Could not download log from', log_url, 'after retrying', max_retries, 'times.')
            return None
        log.warning('The server reset the connection. Retrying after', sleep_duration, 'seconds.')
        time.sleep(sleep_duration)
        _get_log_from_url(log_url, max_retries, retry_count + 1)
