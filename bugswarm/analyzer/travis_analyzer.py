"""
Provides general language-independent Analyzer for Travis build log files. Dynamically mixes-in the most specific
language Analyzer from the languages packages. If no specific Analyzer is found, it provides basic statistics about any
build process on Travis.
"""

import re

from bugswarm.common import log
from .base_log_analyzer import LogAnalyzerABC


class TravisLogFileAnalyzer(LogAnalyzerABC):
    """
    tests_run = 'NA'
    num_tests_run = 0
    num_tests_failed = 0
    num_tests_ok = 'NA'
    num_tests_skipped = 'NA'
    test_duration = 'NA'
    setup_time_before_build = 0
    """

    def custom_analyze(self):
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
        super().custom_analyze()

    def check_is_invalid_log(self):
        log_not_found_line = '<Error><Code>NoSuchKey</Code><Message>The specified key does not exist.</Message><Key>'
        content = self.folds[self.OUT_OF_FOLD]['content']
        if len(content) > 1:
            if log_not_found_line in content[1]:
                self.invalid_log = content[1].strip()

    def get_connection_lines(self):
        terms_to_catch = [
            'getRepositorySession()',
            "Can't get http",
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
