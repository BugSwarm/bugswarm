class StrategyContext:

    def __init__(self):
        # When true, all in-progress jobs are canceled if any job in a matrix fails.
        self.fail_fast = 'false'
        # (Dynamic) The index of the current job in the matrix. Note: This number is a zero-based number.
        self.job_index = ''
        # The total number of jobs in the matrix.
        self.job_total = '1'
        # The maximum number of jobs that can run simultaneously when using a matrix job strategy.
        self.max_parallel = '1'
