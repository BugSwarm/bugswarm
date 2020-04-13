from typing import Any
from typing import Optional

from bugswarm.common import log

from .step import Step
from .step import StepException
from ...utils import Utils


class Preflight(Step):
    def process(self, data: Any, context: dict) -> Optional[Any]:
        repo = context['repo']
        utils = context['utils']
        log.info('Repository:', repo)

        # Skip the repo if it appears to be private or deleted.
        if utils.repo_is_private_or_removed(repo):
            Utils.write_empty_json(repo, context['task_name'])
            msg = 'Repository: {} is either private or removed. Skipping.'.format(repo)
            log.error(msg)
            raise StepException(msg)

        # Skip the repo if was not cloned successfully.
        if Utils.clone_repo(repo) is False:
            msg = 'Cloning failed for {}. Skipping.'.format(repo)
            log.error(msg)
            raise StepException(msg)

        is_mined, repo_in_db = Utils.is_repo_previously_mined(repo)
        if is_mined:
            # Set the current mining repo to be what our DB contains
            repo = repo_in_db

        if Utils.store_git_log(repo) is False:
            # The clone failed, likely because this repo has been removed or made private.
            # So signal that this repo should be skipped.
            msg = 'git log failed for {}. Skipping.'.format(repo)
            log.error(msg)
            raise StepException(msg)
        try:
            shas = Utils.read_sha_from_git_log(repo)
        except UnicodeDecodeError as e:
            msg = 'UnicodeDecodeError while reading the git log file: {}. Skipping.'.format(e)
            log.error(msg)
            raise StepException(msg)
        except ValueError as e:
            msg = 'ValueError when reading the git log: {}. Skipping.'.format(e)
            log.error(msg)
            raise StepException(msg)

        if not shas:
            msg = 'Did not read any SHAs from the git log. Skipping.'
            log.error(msg)
            raise StepException(msg)

        context['shas'] = shas
        return data
