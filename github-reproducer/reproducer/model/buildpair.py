from multiprocessing import Value

from .build import Build


class BuildPair(object):
    def __init__(self, repo: str, json_data):
        # The JSON representation of this build pair.
        self.json_data = json_data
        # The repository slug for the project from which this build pair was mined.
        self.repo = repo
        self.branch = self.json_data['branch']

        self.pr_num = self.json_data['pr_num']
        self.failed_build = Build(self, self.json_data['failed_build'], is_failed=True)
        self.passed_build = Build(self, self.json_data['passed_build'], is_failed=False)
        self.builds = [self.failed_build, self.passed_build]
        self.jobpairs = []
        self.match = Value('i', 0)
        self.done = Value('i', False)
        self.set_match_type = Value('i', False)
