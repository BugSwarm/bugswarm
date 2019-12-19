import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from distutils.dir_util import copy_tree
from typing import Callable
from typing import List

from . import utils as procutils
from bugswarm.common import log


class ParallelArtifactRunner(object):
    """
    ParallelArtifactRunner is an abstract base class that facilitates parallel processing of BugSwarm artifacts.

    A concrete subclass must override the process_artifact method where it can perform some operation on each artifact.
    A concrete subclass may also override the following methods:
    - pre_run:   Called before processing any artifacts
    - post_run:  Called after processing all artifacts
    """
    def __init__(self, image_tags: List[str], workers: int = 1):
        """
        :param image_tags: A list of image tags representing BugSwarm artifacts.
        :param workers: The maximum number of worker threads to spawn, clamped to (0, length of `image_tags`].
                        Defaults to 1, in which case each image tag is processed sequentially.
        """
        if not image_tags:
            raise ValueError
        if workers <= 0:
            raise ValueError
        self._image_tags = image_tags
        self._num_workers = min(workers, len(self._image_tags))

    def run(self):
        """
        Start processing image tags.

        Overriding is forbidden.
        """
        self.pre_run()
        with ThreadPoolExecutor(max_workers=self._num_workers) as executor:
            future_to_image_tag = {executor.submit(self._thread_main, image_tag): image_tag
                                   for image_tag in self._image_tags}
        attempted = 0
        succeeded = 0
        errored = 0
        for future in as_completed(future_to_image_tag):
            attempted += 1
            try:
                data = future.result()
                if data:
                    succeeded += 1
                else:
                    errored += 1
            except Exception as e:
                log.error(e)
                errored += 1
        self.post_run()

    def _thread_main(self, image_tag: str):
        return self.process_artifact(image_tag)

    def process_artifact(self, image_tag: str):
        """
        Subclasses must override this method to process each item in the workload.

        Subclasses that do not inherit directly from ParallelArtifactRunner can call super as appropriate.
        :param image_tag: The image tag representing the artifact to process.
        :return: The eventual return value of the worker thread that processed `image_tag`.
        """
        raise NotImplementedError

    def pre_run(self):
        """
        Called before any items have been processed.

        Overriding is optional. Defaults to no-op. Subclasses should call super as appropriate.
        """
        pass

    def post_run(self):
        """
        Called after all items have been processed.

        Overriding is optional. Defaults to no-op. Subclasses can call super as appropriate.
        """
        pass


class CopyAndExecuteArtifactRunner(ParallelArtifactRunner):
    """
    Concrete subclass of ParallelArtifactRunner that facilitates a common runner workflow:
    - List, in a file, BugSwarm artifact image tags to process;
    - Copy files, that should be available to all processed artifacts, into the host-side sandbox;
    - For each processed artifact, execute commands inside the artifact container.
    """
    def __init__(self, image_tags_file: str, copy_dir: str, command: Callable[[str], str], workers: int = 1):
        """
        :param image_tags_file: Path to a file containing a newline-separated list of image tags.
        :param copy_dir: A directory to copy into the host-side sandbox before any artifacts are processed.
        :param command: A callable used to determine what command(s) to execute in each artifact container. `command` is
                        called once for each processed artifact. The only parameter is the image tag of the artifact
                        about to be processed.
        :param workers: The same as for the superclass initializer.
        """
        with open(image_tags_file) as f:
            image_tags = list(map(str.strip, f.readlines()))
        super().__init__(image_tags, workers)
        self.copy_dir = copy_dir
        self._command = command

    def pre_run(self):
        copy_tree(self.copy_dir, os.path.join(procutils.HOST_SANDBOX, self.copy_dir))

    def process_artifact(self, image_tag: str):
        return procutils.run_artifact(image_tag, command=self._command(image_tag))
