

class Job(object):
    def __init__(self, job_id: int, job_num: int, config: str,
                 language: str, result, job_name=None, failed_step_index=None, steps=[],
                 run_time=0):
        self.job_id = job_id
        self.job_num = job_num
        self.job_name = job_name
        # The configuration is used to algin jobs that have the same configuration.
        self.config = config
        self.language = language
        self.result = result

        self.failed_step_index = failed_step_index
        self.steps = steps
        self.failed_step_kind = None  # One of 'uses' or 'run'
        self.failed_step_command = None  # Either the name of the action run with 'uses', or the command run with 'run'

        self.run_time_seconds = run_time

    def __str__(self):
        content = ' : '.join(['number=' + str(self.job_num)])
        return 'Job(' + content + ')'

    def __repr__(self):
        content = ' : '.join(['number=' + str(self.job_num)])
        return 'Job(' + content + ')'
