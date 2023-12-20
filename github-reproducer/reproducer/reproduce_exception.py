from contextlib import contextmanager

import docker.errors
import git


class ReproduceError(Exception):
    """
    Base exception for errors in the Reproducer.

    Subclasses should override CATEGORY with their own short explanatory string.
    """

    CATEGORY = 'Uncategorized Error'

    def __init__(self, *args, pipeline_stage: str = None):
        super().__init__(*args)
        self.pipeline_stage = pipeline_stage

    @property
    def message(self):
        return super().__str__()

    def __str__(self):
        if self.pipeline_stage:
            return '{} in {}: {}'.format(self.CATEGORY, self.pipeline_stage, self.message)
        return '{}: {}'.format(self.CATEGORY, super().__str__())

    def __repr__(self):
        prefix = '{}(stage={}'.format(type(self).__name__, self.pipeline_stage)
        if self.args:
            args_str = ', '.join(repr(el) for el in self.args)
            return prefix + '; ' + args_str + ')'
        return prefix + ')'


class DockerError(ReproduceError):
    CATEGORY = 'Docker Error'


class DockerHubError(ReproduceError):
    CATEGORY = 'DockerHub Error'


class GitError(ReproduceError):
    CATEGORY = 'Git Error'


class RepoCloneError(ReproduceError):
    CATEGORY = 'Repo Clone/Copy Error'


class RepoSetupError(ReproduceError):
    CATEGORY = 'Repo Setup Error'


class ReproductionTimeout(ReproduceError):
    CATEGORY = 'Reproduction Timeout'


class ExpressionParseError(ReproduceError):
    CATEGORY = 'GHA Expression Parse Error'


class ContextError(ReproduceError):
    CATEGORY = 'GHA Context Error'


class UnsupportedWorkflowError(ReproduceError):
    CATEGORY = 'Unsupported GHA Feature'


class InvalidPredefinedActionError(ReproduceError):
    CATEGORY = 'Invalid Predefined Action'


@contextmanager
def wrap_errors(pipeline_stage: str):
    try:
        yield
    except ReproduceError as e:
        if not e.pipeline_stage:
            e.pipeline_stage = pipeline_stage
        raise e
    except docker.errors.DockerException as e:
        raise DockerError(e, pipeline_stage=pipeline_stage)
    except git.GitError as e:
        raise GitError(e, pipeline_stage=pipeline_stage)
    except Exception as e:
        raise ReproduceError(e, pipeline_stage=pipeline_stage)
