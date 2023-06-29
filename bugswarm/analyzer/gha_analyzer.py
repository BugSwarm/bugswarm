"""
Provides general language-independent Analyzer for Travis build log files. Dynamically mixes-in the most specific
language Analyzer from the languages packages. If no specific Analyzer is found, it provides basic statistics about any
build process on Travis.
"""

import re

from bugswarm.common import log

from .base_log_analyzer import LogAnalyzerABC


class GitHubLogFileAnalyzer(LogAnalyzerABC):
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
        self.get_os()
        self.analyze_setup_time_before_build()
        ##############################
        self.analyze_status()
        self.get_connection_lines()
        super().custom_analyze()

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
            'Server Error:'
        ]

        terms_to_catch_dep = [
            'could not resolve dependencies',  # Java
            '> could not find',  # Java
            'could not resolve plugin',  # Java
            'one of its dependencies could not be resolved',  # Java
            'could not resolve dependency',  # Javascript
            'non-resolvable import',  # Python
            'installing build dependencies ... error',  # Python
            'could not find a version that satisfies the requirement',  # Python
        ]
        for fold in self.folds:
            for l in self.folds[fold]['content']:
                for t in terms_to_catch_dep:
                    if t in l.lower():
                        self.could_not_resolve_dep = l.strip()

                for t in terms_to_catch:
                    if t.lower() in l.lower():
                        self.connection_lines.append(l.strip())

    def get_os(self):
        if 'Operating System' not in self.folds:
            return
        lines = self.folds['Operating System']['content']
        """
        Example:
        Ubuntu
        18.04.6
        LTS
        """
        if len(lines) < 2:
            return
        # Travis pipeline used codename for OS attribute
        version_to_codename = {'14.04': 'trusty', '16.04': 'xenial', '18.04': 'bionic', '20.04': 'focal',
                               '22.04': 'jammy'}
        if lines[1][:5] in version_to_codename:
            self.os = version_to_codename[lines[1][:5]]

    # Analyze the build log exit status.
    def analyze_status(self):
        self.status = 'unknown'

        # Handle the empty log corner case.
        if not self.folds:
            log.error('The log file is empty.')
            return

        # GitHub Actions will not print out exit codes unless there is an error
        # Check for stopped and terminated.
        for fold in self.folds:
            for line in self.folds[fold]['content']:
                if '##[error]The operation was canceled.' in line:
                    self.status = 'cancelled'
                    return

        # Starting from the last line and moving upward, check if the line has an exitcode.
        out_of_fold_len = len(self.folds[self.OUT_OF_FOLD]['content'])
        for line_index in range(out_of_fold_len - 1, -1, -1):
            line = self.folds[self.OUT_OF_FOLD]['content'][line_index]
            if len(line) > 0:
                match = re.search(r'^##\[error\]Process completed with exit code (\d*)\.', line, re.M)
                if match:
                    self.status = 'ok' if int(match.group(1)) == 0 else 'broken'
                    return
                match = re.search(r'^##\[error\].*failed', line, re.M)
                if match:
                    self.status = 'broken'
                    return

        # No error in the log
        self.status = 'ok'

    # Estimated setup time = time we see the first user custom command - job's start time
    # This approximation doesn't work if we have custom commands before setup/cache actions...
    def analyze_setup_time_before_build(self):
        setup_time = 0
        for fold in self.folds:
            if re.search(r'^Run ', fold, re.M):
                # Check if running action or command
                # Only Gradle has build actions. Maven and Ant need to enter the mvn/ant commands.
                if not re.search(r'^Run [\w|-]+\/[\w|-]+@v?\d+', fold, re.M) or 'gradle-build-action' in fold or \
                        'gradle-command-action' in fold:
                    # Running command, so no more setup
                    break

            if 'duration' in self.folds[fold]:
                setup_time += self.folds[fold]['duration']

        if setup_time > 0 and not hasattr(self, 'setup_time_before_build'):
            self.setup_time_before_build = round(setup_time, 2)
