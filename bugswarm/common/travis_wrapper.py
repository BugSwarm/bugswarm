import time
from collections import deque

import cachecontrol
import requests

from bugswarm.common import log
from bugswarm.common import credentials

_BASE_URL = 'https://api.travis-ci.com'
# Number of seconds to sleep before retrying. Five seconds has been long enough to obey the Travis API rate limit.
_SLEEP_SECONDS = 5
_TOKENS = deque(credentials.TRAVIS_TOKENS)


class TravisWrapper(object):
    def __init__(self):
        self._session = cachecontrol.CacheControl(requests.Session())
        if credentials.TRAVIS_TOKENS:
            if not isinstance(credentials.TRAVIS_TOKENS, list):
                raise TypeError('TRAVIS_TOKENS must be a list.')
            if not all(isinstance(t, str) for t in credentials.TRAVIS_TOKENS):
                raise ValueError('All Travis CI Tokens must be given as strings.')

            # Start with the first token in TRAVIS_TOKENS list and pop() element from right and append to front
            # In the case where we are using 2 or more threads, each thread will grab the next token in the list
            self._session.headers['Authorization'] = 'token {}'.format(_TOKENS[0])
            _TOKENS.appendleft(_TOKENS.pop())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()

    def _close(self):
        self._session.close()

    # Potentially raises requests.exceptions.Timeout or requests.exceptions.RequestException.
    def _get(self, address, **kwargs):
        sleep_seconds = _SLEEP_SECONDS
        attempts = 0
        while True:
            response = self._session.get(address, params=kwargs)
            code = response.status_code
            if code == 200:
                return response.json()
            elif code == 404:
                log.error('Get request for {} returned 404 Not Found.'.format(address))
                response.raise_for_status()
            elif code == 403:
                # Token did not successfully authorize, try next one in list
                # deque.pop() removes element from the right so we appendleft()
                self._session.headers['Authorization'] = 'token {}'.format(_TOKENS[0])
                _TOKENS.appendleft(_TOKENS.pop())
            elif code == 429:
                if attempts < 1 or not _TOKENS:
                    log.warning(
                        'The Travis API returned status code 429 Too Many Requests. '
                        'Retrying after sleeping for {} seconds.'.format(sleep_seconds))
                    time.sleep(sleep_seconds)
                    attempts += 1
                else:
                    # Use another token if # of attempts for GET Requests >= 1, will use next token in list
                    self._session.headers['Authorization'] = 'token {}'.format(_TOKENS[0])
                    _TOKENS.appendleft(_TOKENS.pop())
            else:
                log.error('Get request for {} returned {}.'.format(address, code))
                raise requests.exceptions.ConnectionError('{} download failed. Error code is {}.'.format(address, code))

    def _get_iterate(self, address, **kwargs):
        after_number = None
        build_number_exists = False
        if 'last_build_number' in kwargs:
            build_number = kwargs['last_build_number']
            build_number_exists = True
        result = self._get(address, **kwargs)
        latest_result_build_number = result[0]['number']
        if build_number_exists:
            if int(latest_result_build_number) == build_number:
                return
        while True:
            if after_number:
                if build_number_exists and int(after_number) < build_number:
                    return
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

    def get_builds_for_repo(self, repo, build_number=None):
        if build_number:
            return self._get_iterate(TravisWrapper._endpoint('repositories/{}/builds'.format(repo)),
                                     last_build_number=build_number)
        return self._get_iterate(TravisWrapper._endpoint('repositories/{}/builds'.format(repo)))

    def get_build_info(self, build_id):
        return self._get(TravisWrapper._endpoint('builds/{}'.format(build_id)))

    def get_job_info(self, job_id):
        return self._get(TravisWrapper._endpoint('jobs/{}'.format(job_id)))
