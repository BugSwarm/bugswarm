from ..job import Job
from .context import Context


class MatrixContext(Context):
    def __init__(self, job: Job):
        super().__init__()
        matrix = job.config.get('strategy', {}).get('matrix', {})
        self.contents = {key.lower(): val for key, val in matrix.items()}

    def as_dict(self) -> dict:
        return self.contents
