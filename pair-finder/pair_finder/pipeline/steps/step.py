from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Optional


class Step(ABC):
    def __init__(self):
        pass

    # Concrete implementations should raise a StepException upon encountering a fatal error to signal that the
    # pipeline should exit early.
    @abstractmethod
    def process(self, data: Any, context: dict) -> Optional[Any]:
        pass


class StepException(Exception):
    pass
