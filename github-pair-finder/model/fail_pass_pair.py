
class FailPassPair(object):
    def __init__(self, failed_build, passed_build):
        self.failed_build = failed_build
        self.passed_build = passed_build
        self.repo_mined_version = None
        self.jobpairs = []
        self.exclude_from_output = False

    def __str__(self):
        content = ' -> '.join([str(self.failed_build), str(self.passed_build)])
        return 'FailPassPair(' + content + ')'

    def __repr__(self):
        content = ' -> '.join([str(self.failed_build), str(self.passed_build)])
        return 'FailPassPair(' + content + ')'
