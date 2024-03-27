import git
import requests

from bugswarm.common import log
from bugswarm.common.credentials import GITHUB_TOKENS

from .. import utils


class CheckBuildIsResettable:
    def process(self, build_groups, context):
        repo = context['repo']
        repo_clone_path = utils.repo_clone_path(repo)
        repo_obj = git.Repo(repo_clone_path)

        session = requests.session()
        session.headers = {'Authorization': 'token {}'.format(GITHUB_TOKENS[0])}

        shas_tested = dict()

        log.info('Checking if builds are resettable and/or archived')
        for group in build_groups.values():
            for pair in group.pairs:
                for build in [pair.failed_build, pair.passed_build]:
                    # If we've already tried to fetch this commit, use that result
                    # Otherwise, see whether fetching the commit results in an error & cache the result
                    if build.commit in shas_tested:
                        build.resettable = shas_tested[build.commit]
                    else:
                        try:
                            repo_obj.remote().fetch(build.commit)
                        except git.GitCommandError:
                            build.resettable = False
                        else:
                            build.resettable = True
                        shas_tested[build.commit] = build.resettable

                    # Check that the given SHA doesn't result in a github 404
                    response = session.head('https://github.com/{}/commit/{}'.format(repo, build.commit))
                    build.github_archived = response.status_code != 404

        return build_groups
