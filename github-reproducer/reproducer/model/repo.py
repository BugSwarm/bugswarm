from multiprocessing import Lock
from queue import Queue

from .buildpair import BuildPair


class Repo(object):
    def __init__(self, repo):
        self.repo = repo
        self.buildpairs = []
        self.has_repo = False
        self.all_done = False
        self.clone_error = False
        self.lock = Lock()
        self.queue = Queue()

    def add_buildpair_to_repo(self, repo: str, buildpair):
        buildpair_obj = BuildPair(repo, buildpair)
        self.buildpairs.append(buildpair_obj)
        return buildpair_obj

    def init_queue_to_reproduce(self, swarm):
        if swarm:
            for bp in self.buildpairs:
                for jp in bp.jobpairs:
                    if not jp.skip:
                        self.queue.put(jp)
        else:
            for bp in self.buildpairs:
                for jp in bp.jobpairs:
                    # Get the passed job first because, when pruning is on, reproducing the failed job can be skipped if
                    # the passed job mismatches.
                    for i in range(1, -1, -1):
                        job = jp.jobs[i]
                        if not job.skip:
                            self.queue.put(job)

    def get_job(self):
        self.lock.acquire()
        for bp in self.buildpairs:
            for jp in bp.jobpairs:
                # Get the passed job first because, when pruning is on, reproducing the failed job can be skipped if the
                # passed job mismatches.
                for i in range(1, -1, -1):
                    job = jp.jobs[i]
                    if not job.skip and not job.reproduced:
                        job.reproduced = True
                        return job

    def get_jobpair(self):
        self.lock.acquire()
        for bp in self.buildpairs:
            for jp in bp.jobpairs:
                if not jp.skip and not jp.reproduced:
                    jp.reproduced = True
                    return jp
        self.lock.release()

    def set_all_jobs_in_repo_to_skip(self):
        self.all_done = True
        for bp in self.buildpairs:
            for b in bp.builds:
                for j in b.jobs:
                    j.skip = True
