from .context import Context


class RunnerContext(Context):

    def __init__(self):
        super().__init__()
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

    def as_dict(self):
        return {
            'name': self.name,
            'os': self.os,
            'arch': self.arch,
            'temp': self.temp,
            'tool_cache': self.tool_cache,
        }
