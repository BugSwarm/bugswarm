# Almost entirely copied from the Travis pipeline.

import os
import signal
import time

from typing import Any
from typing import Optional

from bugswarm.common import log
from bugswarm.common.credentials import GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper

# from utils import Utils


class CleanPairs:
    @staticmethod
    def print_helpful_links_for_debugging(repo, commit, branch, b):
        log.debug('PR:', branch.pr_num, 'base branch =', branch.base_branch)
        log.debug('https://api.github.com/repos/' + repo + '/commits/' + commit + '/status')
        log.debug('https://api.travis-ci.org/builds/' + str(b.build_id))
        log.debug('https://api.github.com/repos/' + repo +
                  '/pulls/' + str(branch.pr_num) + '/commits')
        log.debug('https://github.com/' + repo + '/pull/' + str(branch.pr_num) + '/commits')

    def process(self, data: Any, context: dict) -> Optional[Any]:
        """
        Perform last-second checks on the pairs. This step is meant specifically to annotate pairs for exclusion from
        the output. So before adding another pair-annotating loop to this step, consider adding a new pipeline step to
        contain your annotation logic.

        However, this step would be the appropriate place to perform sanity checks for invariants, since CleanPairs
        should always be the last step (besides Postflight) in the pipeline.

        This pipeline step also performs two checks to determine which pairs should be excluded from the output:
          1. Check for and exclude pairs with errored builds are not actually errored. Pairs marked as not actually
             errored will be excluded from the output. See output_manager.py.
          2. Check for and exclude pairs where the two builds have the same trigger commit.
             - These same-commit pairs are mined in cases when a Travis build is manually restarted or re-triggered
               by a developer. Which, from our observations, happens very rarely. In these cases, Travis does not
               increment the build number but does increment the build ID.
             - We exclude same-commit pairs because, since the trigger commits are the same, there must be no source
               code changes between the failed or errored build and the passed build. (The second build must have passed
               due to some change outside of the repository.)
             - Another reason to exclude these pairs is that Reproducer should not be able to reproduce the failed or
               errored build since the "broken" and fixed states of the repository for this pair are the same. So we
               might as well exclude the pair now and prevent wasted time in the Reproducer.

        This pipeline step also attaches the following properties to the pairs:
          - repo_mined_version
        """
        repo = context['repo']
        branches = data
        excluded_pairs = 0

        log.info('Excluding same-commit pairs.')
        same_commit_pairs = 0
        for _, branch_obj in branches.items():
            if not branch_obj.pairs:
                continue
            for pair in branch_obj.pairs:
                f_commit = pair.failed_build.commit
                p_commit = pair.passed_build.commit
                if f_commit and p_commit and f_commit == p_commit:
                    pair.exclude_from_output = True
                    same_commit_pairs += 1
                    excluded_pairs += 1

        log.debug('same-commit pairs:', same_commit_pairs)
        log.debug('excluded pairs:', excluded_pairs)

        # latest_commit = Utils.get_latest_commit_for_repo(repo)
        gh = context['github_api']
        latest_commit = gh.get('https://api.github.com/repos/{}/commits'.format(repo))[1][0]['sha']
        for _, branch_obj in branches.items():
            if not branch_obj.pairs:
                continue
            for pair in branch_obj.pairs:
                pair.repo_mined_version = latest_commit

        # Sanity check for invariants:
        # 1. The failed build ID is less than the passed build ID.
        # 2. The failed build and passed build have the same branch name. (Do not check branch IDs since those must be
        #    the same by construction.)
        # The second invariant is always true by construction, so we actually only check the first invariant.
        # If either invariant does not hold, exit the entire parent process. Do
        # not pass Go. Do not change the database.
        for _, branch_obj in branches.items():
            for pair in branch_obj.pairs:
                if int(pair.failed_build.build_id) >= int(pair.passed_build.build_id):
                    log.error('Invariant violation detected: '
                              'pair.failed_build.build_id < pair.passed_build.build_id is false: '
                              'failed build: {}, passed build: {}'
                              .format(pair.failed_build, pair.passed_build))
                    os.kill(os.getpid(), signal.SIGINT)
                    # Sleep to make sure we receive the signal.
                    time.sleep(2)

        return data
