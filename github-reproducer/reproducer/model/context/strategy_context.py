from .context import Context


class StrategyContext(Context):

    def __init__(self, job):
        super().__init__()
        # When true, all in-progress jobs are canceled if any job in a matrix fails.
        self.fail_fast = str(job.config.get('strategy', {}).get('fail-fast', {}) or False).lower()
        # (Dynamic) The index of the current job in the matrix. Note: This number is a zero-based number.
        self.job_index = '0'  # TODO set this properly (put job_index in database from pairfinder?)
        # The total number of jobs in the matrix.
        self.job_total = '1'
        # The maximum number of jobs that can run simultaneously when using a matrix job strategy.
        self.max_parallel = '1'

    def as_dict(self):
        return {
            'fail_fast': self.fail_fast,
            'job_index': self.job_index,
            'job_total': self.job_total,
            'max_parallel': self.max_parallel,
        }
