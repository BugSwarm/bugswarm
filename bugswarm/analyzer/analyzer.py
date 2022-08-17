import pprint

from .dispatcher import Dispatcher
from .result_comparer import ResultComparer

LOAD_JSON = 1


class Analyzer(object):
    def __init__(self):
        self.dispatcher = Dispatcher()
        self.comparer = ResultComparer()

    def analyze_single_log(self, log_path, job_id, build_system=None, trigger_sha=None, repo=None, print_result=False,
                           mining=True):
        """
        When mining is True and build_system is None, Analyzer will get build system from Travis and GitHub API.
        Otherwise, Analyzer will get build_system from BugSwarm API.
        """
        if not mining and not build_system:
            # Not in mining mode, and we don't have build_system.
            build_system = self.dispatcher.get_build_system_from_bugswarm_database(job_id)

        result = self.dispatcher.analyze(log_path, job_id, build_system, trigger_sha, repo)
        if print_result:
            pprint.pprint(result)

        return result

    def compare_single_log(self, reproduced, orig, job_id, build_system=None, trigger_sha=None, repo=None,
                           print_result=False, mining=True):
        if not mining and not build_system:
            # Not in mining mode, and we don't have build_system.
            build_system = self.dispatcher.get_build_system_from_bugswarm_database(job_id)

        reproduced_result = self.dispatcher.analyze(reproduced, job_id, build_system, trigger_sha, repo)
        original_result = self.dispatcher.analyze(orig, job_id, build_system, trigger_sha, repo)
        match, mismatched_attributes = ResultComparer.compare_attributes(reproduced_result, original_result)
        if print_result:
            pprint.pprint(match)
            pprint.pprint(mismatched_attributes)

        return match, mismatched_attributes

    def force_re_analyze_travis_log(self, orig, job_id, build_system=None, trigger_sha=None, repo=None,
                                    print_result=False, mining=True):
        print('the orig log was not determined as Java: ', orig)
        print('force analyze as Java log')

        if not mining and not build_system:
            # Not in mining mode, and we don't have build_system.
            build_system = self.dispatcher.get_build_system_from_bugswarm_database(job_id)

        result = self.dispatcher.analyze(orig, job_id, build_system, trigger_sha, repo, 1)
        if print_result:
            pprint.pprint(result)

        return result
