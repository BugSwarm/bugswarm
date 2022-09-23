from ..job import Job
from .context import Context
from .env_context import EnvContext
from .github_context import GitHubContext
from .job_context import JobContext
from .runner_context import RunnerContext
from .steps_context import StepsContext
from .strategy_context import StrategyContext
from .inputs_context import InputsContext


class RootContext(Context):
    def __init__(self, job: Job):
        super().__init__()
        self.github = GitHubContext(job)
        self.env = EnvContext()
        self.job = JobContext()
        self.steps = StepsContext()
        self.runner = RunnerContext()
        self.strategy = StrategyContext(job)
        self.inputs = InputsContext()
        self.matrix = job.config.get('strategy', {}).get('matrix', {})

    def as_dict(self):
        return vars(self)
