from typing import Any
from typing import Optional

from ...utils import Utils
from .step import Step


class Postflight(Step):
    def process(self, data: Any, context: dict) -> Optional[Any]:
        repo = context['repo']
        keep_clone = context['keep_clone']

        if keep_clone is False:
            Utils.remove_repo_clone(repo)

        return data
