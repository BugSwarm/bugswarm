class RunnerContext(object):

    def __init__(self):
        # The name of the runner executing the job.
        self.name = 'Bugswarm GitHub Actions Runner'
        # The operating system of the runner executing the job.
        self.os = 'Linux'
        # The architecture of the runner executing the job.
        self.arch = 'X64'
        # The path to a temporary directory on the runner.
        self.temp = '/tmp'
        # The path to the directory containing preinstalled tools for GitHub-hosted runners.
        self.tool_cache = '/opt/hostedtoolcache'
