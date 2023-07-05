from .build import Build


class PullRequest(object):
    def __init__(self, pr_num: str = '-1', builds: [Build] = None):
        if builds is None:
            builds = []
        self.pr_num = pr_num
        self.builds = builds
        self.merged = False
        self.num_commits = -1

    def __str__(self):
        content = ' : '.join(['id=' + str(self.pr_num),
                              'merged=' + str(self.merged),
                              'builds=' + str(len(self.builds)),
                              'num_commits=' + str(self.num_commits)])
        return 'PullRequest(' + content + ')'

    def __repr__(self):
        content = ' : '.join(['id=' + str(self.pr_num),
                              'merged=' + str(self.merged),
                              'builds=' + str(len(self.builds)),
                              'num_commits=' + str(self.num_commits)])
        return 'PullRequest(' + content + ')'
