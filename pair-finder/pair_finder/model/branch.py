from typing import Optional

BranchID = str


class Branch(object):
    def __init__(self, branch_name: Optional[str], pr_num: int):
        self.branch_id = Branch.construct_branch_id(branch_name, pr_num)
        self.branch_name = branch_name
        self.pr_num = pr_num
        self.builds = []
        self.merged_at = None
        self.num_commits = -1
        self.pairs = []
        self.ght_commits = []
        self.github_commits = []
        self.html_commits = {}
        self.base_branch = ''
        self.pr_info = None

    def get_build(self, build_id):
        for b in self.builds:
            if b.build_id == build_id:
                return b

    def sort_builds(self):
        self.builds = sorted(self.builds, key=lambda b: b.build_id)

    def __str__(self):
        content = ' : '.join(['pr_num=' + str(self.pr_num),
                              'merged_at=' + str(self.merged_at),
                              'builds=' + str(len(self.builds)),
                              'num_commits=' + str(self.num_commits)])
        return 'Branch(' + content + ')'

    def __repr__(self):
        content = ' : '.join(['pr_num=' + str(self.pr_num),
                              'merged_at=' + str(self.merged_at),
                              'builds=' + str(len(self.builds)),
                              'num_commits=' + str(self.num_commits)])
        return 'Branch(' + content + ')'

    @classmethod
    def construct_branch_id(cls, branch_name: Optional[str], pr_num: int) -> BranchID:
        """
        Create the a string that uniquely identifies this branch within its project.

        If the branch if from a pull request, then the branch ID is the PR number.
        Otherwise, the branch ID is the branch name appended with a tilde ('~').
        """
        if branch_name and not isinstance(branch_name, str):
            raise TypeError
        if not isinstance(pr_num, int):
            raise TypeError
        return branch_name + '~' if pr_num == -1 else str(pr_num)
