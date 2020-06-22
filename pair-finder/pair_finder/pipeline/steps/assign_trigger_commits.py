import re
import time
import requests

from typing import Any
from typing import Optional

from bugswarm.common import log

from .step import Step
from .step import StepException


class AssignTriggerCommits(Step):
    @staticmethod
    def find_trigger_commit_by_matching_datetime(repo, utils, commits_with_same_datetime, b, checked_commits):
        if len(commits_with_same_datetime) == 1:
            b.trigger_commit = commits_with_same_datetime[0]
            log.debug('found trigger by matching datetime')
        elif len(commits_with_same_datetime) > 1:
            log.debug('Multiple commits with same datetime.')
            log.debug(commits_with_same_datetime)
            for commit in commits_with_same_datetime:
                checked_commits.append(commit)
                trigger_commit = utils.github.get_build_trigger(repo, commit, b.build_id)
                if trigger_commit:
                    b.trigger_commit = trigger_commit
                    log.debug('found trigger by matching build id')
                    break

    @staticmethod
    def check_how_many_more_commits_from_ght(branches):
        total_commits_from_html = 0
        total_commits_from_ght = 0
        total_new_commits_from_ght = 0
        for _, branch_obj in branches.items():
            if not branch_obj.pairs:
                continue
            total_commits_from_html += len(branch_obj.html_commits)
            total_commits_from_ght += len(branch_obj.ght_commits)
            total_new_commits_from_ght += len([c for c in branch_obj.ght_commits if c['sha'] not in
                                               branch_obj.html_commits])
        log.debug('total_commits_from_html =', total_commits_from_html)
        log.debug('total_commits_from_ght =', total_commits_from_ght)
        log.debug('total_new_commits_from_ght =', total_new_commits_from_ght)

    @staticmethod
    def print_helpful_links_for_debugging(repo, commit, branch, b):
        log.debug('PR:', branch.pr_num, 'base branch =', branch.base_branch)
        log.debug('https://api.github.com/repos/' + repo + '/commits/' + commit + '/status')
        log.debug('https://api.travis-ci.org/builds/' + str(b.build_id))
        log.debug('https://api.github.com/repos/' + repo + '/pulls/' + str(branch.pr_num) + '/commits')
        log.debug('https://github.com/' + repo + '/pull/' + str(branch.pr_num) + '/commits')

    @staticmethod
    def base_approach(branch, b):
        # Base approach: See if build_id is in Github API commits, see 'download_pr_commits' to know where
        # github_commits come from.
        for commit in branch.github_commits:
            if str(b.build_id) in commit['build_ids']:
                b.trigger_commit = commit['sha']
                # Return the sha for debug purposes.
                return commit['sha']

    @staticmethod
    def html_approach(branch, b):
        # HTML approach to get trigger commits.
        for commit in branch.html_commits:
            if str(b.build_id) in branch.html_commits[commit]:
                b.trigger_commit = commit
                return commit

    @staticmethod
    def travistorrent_approach(b):
        if b.virtual_commit_info:
            try:
                match = re.search(r'Merge (.*) into (.*)', b.virtual_commit_info['commit']['message'], re.M)
                if match and len(match.groups()) == 2:
                    b.trigger_commit = match.group(1)
                    b.base_commit = match.group(2)
                    return b.trigger_commit
            except TypeError:
                log.error('Encountered a TypeError in travistorrent_approach.')
                log.error(b.virtual_commit_info)
                raise StepException

    @staticmethod
    def fill_more_trigger_from_ght(utils, repo, branch, b):
        # Try to fill more trigger commits from GHT commits.
        if not b.trigger_commit:
            for c in branch.ght_commits:
                if c['sha'] not in branch.html_commits:
                    if utils.github.is_commit_associated_with_build(repo, c['sha'], b.build_id):
                        b.trigger_commit = c['sha']
                        print('found trigger with GHT commit!')
                        return c['sha']

    @staticmethod
    def debug_when(branch, b, repo, utils):
        # DEBUG when matching committer date gets more result than HTML approach
        commits_with_same_datetime = [commit['sha'] for commit in branch.github_commits if
                                      commit['commit']['committer']['date'] == b.committed_at]
        # AssignTriggerCommits.find_trigger_commit_by_matching_datetime(repo, utils, commits_with_same_datetime, b,
        #                                                               checked_commits)
        if not b.trigger_commit and commits_with_same_datetime:
            b.trigger_commit = 'mock'
            print('why got matching committer date but did not find trigger from from html?',
                  len(commits_with_same_datetime),
                  commits_with_same_datetime[0])
            for c in commits_with_same_datetime:
                if utils.github.is_commit_associated_with_build(repo, c, b.build_id):
                    log.warning('this commit is confirmed to be the trigger but it didnt show up in HTML.')
                    AssignTriggerCommits.print_helpful_links_for_debugging(repo, c, branch, b)
                    utils.github.get_pr_commits_by_html(repo, str(branch.pr_num), branch)
                    for commit in branch.html_commits:
                        if str(b.build_id) == branch.html_commits[commit]:
                            log.debug('Tried again and found the commit in HTML this time.')
                    break

    @staticmethod
    def is_github_archived(repo, sha):
        url = 'https://github.com/{}/commit/{}'.format(repo, sha)
        try:
            return requests.head(url).status_code != 404
        except requests.exceptions.RequestException:
            log.error('Encountered an error while checking GitHub commit archive.')
            raise StepException

    def process(self, data: Any, context: dict) -> Optional[Any]:
        log.info('Assigning trigger commits.')
        # Uncomment repo and utils to use the commented debug code below.
        repo = context['repo']
        # utils = context['utils']
        shas = context['shas']

        branches = data

        non_pr_pairs = 0
        pr_pairs = 0
        non_pr_pairs_resettable = 0
        pr_pairs_resettable = 0
        pr_builds_found_trigger = 0
        pr_builds = 0
        # AssignTriggerCommits.check_how_many_more_commits_from_ght(branches)
        start_time = time.time()
        for _, branch_obj in branches.items():
            if not branch_obj.pairs:
                continue
            for pair in branch_obj.pairs:
                builds = [pair.failed_build, pair.passed_build]
                # log.info('Looking for trigger commits for builds', b1, b2)

                for b in builds:
                    # if its non-PR branch_obj, we do not need to resolve further for trigger commit
                    if branch_obj.pr_num == -1:
                        b.trigger_commit = b.commit
                    # if its PR branch_obj, we need to resolve for trigger commit
                    else:
                        pr_builds += 1

                        # travistorrent approach
                        AssignTriggerCommits.travistorrent_approach(b)
                        # found_trigger_from_github = AssignTriggerCommits.base_approach(branch_obj, b)
                        # found_trigger_from_html = AssignTriggerCommits.html_approach(branch_obj, b)
                        # if AssignTriggerCommits.fill_more_trigger_from_ght(utils, repo, branch_obj, b):
                        #     pr_pairs_trigger_from_ght += 1

                        # This code helps evaluate and debug the approaches.
                        # if found_trigger_from_github and not found_trigger_from_html:
                        #     # if not utils.github.is_commit_associated_with_build(repo, ccc, b.build_id):
                        #     log.debug('found from github but didnt find from html')
                        #     AssignTriggerCommits.print_helpful_links_for_debugging(repo, ccc, branch_obj, b)
                        #     utils.github.get_pr_commits_by_html(repo, str(branch_obj.pr_num), branch_obj)
                        #     for commit in branch_obj.html_commits:
                        #         if str(b.build_id) in branch_obj.html_commits[commit]:
                        #             log.debug('tried again, found the commit in html this time')

                        # DEBUG - to check if there's any case where we found trigger from HTML but didnt find
                        # from the base approach (ie. from Github API result)
                        # if found_trigger_from_html and not found_trigger_from_github:
                        #     log.debug('found trigger from HTML but didnt find from github!')
                        #     log.debug('sha is =', found_trigger_from_html)
                        #     AssignTriggerCommits.print_helpful_links_for_debugging(
                        #         repo, found_trigger_from_html, branch_obj, b)
                        #     if utils.github.is_commit_associated_with_build(
                        #             repo, found_trigger_from_html, b.build_id):
                        #         log.debug('\t\ttried again, found trigger from github this time.')

                        if b.trigger_commit:
                            pr_builds_found_trigger += 1

                    if b.trigger_commit:
                        if b.trigger_commit in shas:
                            b.resettable = True
                        else:
                            pass
                            # print('have trigger but why not in git log?')
                            # AssignTriggerCommits.print_helpful_links_for_debugging(repo, b.trigger_commit,
                            # branch_obj, b)

                    if b.commit:
                        b.github_archived = AssignTriggerCommits.is_github_archived(repo, b.commit)

        # Preare to print some stats.
        pr_pairs_only_1_resettable = 0
        pr_builds_have_trigger_but_not_resettable = 0
        pr_pairs_found_trigger = 0
        for _, branch_obj in branches.items():
            if not branch_obj.pairs:
                continue
            for pair in branch_obj.pairs:
                builds = [pair.failed_build, pair.passed_build]

                if branch_obj.pr_num == -1:
                    non_pr_pairs += 1
                    if builds[0].resettable and builds[1].resettable:
                        non_pr_pairs_resettable += 1
                else:
                    pr_pairs += 1
                    if builds[0].resettable and builds[1].resettable:
                        pr_pairs_resettable += 1

                    if builds[0].trigger_commit and builds[1].trigger_commit:
                        pr_pairs_found_trigger += 1

                    if len([b for b in builds if b.resettable]) == 1:
                        pr_pairs_only_1_resettable += 1

                    for b in builds:
                        if b.trigger_commit and not b.resettable:
                            pr_builds_have_trigger_but_not_resettable += 1

        log.debug('non pr pairs resettable = %d/%d' % (non_pr_pairs_resettable, non_pr_pairs))
        log.debug('pr_builds_found_trigger = %d/%d' % (pr_builds_found_trigger, pr_builds))
        log.debug('pr_pairs_found_trigger = %d/%d' % (pr_pairs_found_trigger, pr_pairs))
        log.debug('pr_pair both resettable = %d/%d' % (pr_pairs_resettable, pr_pairs))
        # log.debug('pr_pairs_trigger_from_ght =', pr_pairs_trigger_from_ght)
        log.debug('pr_builds_have_trigger_but_not_resettable =', pr_builds_have_trigger_but_not_resettable)
        log.debug('pr_pairs_only_1_build_resettable =', pr_pairs_only_1_resettable)
        log.debug('Assigned trigger commits in', time.time() - start_time, 'seconds.')
        return data
