import time

import cachecontrol
import requests

from bugswarm.common import log

_BASE_URL = 'https://api.travis-ci.org'
# Number of seconds to sleep before retrying. Five seconds has been long enough to obey the Travis API rate limit.
_SLEEP_SECONDS = 5
_MAX_SLEEP_SECONDS = 60 * 5  # 5 minutes.


class TravisWrapper(object):
    def __init__(self):
        self._session = cachecontrol.CacheControl(requests.Session())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()

    def _close(self):
        self._session.close()

    # Potentially raises requests.exceptions.Timeout or requests.exceptions.RequestException.
    def _get(self, address, **kwargs):
        sleep_seconds = _SLEEP_SECONDS
        while True:
            response = self._session.get(address, params=kwargs)
            code = response.status_code
            if code == 200:
                return response.json()
            elif code == 404:
                log.error('Get request for {} returned 404 Not Found.'.format(address))
                response.raise_for_status()
            elif code == 429:
                log.warning(
                    'The Travis API returned status code 429 Too Many Requests. '
                    'Retrying after sleeping for {} seconds.'.format(sleep_seconds))
                time.sleep(sleep_seconds)
                sleep_seconds = min(sleep_seconds * 2, _MAX_SLEEP_SECONDS)
            else:
                log.error('Get request for {} returned {}.'.format(address, code))
                raise requests.exceptions.ConnectionError('{} download failed. Error code is {}.'.format(address, code))

    def _get_iterate(self, address, **kwargs):
        after_number = None
        result = self._get(address, **kwargs)
        while True:
            if after_number:
                result = self._get(address, after_number=after_number)
            if not result:
                return
            yield from result
            after_number = result[-1]['number']
            if after_number == '1':
                return

    @staticmethod
    def _endpoint(path):
        return '{}/{}'.format(_BASE_URL, path)

    def search(self, term):
        return self._get_iterate(TravisWrapper._endpoint('search/repositories'), query=term)

    def get_builds_for_repo(self, repo):
        return self._get_iterate(TravisWrapper._endpoint('repositories/{}/builds'.format(repo)))

    def get_build_info(self, build_id):
        return self._get(TravisWrapper._endpoint('builds/{}'.format(build_id)))

    def get_job_info(self, job_id):
        return self._get(TravisWrapper._endpoint('jobs/{}'.format(job_id)))
