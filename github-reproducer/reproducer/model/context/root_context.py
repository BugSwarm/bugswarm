from ..job import Job
from .context import Context
from .env_context import EnvContext
from .github_context import GitHubContext
from .job_context import JobContext
from .runner_context import RunnerContext
from .steps_context import StepsContext
from .strategy_context import StrategyContext
from .inputs_context import InputsContext
from .matrix_context import MatrixContext


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
        self.matrix = MatrixContext(job)

    def as_dict(self):
        return {
            'github': self.github,
            'env': self.env,
            'job': self.job,
            'steps': self.steps,
            'runner': self.runner,
            'strategy': self.strategy,
            'inputs': self.inputs,
            'matrix': self.matrix,
        }
