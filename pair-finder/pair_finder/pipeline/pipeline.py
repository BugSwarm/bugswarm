from typing import Any
from typing import Optional
from typing import Tuple

from bugswarm.common import log

from .steps.step import StepException


class Pipeline(object):
    """
    A Pipeline represents a series of steps.
    Only supports linearly connected steps.
    """

    def __init__(self, steps):
        self._step_results_context = None
        self._steps = steps

    @property
    def steps(self):
        return self._steps

    def run(self, data: Any, in_context: dict) -> Tuple[Optional[Any], dict]:
        self._step_results_context = {}
        d = data
        for f in self.steps:
            try:
                d = f.process(d, in_context)
            except StepException as e:
                log.error(e)
                # The most recently run step encountered a fatal error, so end the pipeline early.
                return None, in_context
            except Exception as e:
                # This error was unexpected. (Step subclasses should only raise StepException.) So let the exception
                # propagate so the thread running this Pipeline terminates.
                log.error(e)
                raise
            key = self._context_key_for_step_class(type(f))
            self._step_results_context[key] = d
        return d, in_context

    def get_step_result_context(self, step_class) -> Any:
        return self._step_results_context[self._context_key_for_step_class(step_class)]

    def _context_key_for_step_class(self, step_class) -> str:
        step_classes = [type(x) for x in self.steps]
        index = step_classes.index(step_class)
        return '-'.join([str(index + 1), step_class.__name__])
