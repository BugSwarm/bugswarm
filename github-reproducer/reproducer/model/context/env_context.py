from reproducer.utils import Utils

from .context import Context


class EnvContext(Context):
    """Context used for environment variables. Note that the environment variables are *already quoted*."""

    def __init__(self):
        super().__init__()
        self.env = {}

    def update_env(self, workflow_env, job, step, parent_step, root_context):
        # Parent step: the step that triggered the composite action, None for non-composite action.
        self.env = {}
        workflow_env = {k: Utils.substitute_expressions(root_context, v) for k, v in workflow_env.items()}
        self.env.update(workflow_env)
        job_env = {k: Utils.substitute_expressions(root_context, v) for k, v in job.config.get('env', {}).items()}
        self.env.update(job_env)

        if parent_step:
            parent_step_env = {
                k: Utils.substitute_expressions(root_context, v) for k, v in parent_step.get('env', {}).items()
            }
            self.env.update(parent_step_env)

        step_env = {k: Utils.substitute_expressions(root_context, v) for k, v in step.get('env', {}).items()}
        self.env.update(step_env)
        # self.env.update(job.config.get('env', {}))
        # self.env.update(step.get('env', {}))

    def as_dict(self) -> dict:
        return self.env

    def to_env_str(self) -> str:
        s = ''
        for k, v in self.as_dict().items():
            s += '{}={} '.format(k, v)
        return s

    def is_dynamic(self, key) -> bool:
        return True
