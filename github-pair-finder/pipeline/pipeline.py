from bugswarm.common import log

from .steps.step_exception import StepException


class Pipeline:
    def __init__(self, steps, cleanup_step=None):
        self.steps = steps
        self.cleanup_step = cleanup_step

    def run(self, data, in_context):
        try:
            for step in self.steps:
                data = step.process(data, in_context)
            return data, in_context
        except StepException as e:
            log.error(e)
            return None, in_context
        except Exception as e:
            log.error(e)
            log.error("Exiting this thread's pipeline due to the previous error.")
            raise e
        finally:
            if self.cleanup_step:
                self.cleanup_step.process(data, in_context)
