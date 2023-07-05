

class Job(object):
    def __init__(self, job_id: int, job_num: int, config: str, language: str, result):
        self.job_id = job_id
        self.job_num = job_num
        # The configuration is used to algin jobs that have the same configuration.
        self.config = config
        self.language = language
        self.result = result

    def __str__(self):
        content = ' : '.join(['number=' + str(self.job_num)])
        return 'Job(' + content + ')'

    def __repr__(self):
        content = ' : '.join(['number=' + str(self.job_num)])
        return 'Job(' + content + ')'
