from bugswarm.common import log


class JobCenter(object):
    """
    This file is out-dated.
    This file is only used to reproduce a list of jobs, not pairs. We have not done that in a long time, so this file is
    very out-dated. If we ever want to reproduce a list of jobs, please update this file.
    """
    def __init__(self):
        self.repos = {}
        self.uninitialized_repos = []
        self.total_jobs = 0

    def load_jobs_from_script_file(self, file, job_center):
        with open(file) as f:
            for l in f:
                if 'sudo docker' in l or '#!/bin/bash' in l:
                    continue
                self.add(l.strip())
        log.debug('len(job_ids) =', self.total_jobs)

    def add(self, script):
        splitted = script.split(' ')
        if len(splitted) == 6:
            bash, reproduce, repo, sha, build_job, job_id = script.strip().split(' ')
        elif len(splitted) == 7:
            bash, reproduce, repo, base_sha, sha, build_job, job_id = script.strip().split(' ')

        if repo not in self.repos:
            self.repos[repo] = self.repo_obj()
            self.uninitialized_repos.append(repo)
        self.repos[repo].add_job_to_repo(repo, job_id, sha, build_job, script)
        self.total_jobs += 1

    def check_all_repos_done(self):
        all_done = True
        for r in self.repos:
            if not self.repos[r].all_done:
                all_done = False
        return all_done

    class repo_obj(object):
        def __init__(self):
            self.jobs = []
            self.has_repo = False
            self.all_done = False
            self.clone_error = False

        def add_job_to_repo(self, repo, job_id, sha, build_job, script):
            self.jobs.append(self.job_obj(repo, job_id, sha, build_job, script))

        class job_obj(object):
            def __init__(self, repo, job_id, sha, build_job, script):
                self.repo = repo
                self.job_id = job_id
                self.sha = sha
                self.build_job = build_job
                self.script = script

        def get_job(self):
            job = self.jobs.pop()
            if not self.jobs:
                self.all_done = True
            return job
