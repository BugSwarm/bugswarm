from .context import Context


class JobContext(Context):
    def __init__(self):
        super().__init__()
        self.status = '"${_GITHUB_JOB_STATUS}"'

    def as_dict(self) -> dict:
        return {'status': self.status}

    def is_dynamic(self, key) -> bool:
        return key == 'status'
