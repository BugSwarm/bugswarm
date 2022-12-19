from typing import Optional
from reproducer.utils import Utils
from reproducer.model.job import Job


class JobImageUtils:
    @staticmethod
    def default_image_label():
        return 'ubuntu-22.04'

    @staticmethod
    def get_bugswarm_image_tag(image_tag: str, use_default: bool) -> Optional[str]:
        # Convert GitHub Actions Runner label -> Docker image
        # If the conversion failed, return None if user_default is False, otherwise use ubuntu-22.04.
        bugswarm_image_tags = {
            'ubuntu-22.04': 'bugswarm/githubactionsjobrunners:ubuntu-22.04',
            'ubuntu-20.04': 'bugswarm/githubactionsjobrunners:ubuntu-20.04',
            'ubuntu-18.04': 'bugswarm/githubactionsjobrunners:ubuntu-18.04',
        }
        image_tag = image_tag.lower()

        if image_tag in bugswarm_image_tags:
            return bugswarm_image_tags[image_tag]
        if use_default:
            return bugswarm_image_tags[JobImageUtils.default_image_label()]
        return None

    @staticmethod
    def get_image_tag(runs_on, container) -> str:
        # Return a Docker image name based on jobs' runs_on and container
        # If the container field is set, always use the container
        if container:
            return container
        return JobImageUtils.get_bugswarm_image_tag(runs_on, use_default=True)

    @staticmethod
    def get_job_runs_on(config: Optional[dict], utils: Utils, job_id: str) -> str:
        # Return a supported runner label.
        runs_on = config.get('runs-on', None)
        if isinstance(runs_on, str):
            # Check if runs_on is a valid label.
            bugswarm_image_tag = JobImageUtils.get_bugswarm_image_tag(runs_on, use_default=False)
            if bugswarm_image_tag:
                return runs_on
        if isinstance(runs_on, list):
            for label in runs_on:
                # Check if label is a valid label.
                bugswarm_image_tag = JobImageUtils.get_bugswarm_image_tag(label, use_default=False)
                if bugswarm_image_tag:
                    return label
        # Unable to find a supported runner label, try manually parse the original log.
        return JobImageUtils.get_latest_image_label(utils, job_id)

    @staticmethod
    def get_job_container(config: Optional[dict]) -> Optional[str]:
        # Return a Docker image name. (None if not found)
        # This will only handle very basic container image
        # https://docs.github.com/en/actions/using-jobs/running-jobs-in-a-container
        container = config.get('container', None)
        if isinstance(container, str) and container != '':
            return container
        if isinstance(container, dict) and 'image' in container and container['image'] != '':
            return container['image']
        return None

    @staticmethod
    def get_latest_image_label(utils: Utils, job_id: str) -> str:
        # Get original runner image label from the original log.
        # It converts ubuntu-latest to ubuntu-18.04, ubuntu-20.04, or ubuntu-22.04
        actual_image_tag = utils.get_job_image_from_original_log(job_id)
        if actual_image_tag:
            if JobImageUtils.get_bugswarm_image_tag(actual_image_tag, use_default=False):
                # Verified actual_image_tag is a supported image label
                return actual_image_tag

        return JobImageUtils.default_image_label()

    @staticmethod
    def update_job_image_tag(job: Job, utils: Utils):
        job.runs_on = JobImageUtils.get_job_runs_on(job.config, utils, job.job_id)
        job.container = JobImageUtils.get_job_container(job.config)
        job.image_tag = JobImageUtils.get_image_tag(job.runs_on, job.container)
