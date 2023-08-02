

class Build(object):
    def __init__(self, build_id: int, build_num: int, commit: str, message: str, committed_at, committer_name: str,
                 finished_at):
        self.build_id = build_id
        self.build_num = build_num

        self.commit = commit
        # In some cases, the Travis API returns null for some commit messages. In this case, default to an empty string.
        self.message = message or ''
        # The commit that triggered the build.
        self.trigger_commit = ''
        # The base commit at the time of the build.
        self.base_commit = ''

        self.committed_at = committed_at

        # The jobs for the build.
        self.jobs = []
        self.virtual_commit_info = None
        self.status = 'passed'
        self.resettable = False
        self.github_archived = False
        self.squashed = False

    def get_job(self, job_id):
        for j in self.jobs:
            if j.job_id == job_id:
                return j

    def update_status(self):
        """
        there are usually many jobs in a build, if any of the jobs failed ( status == 1 ),
        the build is determined as failed.
        If any of the jobs have status null, then it might be errored or pending, further check is done in .
        :return:
        """
        statuses_of_jobs = [j.result for j in self.jobs]
        # print(statuses_of_jobs)
        if None in statuses_of_jobs:
            self.status = 'errored'
        elif 1 in statuses_of_jobs:
            self.status = 'failed'

    def passed(self) -> bool:
        return self.status == 'passed'

    def failed(self) -> bool:
        return self.status == 'failed' or self.status == 'errored'

    def errored(self) -> bool:
        return self.status == 'errored'

    def __str__(self):
        content = ' : '.join(['number=' + str(self.build_num),
                              'id=' + str(self.build_id),
                              self.status,
                              'jobs=' + str(len(self.jobs)) if self.jobs is not None else '?',
                              'trigger=' + self.trigger_commit[:7],
                              'base=' + self.base_commit[:7]])
        return 'Build(' + content + ')'

    def __repr__(self):
        content = ' : '.join(['number=' + str(self.build_num),
                              'id=' + str(self.build_id),
                              self.status,
                              'jobs=' + str(len(self.jobs)) if self.jobs is not None else '?',
                              'trigger=' + self.trigger_commit[:7],
                              'base=' + self.base_commit[:7]])
        return 'Build(' + content + ')'
