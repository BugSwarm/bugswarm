import abc
import re


class LogAnalyzerABC(abc.ABC):
    def __init__(self, primary_language, folds, job_id):
        self.primary_language = primary_language
        self.job_id = job_id
        self.folds = folds
        self.OUT_OF_FOLD = 'out_of_fold'
        self.test_lines = []
        self.frameworks = []
        self.tests_run = False
        self.analyzer = 'plain'
        self.tests_failed = []
        self.initialized_tests = False
        self.err_msg = []
        self.err_lines = []
        self.connection_lines = []

    def analyze(self):
        self.custom_analyze()
        self.pre_output()
        self.sanitize_output()

    @abc.abstractmethod
    def custom_analyze(self):
        """
        Subclasses must implement their own analyses in this method.
        They must also ensure that they call `super().custom_analyze()` so any mixins after them in
        the MRO get called as well.
        """
        pass

    # Assign function values to variables before outputting.
    def pre_output(self):
        if hasattr(self, 'bool_tests_failed'):
            self.did_tests_fail = self.bool_tests_failed()

    # Perform last-second sanitaztion of variables. Can be used to guarantee invariants.
    def sanitize_output(self):
        if hasattr(self, 'pure_build_duration') and hasattr(self, 'test_duration'):
            if self.pure_build_duration < self.test_duration:
                del self.pure_build_duration

    def add_framework(self, framework):
        if framework not in self.frameworks:
            self.frameworks.append(framework)

    # pre-init values so we can sum-up in case of aggregated test sessions (always use calc_ok_tests when you use this)
    def init_tests(self):
        if not self.initialized_tests:
            self.test_duration = 0
            self.num_tests_run = 0
            self.num_tests_failed = 0
            self.num_tests_ok = 0
            self.num_tests_skipped = 0
            self.initialized_tests = True

    # For non-aggregated reporting, at the end (always use this when you use init_tests)
    def uninit_ok_tests(self):
        if hasattr(self, 'num_tests_run') and hasattr(self, 'num_tests_failed'):
            self.num_tests_ok += self.num_tests_run - self.num_tests_failed

    # The output is in seconds, even when it takes longer than a minute
    @staticmethod
    def convert_plain_time_to_seconds(s):
        match = re.search(r'(.+)s', s, re.M)
        if match:
            return round(float(match.group(1)), 2)
        return 0

    # Returns a dictionary containing the analysis results. All of the attributes are extracted by build log analysis.
    def output(self):
        mapping = {
            # The build ID of the Travis build.
            'tr_build_id': 'build_id',
            # The job ID of the build job under analysis.
            'tr_job_id': 'job_id',
            # The primary programming language.
            'tr_log_lan': 'primary_language',
            # The overall return status of the build.
            'tr_log_status': 'status',
            # The setup time before the script phase (the actual build) starts, in seconds.
            'tr_log_setup_time': 'setup_time_before_build',
            # The build log Analyzer that was invoked for analysis of this build.
            'tr_log_analyzer': 'analyzer',
            # The testing frameworks ran.
            'tr_log_frameworks': 'frameworks',
            # Whether tests were run.
            'tr_log_bool_tests_ran': 'tests_run',
            # Whether tests failed.
            'tr_log_bool_tests_failed': 'did_tests_fail',
            # Number of tests that succeeded.
            'tr_log_num_tests_ok': 'num_tests_ok',
            # Number of tests that failed.
            'tr_log_num_tests_failed': 'num_tests_failed',
            # Number of tests that ran in total.
            'tr_log_num_tests_run': 'num_tests_run',
            # Number of tests that were skipped.
            'tr_log_num_tests_skipped': 'num_tests_skipped',
            # Names of the tests that failed.
            'tr_log_tests_failed': 'tests_failed',
            # Duration of the running the tests, in seconds.
            'tr_log_testduration': 'test_duration',
            # Duration of running the build command like maven or ant, in seconds. (If present, this duration should be
            # longer than 'tr_log_testduration' since it includes this phase.)
            'tr_log_buildduration': 'pure_build_duration',

            # Added: Error messages in log.
            'tr_err_msg': 'err_msg',
            # Added: Build image provisioned date and time.
            'tr_build_image': 'build_image',
            # Added: (Travis) Worker instance info in log.
            'tr_worker_instance': 'worker_instance',
            # Added: (Travis) Using worker line in log, if it exists, will be first line of log.
            'tr_using_worker': 'using_worker',
            # Added: Capturing the line that specifies operating system.
            'tr_os': 'os',
            # Added: Capturing the lines that likely mention connection problems, dependencies, or endpoints that no
            # longer exist online.
            'tr_connection_lines': 'connection_lines',
            # Added: Capturing the lines that mention could not resolve dependencies.
            'tr_could_not_resolve_dep': 'could_not_resolve_dep',
            # Added: (Travis) Cookbook version in log.
            'tr_cookbook': 'cookbook',
            # Added: Invalid log tells whether the original log downloaded is an invalid log (error message).
            'tr_invalid_log': 'invalid_log',
            # Added: The build system used by the project as indicated by the build log.
            'tr_build_system': 'build_system',
        }
        output = {}
        for key in mapping:
            if not hasattr(self, mapping[key]):
                if key in ['tr_log_num_tests_run', 'tr_log_num_tests_failed']:
                    output[key] = 0
                else:
                    output[key] = 'NA'
            else:
                attr = getattr(self, mapping[key])
                if isinstance(attr, list):
                    output[key] = '#'.join(attr)
                else:
                    output[key] = attr
        return output
