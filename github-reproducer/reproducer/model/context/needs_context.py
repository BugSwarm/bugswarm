from typing import Any, Tuple
from .context import Context

from bugswarm.common import log


class NeedsContext(Context):
    """
    Provides the `needs` context for GitHub Actions expressions.

    Since the reproducer runs jobs individually (not as a full workflow), we cannot
    obtain real outputs from dependency jobs. Instead:
    - `needs.<job_id>.result` returns 'success' (the job ran, so dependencies succeeded)
    - `needs.<job_id>.outputs.<key>` returns '' (unknown)
    """

    def __init__(self):
        super().__init__()

    def as_dict(self) -> dict:
        return {}

    def get(self, path: str, err_if_not_present=False, make_string=False) -> Tuple[Any, bool]:
        parts = path.split('.')
        if len(parts) >= 2 and parts[1].lower() == 'result':
            # needs.<job_id>.result — job must have succeeded for this job to run
            return 'success', False
        if len(parts) >= 3 and parts[1].lower() == 'outputs':
            # needs.<job_id>.outputs.<key>
            log.warning('needs.{}.outputs.{} is not available in the reproducer, returning empty string'.format(
                parts[0], '.'.join(parts[2:])))
            return '', False
        # Unknown sub-path — return empty string rather than crashing
        log.warning('Unrecognized needs context path: {}'.format(path))
        return '', False
