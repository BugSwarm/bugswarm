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
            match = re.search(r'\[(junit|junitlauncher|testng|test.*)\] ', line)
            if match:
                test_section_started = True
            match = re.search(r'\[\w+\] Failures \(\d+\):|\[\w+\] Test run finished', line)
            if match:
                test_section_started = True

            # Same with Maven and Gradle. Only use the last build to calculate pure_build_duration
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

        match = re.search(r'(\d+) ms', string, re.M)
        if match:
            return round(float(match.group(1)) * 0.001, 2)
        return 0

    @staticmethod
    def extract_test_name(string):
        return string.split(':')[0].split('.')[1]

    def analyze_tests(self):
        current_testsuite = ''
        last_testcase = ''
        started_failure = False
        junit5_console_launcher_started = False
        line_idx = -1
        for line in self.test_lines:
            line_idx += 1

            # Matches the likes of Testcase: testMethod(path.to.TestClass):	FAILED
            # and Testcase: testMethod(path.to.TestClass):	Caused an ERROR
            # This adds path.to.TestClass.testMethod to tests_failed
            match = re.search(r'Testcase: (\w+)\(([\w.]+)\):\s(Caused an ERROR|FAILED)', line, re.M)
            if match:
                if match.group(2) == current_testsuite:
                    self.tests_failed.append(current_testsuite + '.' + match.group(1))
                continue

            # This usually comes after a line logging the name of a testcase; this line means that test case failed.
            # This adds path.to.TestClass.testMethod to tests_failed
            match = re.search(r'\t(FAILED$|Caused an ERROR$)', line, re.M)
            if match and last_testcase != '':
                self.tests_failed.append(current_testsuite + '.' + last_testcase)
                continue
            elif match and current_testsuite != '':
                # Matches the likes of
                # Testsuite: path.to.TestClass
                # Testcase: path.to.TestClass:	Caused an ERROR

                # This condition is only reached if the name of the test method is not present in the log.
                # This adds '(path.to.TestClass)' to tests_failed
                self.tests_failed.append('(' + current_testsuite + ')')
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

            # Junitreport, JUnit5
            match = re.search(r'Failures \([0-9]+\):', line, re.M)
            if match:
                started_failure = True
                continue

            # Matches the likes of
            # MethodSource [className = 'className', methodName = 'testMethod', methodParameterTypes = '']
            # This adds path.to.TestClass.testMethod to tests_failed
            match = re.search(
                r'MethodSource \[className = \'([\w.]+)\', methodName = \'(\w+)\', methodParameterTypes = \'.*\']',
                line, re.M
            )
            if match and started_failure:
                self.tests_failed.append(match.group(1) + '.' + match.group(2))
                continue
            # Matches the likes of ClassSource [className = 'className', filePosition = null]
            # This condition is only reached if the name of the test method is not present in the log.
            # This adds '(path.to.TestClass)' to tests_failed
            match = re.search(r'ClassSource \[className = \'([\w.]+)\'.*]', line, re.M)
            if match and started_failure:
                self.tests_failed.append('(' + match.group(1) + ')')
                continue

            if junit5_console_launcher_started:
                match = re.search(r'\[\s+(\d+) tests found\s+\]', line, re.M)
                if match:
                    self.num_tests_run += int(match.group(1))
                    continue
                match = re.search(r'\[\s+(\d+) tests skipped\s+\]', line, re.M)
                if match:
                    self.num_tests_skipped += int(match.group(1))
                    continue
                match = re.search(r'\[\s+(\d+) tests aborted\s+\]', line, re.M)
                if match:
                    self.num_tests_skipped += int(match.group(1))
                    continue
                match = re.search(r'\[\s+(\d+) tests failed\s+\]', line, re.M)
                if match:
                    self.num_tests_failed += int(match.group(1))
                    continue
                match = re.search(r'\[\s+\d+', line, re.M)
                if not match:
                    junit5_console_launcher_started = False

            # JUnit 4
            match = re.search(
                r'Tests run: (\d*), Failures: (\d*), Errors: (\d*), (Skipped: (\d*), )?Time elapsed: (.*)', line, re.M)
            # Some logs print the JUnit summary twice on consecutive lines. We want to avoid double-counting.
            if match and (line_idx == 0 or self.test_lines[line_idx - 1] != line):
                self.init_tests()
                self.add_framework('JUnit')
                num_run = int(match.group(1))
                num_failure = int(match.group(2))
                num_error = int(match.group(3))
                if not (num_run == 0 and num_error == 1):
                    # On Ant, JUnit 4 will return Tests run: 0, Failures: 0, Errors: 1
                    # if the @BeforeClass operation failed.
                    self.tests_run = True
                    self.num_tests_run += num_run
                    self.num_tests_failed += num_failure + num_error
                if match.group(4):
                    self.num_tests_skipped += int(match.group(5))
                self.test_duration += JavaAntAnalyzer.convert_ant_time_to_seconds(match.group(6))
                continue

            # JUnit 5
            match = re.search(
                r'Tests run: (\d*), Failures: (\d*), Aborted: (\d*), Skipped: (\d*), Time elapsed: (.*)', line, re.M)
            if match:
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.num_tests_run += int(match.group(1))
                self.num_tests_failed += int(match.group(2))
                self.num_tests_skipped += int(match.group(3)) + int(match.group(4))
                self.test_duration += JavaAntAnalyzer.convert_ant_time_to_seconds(match.group(5))
                continue

            # JUnit 5
            match = re.search(r'Test run finished after (.*)', line, re.M)
            if match:
                junit5_console_launcher_started = True
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.test_duration += JavaAntAnalyzer.convert_ant_time_to_seconds(match.group(1))

            # TestNG
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
