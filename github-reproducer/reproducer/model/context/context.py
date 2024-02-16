from abc import ABC, abstractmethod
from typing import Any, Tuple

from reproducer.reproduce_exception import ContextError

from bugswarm.common import log


class Context(ABC):
    def __init__(self):
        self.case_sensitive = False

    @abstractmethod
    def as_dict(self) -> dict:
        pass

    def is_dynamic(self, key) -> bool:
        return False

    def get(self, path: str, err_if_not_present=False, make_string=False) -> Tuple[Any, bool]:
        """
        Assumes paths are simple (i.e. no `[]` indexing and no `.*` object filters)
        """

        result = self.as_dict()
        parts = path.split('.')
        is_dynamic = False

        try:
            for i, key in enumerate(parts):
                if not self.case_sensitive:
                    key = key.lower()

                if isinstance(result, dict):
                    result = result[key]
                elif isinstance(result, Context):
                    is_dynamic = is_dynamic or result.is_dynamic(key)
                    result, d = result.get('.'.join(parts[i:]), err_if_not_present, make_string)
                    return result, is_dynamic or d
                else:
                    raise KeyError('Path "{}" not present in context'.format(path))
        except KeyError as e:
            log.warning('Path "{}" not present in context'.format(path))
            if err_if_not_present:
                raise ContextError(e.args) from e
            return '', False

        if make_string:
            if isinstance(result, list):
                return '[Array]', False
            if isinstance(result, (dict, Context)):
                return '[Object]', False
            return str(result), is_dynamic

        return result, is_dynamic
