from typing import Any, Tuple

from reproducer.pipeline.github import expressions

from .context import Context


class EnvContext(Context):
    """Context used for environment variables. Note that the environment variables are *already quoted*."""

    def __init__(self):
        super().__init__()
        self.env = {}  # Environment variables that get overrided by $GITHUB_ENV.
        self.step_env = {}  # Environment variables that override $GITHUB_ENV.
        self.updating = False

    def update_env(self, workflow_env, job, parent_step, step, root_context):
        # Parent step: the step that triggered the composite action, None for non-composite action.
        self.updating = True
        parent_step = parent_step or {}
        saved_env = self.env
        saved_step_env = self.step_env
        try:
            self.env = {}
            workflow_env = {k: expressions.substitute_expressions(v, job.job_id, root_context)
                            for k, v in workflow_env.items()}
            self.env.update(workflow_env)
            job_env = {k: expressions.substitute_expressions(v, job.job_id, root_context)
                       for k, v in job.config.get('env', {}).items()}
            self.env.update(job_env)

            self.step_env = {}
            parent_step_env = {k: expressions.substitute_expressions(v, job.job_id, root_context)
                               for k, v in parent_step.get('env', {}).items()}
            self.step_env.update(parent_step_env)
            step_env = {k: expressions.substitute_expressions(v, job.job_id, root_context)
                        for k, v in step.get('env', {}).items()}
            self.step_env.update(step_env)
        except Exception as e:
            self.env = saved_env
            self.step_env = saved_step_env
            raise e
        finally:
            self.updating = False

    def get(self, path: str, err_if_not_present=False, make_string=False) -> Tuple[Any, bool]:
        varname = path.replace(' ', '_')
        default_value, default_dyn = super().get(path, err_if_not_present, make_string)

        # Step envs override $GITHUB_ENV. See https://github.com/Robert-Furth/actions-test/actions/runs/3114758307.
        if self.updating or path in self.step_env:
            return default_value, default_dyn

        # If the variable is in the ENVS dict set by parsing $GITHUB_ENV, use it. Otherwise, use the value from the
        # workflow file.
        # CURRENT_ENV_MAP is a Bash associative array, where the keys are the variable names. If varname is in the array,
        # use the corresponding value; otherwise use the static value
        return ('"$(test -v "CURRENT_ENV_MAP[{0}]" && echo "${{CURRENT_ENV_MAP[{0}]}}" || echo {1})"'.format(
                varname, default_value), True)

    def as_dict(self) -> dict:
        return {**self.env, **self.step_env}

    def to_env_str(self) -> str:
        s = ''
        for k, v in self.env.items():
            s += '{}={} '.format(k, v)
        s += '"${CURRENT_ENV[@]}" '
        for k, v in self.step_env.items():
            s += '{}={} '.format(k, v)
        return s

    def is_dynamic(self, key) -> bool:
        return True
