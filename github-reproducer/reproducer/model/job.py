from multiprocessing import Value


class Job(object):
    def __init__(self, build, build_job, job_id, language, config, image_tag):
        self.build = build
        self.build_job = build_job
        self.job_id = str(job_id)
        self.image_tag = image_tag
        self.language = language
        self.config = config
        self.image_tag = image_tag

        self.repo = build.buildpair.repo
        self.branch = build.buildpair.branch
        self.base_sha = build.base_sha
        self.sha = build.head_sha
        self.travis_merge_sha = build.travis_merge_sha
        self.resettable = build.resettable
        self.github_archived = build.github_archived
        self.is_failed = 'failed' if build.is_failed else 'passed'  # TODO: WHY NOT BOOLEAN???
        if build.buildpair.pr_num != -1:
            self.is_pr = True
        else:
            self.is_pr = False
        self.skip = Value('i', 0)
        self.reproduced = Value('i', 0)
        self.match = Value('i', False)
        self.mismatch_attrs = []
        self.job_name = ''  # Initialized in pair center function.

        self.reproduced_result = None
        self.orig_result = None

    def __str__(self):
        return 'Job(' + str(self.job_name) + ')'

    def __repr__(self):
        return 'Job(' + str(self.job_name) + ')'
