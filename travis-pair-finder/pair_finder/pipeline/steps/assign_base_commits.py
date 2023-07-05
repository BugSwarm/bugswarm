import time

from typing import Any
from typing import Optional

from bugswarm.common import log

from .step import Step
from .step import StepException


class AssignBaseCommits(Step):
    @staticmethod
    def print_helpful_links_for_debugging(repo, commit, branch, b):
        log.debug('PR :', branch.pr_num, ' base branch=', branch.base_branch)
        log.debug('https://api.github.com/repos/' + repo + '/commits/' + commit)
        log.debug('https://api.travis-ci.org/builds/' + str(b.build_id))
        log.debug('https://api.github.com/repos/' + repo + '/pulls/' + str(branch.pr_num) + '/commits')
        log.debug('https://github.com/' + repo + '/pull/' + str(branch.pr_num) + '/commits')

    @staticmethod
    def is_sha_in_pr(sha, branches):
        for _, branch_obj in branches.items():
            if sha in branch_obj.html_commits:
                return branch_obj

    @staticmethod
    def assign_base_commit(repo, utils, shas, b, branches, branch):
        parent_shas = utils.get_parents_of_commit(repo, b.trigger_commit, branch.base_branch)
        parent_shas = parent_shas.split('\n')

        for sha in shas:
            if b.trigger_commit not in shas:
                log.error('Trigger commit not in SHAs!')
                raise StepException
            if sha not in shas:
                log.error('Parent commit not in SHAs!')
                raise StepException

            if shas[sha] >= shas[b.trigger_commit]:
                continue
            branch_containing_sha = AssignBaseCommits.is_sha_in_pr(branches)
            if branch_containing_sha:
                if branch_containing_sha.merged_at:
                    if utils.convert_api_date_to_datetime(branch_containing_sha.merged_at) >= shas[b.trigger_commit]:
                        log.debug(sha, 'excluded because PR merged later', branch_containing_sha.branch_name)
                        continue
                else:
                    log.debug(sha, 'excluded because PR not merged', branch_containing_sha.branch_name)
                    continue

            # Before assigning the base SHA, check if it is on the branch from which the pull request is branched.
            result = utils.get_branch_of_sha(repo, sha)
            if not result:
                log.debug(sha, 'excluded because no branch name.')
                continue

            if len(result) > 2:
                branch_name = result[2:]
                if branch_name != branch.base_branch:
                    log.debug(sha, 'excluded because base branch name does not match.')
                    continue
            return sha

    def process(self, data: Any, context: dict) -> Optional[Any]:
        log.info('Assigning base commits.')
        # Uncomment repo and utils to use the commented debug code below.
        # repo = context['repo']
        # utils = context['utils']
        shas = context['shas']
        branches = data
        pr_pairs_resettable = 0
        pr_builds_found_base = 0
        incorrect_base = 0
        start_time = time.time()
        new_correct_base = 0
        old_sha_correct = 0
        for _, branch_obj in branches.items():
            if not branch_obj.pairs:
                continue
            for pair in branch_obj.pairs:
                builds = [pair.failed_build, pair.passed_build]
                for b in builds:
                    if branch_obj.pr_num != -1:
                        # ------------------------------------------------------------
                        # This code is commented out because we are only using
                        # travistorrent approach for now and the base commit is
                        # already set in assign trigger commit (see
                        # travistorrent_approach() in assign_trigger_commit.py).
                        # ------------------------------------------------------------
                        # if b.base_commit and b.resettable:
                        #     old_base_commit = utils.get_pr_commit_base(
                        #         repo, b.trigger_commit, branch_obj.base_branch, b.committed_at)
                        #     if old_base_commit != b.base_commit:
                        #         incorrect_base += 1
                        #         # log.debug('old base commit incorrect')
                        #         # log.debug('pr base sha=', branch_obj.pr_info['base']['sha'])
                        #         new_base_commit = AssignBaseCommits.assign_base_commit(
                        #             repo, utils, shas, b, branches, branch_obj)
                        #         # log.debug('trigger:', b.trigger_commit, 'old:', old_base_commit, 'actual:',
                        #         #           b.base_commit, 'new:', new_base_commit)
                        #         if not new_base_commit:
                        #             log.debug('ERROR didnt find a base commit!')
                        #             continue
                        #
                        #         if new_base_commit != b.base_commit:
                        #             # call assign base commit again and have the debug parameter on
                        #             AssignBaseCommits.assign_base_commit(
                        #                 repo, utils, shas, b, branches, branch_obj, True)
                        #             log.debug('virtual commit', b.commit)
                        #             log.debug('trigger datetime     ', shas[b.trigger_commit], b.trigger_commit)
                        #             log.debug('old base datetime    ', shas[old_base_commit], old_base_commit)
                        #             log.debug('new base datetime    ', shas[new_base_commit], new_base_commit)
                        #             log.debug('actual base datetime ', shas[b.base_commit], b.base_commit)
                        #             AssignBaseCommits.print_helpful_links_for_debugging(
                        #                 repo, b.trigger_commit, branch_obj, b)
                        #             # raise StepException
                        #         else:
                        #             new_correct_base += 1
                        #     else:
                        #         old_sha_correct += 1
                        #         log.debug('base sha actually matched!')

                        if b.base_commit:
                            pr_builds_found_base += 1

                    if b.base_commit and b.resettable:
                        if b.base_commit in shas:
                            b.resettable = True
                        else:
                            log.critical('Have base but why not in git log?')
                            b.resettable = False
                            # AssignBaseCommits.print_helpful_links_for_debugging(repo, b.trigger_commit, branch_obj, b)

        # Preare to print some stats.
        pr_builds_have_base_but_not_resettable = 0
        pr_pairs_found_base = 0
        for _, branch_obj in data.items():
            if not branch_obj.pairs:
                continue
            for pair in branch_obj.pairs:
                builds = [pair.failed_build, pair.passed_build]
                if branch_obj.pr_num != -1:
                    if builds[0].resettable and builds[1].resettable:
                        pr_pairs_resettable += 1

                    if builds[0].base_commit and builds[1].base_commit:
                        pr_pairs_found_base += 1

                    for b in builds:
                        if b.base_commit and not b.resettable:
                            pr_builds_have_base_but_not_resettable += 1

        log.debug('pr_builds_found_base =', pr_builds_found_base)
        log.debug('pr_pairs_found_base =', pr_pairs_found_base)
        log.debug('pr_builds_have_base_but_not_resettable =', pr_builds_have_base_but_not_resettable)
        log.debug('pr_pair both resettable', pr_pairs_resettable)
        log.debug('Assigning base commits in', time.time() - start_time, 'seconds.')
        log.debug('old correct =', old_sha_correct,
                  'old incorrect =', incorrect_base,
                  'newly corrected =', new_correct_base)
        return data
