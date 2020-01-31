import pprint

from .dispatcher import Dispatcher
from .result_comparer import ResultComparer

LOAD_JSON = 1


class Analyzer(object):
    def __init__(self):
        self.dispatcher = Dispatcher()
        self.comparer = ResultComparer()
        print('test')

    def analyze_single_log(self, log_path, job_id, build_system=None, trigger_sha=None, repo=None, print_result=False):
        result = self.dispatcher.analyze(log_path, job_id, build_system, trigger_sha, repo)
        if print_result:
            pprint.pprint(result)

        return result

    def compare_single_log(self, reproduced, orig, job_id, build_system=None, trigger_sha=None, repo=None,
                           print_result=False):
        reproduced_result = self.dispatcher.analyze(reproduced, job_id, build_system, trigger_sha, repo)
        original_result = self.dispatcher.analyze(orig, job_id, build_system, trigger_sha, repo)
        match, mismatched_attributes = ResultComparer.compare_attributes(reproduced_result, original_result)

        return match, mismatched_attributes

    def force_re_analyze_travis_log(self, orig, job_id, build_system=None, trigger_sha=None, repo=None,
                                    print_result=False):
        print('the orig log was not determined as Java: ', orig)
        print('force analyze as Java log')
        result = self.dispatcher.analyze(orig, job_id, build_system, trigger_sha, repo, 1)

        return result
