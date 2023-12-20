#
# Copyright 2016 iXsystems, Inc.
# All rights reserved
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted providing that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#####################################################################

import os

import requests

from bugswarm.common import log

from reproducer.reproduce_exception import DockerHubError


class DockerHub(object):
    def __init__(self, url=None, version='v2'):
        self.version = version
        self.url = '{0}/{1}'.format(url or 'https://hub.docker.com', self.version)
        self._session = requests.Session()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._session.close()

    def image_exists(self, name, tag):
        err, res = self.get_tag(name, tag)
        return err, res

    def get_tag_list(self, repo):
        log.debug('Getting tag list for {}.'.format(repo))
        tags = {}
        for item in self.get_tags(repo):
            tags[item['name']] = 0
        log.debug('Done getting tag list of', len(tags), 'tags.')
        return tags

    def _get(self, address, **kwargs):
        try:
            resp = self._session.get(address, params=kwargs)
        except requests.exceptions.Timeout as e:
            raise DockerHubError('Connection Timeout. Download failed due to: {!r}'.format(e))
        except requests.exceptions.RequestException as e:
            raise DockerHubError('Connection Error. Download failed due to: {!r}'.format(e))
        else:
            return resp

    def _get_item(self, name, subitem=''):
        user = 'library'
        if '/' in name:
            user, name = name.split('/', 1)
        resp = self._get(
            os.path.join(self.api_url('repositories/{0}/{1}'.format(user, name)), subitem + '?page_size=10000'))
        code = resp.status_code
        if code == 200:
            j = resp.json()
            return 0, j
        elif code == 404:
            log.debug('Item does not exist on Docker Hub.')
            return 0, None
            # raise ValueError('{0} repository does not exist'.format(name))
        else:
            log.debug('Error when getting item in Docker Hub wrapper.')
            return 1, None
            # raise ConnectionError('{0} download failed: {1}'.format(name, code))

    def _iter_item(self, url, **kwargs):
        next_link = url
        while next_link:
            response = self._get(next_link)
            result = response.json()
            for i in result['results']:
                yield i
            next_link = result.get('next')

    def api_url(self, path):
        return '{0}/{1}/'.format(self.url, path)

    def get_tag(self, name, tag):
        return self._get_item(name, 'tags/{0}'.format(tag))

    def get_tags(self, name):
        return self._iter_item(self.api_url('repositories/{0}/tags'.format(name)))
