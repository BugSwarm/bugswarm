class BuildGroup:
    """
    A drop-in replacement to Branch objects (see branch.py) specifically for
    Github Actions jobs. Groups workflow runs ("builds") by their Git branch
    (including repo owner) and their workflow ID.
    """

    def __init__(self, branch_name, branch_owner, workflow_id, workflow_path):
        self.branch_name = branch_name
        self.branch_owner = branch_owner
        self.workflow_id = workflow_id
        self.workflow_path = workflow_path

        # List of builds in this group
        self.builds = []

        # Info populated by pipeline steps
        self.merged_at = None
        self.pairs = []
        self.ght_commits = []
        self.github_commits = []
        self.html_commits = {}
        self.base_branch = ''
        self.pr_info = None

    def get_build(self, build_id):
        for build in self.builds:
            if build.build_id == build_id:
                return build
        return None

    def sort_builds(self):
        self.builds.sort(key=lambda b: b.build_id)

    def __repr__(self):
        return 'BuildGroup(branch={}, workflow={}, num_builds={})'.format(
            self.branch_name,
            self.workflow_id,
            len(self.builds)
        )
