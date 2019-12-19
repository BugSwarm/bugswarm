"""
A Mixin for Ant build log analysis. Also provides reasonable default behavior for all Java-based logs.
"""

import re

from bugswarm.common import log

from ..log_file_analyzer import LogFileAnalyzer


class JavaAntAnalyzer(LogFileAnalyzer):
    def __init__(self, primary_language, folds, job_id):
        super().__init__(primary_language, folds, job_id)
        self.reactor_lines = []
        self.tests_failed_lines = []
        self.analyzer = 'java-ant'
        self.build_system = 'Ant'

    def extract_tests(self):
        test_section_started = False

        # Possible future improvement: We could even get all executed tests (also the ones that succeed).
        for line in self.folds[self.OUT_OF_FOLD]['content']:
            match = re.search(r'\[(junit|testng|test.*)\] ', line)
            if match:
                test_section_started = True

            match = re.search(r'Total time: (.+)', line, re.M)
            if match:
                self.pure_build_duration = JavaAntAnalyzer.convert_ant_time_to_seconds(match.group(1))

            if test_section_started:
                self.test_lines.append(line)

    @staticmethod
    def convert_ant_time_to_seconds(string):
        match = re.search(r'((\d+)(\.\d*)?) s', string, re.M)
        if match:
            # log.debug('test_section_started = true : ', match.group(1))
            return round(float(match.group(1)), 2)

        match = re.search(r'(\d+):(\d+) min', string, re.M)
        if match:
            # log.debug('test_section_started = true : ', match.group(1))
            return int(match.group(1)) * 60 + int(match.group(2))
        return 0

    @staticmethod
    def extract_test_name(string):
        return string.split(':')[0].split('.')[1]

    def analyze_tests(self):
        current_testsuite = ''
        last_testcase = ''
        line_idx = -1
        for line in self.test_lines:
            line_idx += 1
            # This usually comes after a line logging the name of a testcase; this line means that test case failed.
            match = re.search(r'\t(FAILED$|Caused an ERROR$)', line, re.M)
            if match and last_testcase != '':
                self.tests_failed.append(current_testsuite + '.' + last_testcase)
                continue

            # Matches the likes of [junit] Testcase: invalid[Import_Invalid_1] took 0.005 sec
            match = re.search(r'Testcase: (\w+(\[.+\])?) took \d', line, re.M)
            if match:
                last_testcase = match.group(1)
                continue
            last_testcase = ''

            # Matches the likes of [junit] Testsuite: wyc.testing.AllInvalidTest
            match = re.search(r'Testsuite: ([\w.]+)$', line, re.M)
            if match:
                current_testsuite = match.group(1)
                continue

            match = re.search(
                r'Tests run: (\d*), Failures: (\d*), Errors: (\d*), (Skipped: (\d*), )?Time elapsed: (.*)', line, re.M)
            # Some logs print the JUnit summary twice on consecutive lines. We want to avoid double-counting.
            if match and (line_idx == 0 or self.test_lines[line_idx - 1] != line):
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.num_tests_run += int(match.group(1))
                self.num_tests_failed += int(match.group(2)) + int(match.group(3))
                if match.group(4):
                    self.num_tests_skipped += int(match.group(5))
                self.test_duration += JavaAntAnalyzer.convert_ant_time_to_seconds(match.group(6))
                continue
            # Added a space after Total tests run:, this differs from
            # TravisTorrent's original implementation. The observed output
            # of testng has a space. Consider updating the regex if we observe
            # a testng version that outputs whitespace differently.
            match = re.search(r'^Total tests run: (\d+), Failures: (\d+), Skips: (\d+)', line, re.M)
            if match:
                self.init_tests()
                self.add_framework('testng')
                self.tests_run = True
                self.num_tests_run += int(match.group(1))
                self.num_tests_failed += int(match.group(2))
                self.num_tests_skipped += int(match.group(3))
                continue
            match = re.search(r'Failed tests:', line, re.M)
            if match:
                continue
        self.uninit_ok_tests()

    def custom_analyze(self):
        self.extract_tests()
        self.analyze_tests()
        self.get_offending_tests()

    def get_offending_tests(self):
        for line in self.tests_failed_lines:
            try:
                test_name = JavaAntAnalyzer.extract_test_name(line)
                self.tests_failed.append(test_name)
            except Exception:
                log.error('Encountered an error while extracting test name.')

    def bool_tests_failed(self):
        if hasattr(self, 'tests_failed') and self.tests_failed:
            return True
        if hasattr(self, 'num_tests_failed') and self.num_tests_failed > 0:
            return True
        return False
