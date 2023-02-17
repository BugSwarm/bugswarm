import re
from typing import Any, Tuple
from .context import Context


class StepsContext(Context):
    """
    Converts all keys of the type `${{ steps.stepid.a.b }}` to the
    environment variable `$_CONTEXT_STEPS_STEPID_A_B`.
    """

    def __init__(self, prefix='_CONTEXT_STEPS'):
        super().__init__()
        self.prefix = prefix

    def as_dict(self):
        return {}

    def is_dynamic(self, key) -> bool:
        return True

    def get(self, path: str, err_if_not_present=False, make_string=False) -> Tuple[Any, bool]:
        path = re.sub(r'\W+', '_', path.upper())
        return '${{_CONTEXT_STEPS_{}}}'.format(path), True
