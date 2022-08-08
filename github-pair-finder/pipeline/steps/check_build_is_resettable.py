import requests

from bugswarm.common import log
from bugswarm.common.credentials import GITHUB_TOKENS


class CheckBuildIsResettable:
    def process(self, build_groups, context):
        repo = context['repo']
        session = requests.session()
        session.headers = {'Authorization': 'token {}'.format(GITHUB_TOKENS[0])}

        log.info('Checking if builds are resettable and/or archived')
        for group in build_groups.values():
            for pair in group.pairs:
                for build in [pair.failed_build, pair.passed_build]:
                    build.resettable = build.commit in context['shas']
                    response = session.head('https://github.com/{}/commit/{}'.format(repo, build.commit))
                    build.github_archived = response.status_code != 404

        return build_groups
