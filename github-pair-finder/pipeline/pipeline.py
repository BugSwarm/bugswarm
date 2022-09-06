from bugswarm.common import log

from .steps.step_exception import StepException


class Pipeline:
    def __init__(self, steps):
        self.steps = steps

    def run(self, data, in_context):
        for step in self.steps:
            try:
                data = step.process(data, in_context)
            except StepException as e:
                log.error(e)
                return None, in_context
            except Exception as e:
                log.error(e)
                log.error("Exiting this thread's pipeline due to the previous error.")
                raise e
        return data, in_context
