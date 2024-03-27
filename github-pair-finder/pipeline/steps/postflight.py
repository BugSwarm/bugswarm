import shutil

from bugswarm.common import log

from .. import utils


class Postflight:
    def process(self, data, context):
        repo = context['repo']
        keep_clone = context['keep_clone']

        if keep_clone is False:
            log.info('Removing repo clone...')
            shutil.rmtree(utils.repo_clone_path(repo), ignore_errors=True)

        return data
