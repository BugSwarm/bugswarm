from typing import Any, Tuple
from .context import Context


class InputsContext(Context):

    def __init__(self):
        super().__init__()
        self.inputs = {}

    def update_inputs(self, inputs, merge=False):
        if merge:
            self.inputs = {**self.inputs, **inputs}
        else:
            self.inputs = inputs

    def as_dict(self):
        return {}

    def is_dynamic(self, key) -> bool:
        return True

    def get(self, path: str, err_if_not_present=False, make_string=False) -> Tuple[Any, bool]:
        # The env variable created converts input names to uppercase letters and replaces spaces with _ characters.
        key = 'INPUT_{}'.format(path.upper().replace(' ', '_'))
        if key in self.inputs:
            # If key in our inputs dict, replace it with string
            return self.inputs[key], True

        # Otherwise, replace it with environment variable
        if '-' in key:
            return '$(printenv {})'.format(key), True
        return '${{{}}}'.format(key), True
