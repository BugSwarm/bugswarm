
class JobPair(object):
    def __init__(self, failed_job, passed_job):
        self.failed_job = failed_job
        self.passed_job = passed_job
        self.build_system = 'NA'

    def __str__(self):
        content = ' -> '.join([str(self.failed_job), str(self.passed_job)])
        return 'JobPair(' + content + ')'

    def __repr__(self):
        content = ' -> '.join([str(self.failed_job), str(self.passed_job)])
        return 'JobPair(' + content + ')'
