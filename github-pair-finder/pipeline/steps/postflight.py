import shutil

from bugswarm.common import log


class Postflight:
    def process(self, data, context):
        repo = context['repo']
        keep_clone = context['keep_clone']

        if keep_clone is False:
            log.info('Removing repo clone...')
            shutil.rmtree('intermediates/repos/{}'.format(repo.replace('/', '-')), ignore_errors=True)

        return data
