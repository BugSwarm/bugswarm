"""
Provides general language-independent Analyzer for Travis build log files. Dynamically mixes-in the most specific
language Analyzer from the languages packages. If no specific Analyzer is found, it provides basic statistics about any
build process on Travis.
"""

import re

from bugswarm.common import log


class LogFileAnalyzer(object):
    """
    tests_run = 'NA'
    num_tests_run = 0
    num_tests_failed = 0
    num_tests_ok = 'NA'
    num_tests_skipped = 'NA'
    test_duration = 'NA'
    setup_time_before_build = 0
    """

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

    # Template method pattern. Subclasses implement their own analyses in custom_analyze.
    def analyze(self):
        self.check_is_invalid_log()
        self.get_using_worker()
        self.get_worker_instance()
        self.get_build_image_provision_datetime()
        self.get_os()
        self.get_cookbook_version()
        ##############################
        self.analyze_status()
        self.analyze_setup_time_before_build()
        self.get_connection_lines()
        self.custom_analyze()
        self.pre_output()
        self.sanitize_output()

    # Subclasses must implement their own analyses in this method.
    def custom_analyze(self):
        raise NotImplementedError

    def check_is_invalid_log(self):
        log_not_found_line = '<Error><Code>NoSuchKey</Code><Message>The specified key does not exist.</Message><Key>'
        content = self.folds[self.OUT_OF_FOLD]['content']
        if len(content) > 1:
            if log_not_found_line in content[1]:
                self.invalid_log = content[1].strip()

    def get_connection_lines(self):
        terms_to_catch = [
            'getRepositorySession()',
            'Can\'t get http',
            '404 Not Found',
            'Failed to fetch',
            'MockWebServer',
            'ssl.SSL',
            'Received request:',
            'Unauthorized.',
            'Failed to connect',
            'Connection refused',
            'SocketTimeOut',
            'failed to upload',
            'the requested URL returned error',
            'unknown host',
        ]
        for fold in self.folds:
            for l in self.folds[fold]['content']:
                if 'could not resolve dependencies' in l.lower():
                    self.could_not_resolve_dep = l.strip()
                for t in terms_to_catch:
                    if t.lower() in l.lower():
                        self.connection_lines.append(l.strip())

    def get_cookbook_version(self):
        if 'system_info' not in self.folds:
            return
        found_version = 0
        for l in self.folds['system_info']['content']:
            if 'Cookbooks Version' in l:
                found_version = 1
                continue
            if found_version:
                self.cookbook = l.strip()
                return

    def get_os(self):
        if 'system_info' not in self.folds:
            return
        for l in self.folds['system_info']['content']:
            if 'Codename:' in l:
                self.os = l[9:].strip()
                return

    def get_using_worker(self):
        if self.folds[self.OUT_OF_FOLD]['content']:
            line = self.folds[self.OUT_OF_FOLD]['content'][0]
            if 'Using worker: ' in line:
                self.using_worker = line[14:].strip()

    def get_worker_instance(self):
        if 'worker_info' not in self.folds:
            return
        for l in self.folds['worker_info']['content']:
            if 'instance: ' in l:
                self.worker_instance = l.strip().split(': ')[1]
                return

    def get_build_image_provision_datetime(self):
        if 'system_info' not in self.folds:
            return
        found_provision = 0
        for l in self.folds['system_info']['content']:
            if 'Build image provisioning date and time' in l:
                found_provision = 1
                continue
            if found_provision:
                self.build_image = l.strip()
                return

    # Analyze the build log exit status.
    def analyze_status(self):
        self.status = 'unknown'

        # Handle the empty log corner case.
        if not self.folds[self.OUT_OF_FOLD]['content']:
            log.error('The log file is empty.')
            return

        startline = 0
        if len(self.folds[self.OUT_OF_FOLD]['content']) > 10:
            startline = -10
        for line in self.folds[self.OUT_OF_FOLD]['content'][startline:]:
            match = re.search(r'^Done\. Your build exited with (\d*)', line, re.M)
            if match:
                self.status = 'ok' if int(match.group(1)) == 0 else 'broken'
                return
            match = re.search(r'^Done\. Build script exited with (\d*)', line, re.M)
            if match:
                self.status = 'ok' if int(match.group(1)) == 0 else 'broken'
                return

        # Check for stopped and terminated.
        for fold in self.folds:
            for line in self.folds[fold]['content']:
                if 'Done: Job Cancelled' in line:
                    self.status = 'cancelled'
                    return
                if 'Your build has been stopped' in line:
                    self.status = 'stopped'
                    return
                if 'The build has been terminated' in line:
                    self.status = 'terminated'
                    return

        # Handle corner case for logs without exitcode/status line. Example: 8175854
        # Starting from the last line and moving upward, check if the line has an exitcode.
        out_of_fold_len = len(self.folds[self.OUT_OF_FOLD]['content'])
        for line_index in range(out_of_fold_len - 1, -1, -1):
            line = self.folds[self.OUT_OF_FOLD]['content'][line_index]
            if len(line) > 0:
                match = re.search(r'^The command (.*) exited with (\d*)\.', line, re.M)
                if match:
                    self.status = 'ok' if int(match.group(2)) == 0 else 'broken'
                    return
                else:
                    return

    def analyze_setup_time_before_build(self):
        for fold in self.folds:
            if re.search(r'(system_info|git.checkout|services|before.install)', fold, re.M):
                if 'duration' in self.folds[fold]:
                    if not hasattr(self, 'setup_time_before_build'):
                        self.setup_time_before_build = 0
                    self.setup_time_before_build += self.folds[fold]['duration']

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
                if type(attr) is list:
                    output[key] = '#'.join(attr)
                else:
                    output[key] = attr
        return output

    # Assign function values to variables before outputting.
    def pre_output(self):
        if hasattr(self, 'bool_tests_failed'):
            self.did_tests_fail = self.bool_tests_failed()

    # Perform last-second sanitaztion of variables. Can be used to guarantee invariants.
    def sanitize_output(self):
        if hasattr(self, 'pure_build_duration') and hasattr(self, 'test_duration'):
            if self.pure_build_duration < self.test_duration:
                del self.pure_build_duration
