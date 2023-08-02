import re

from ..base_log_analyzer import LogAnalyzerABC
from ..utils import get_job_lines


class JavaOtherAnalyzer(LogAnalyzerABC):
    def __init__(self, primary_language, folds, job_id, build_system):
        super().__init__(primary_language, folds, job_id)
        self.tests_failed_lines = []
        self.analyzer = 'java-other'
        self.build_system = build_system
        self.did_tests_fail = False

    def custom_analyze(self):
        self.extract_tests()
        self.analyze_tests()
        super().custom_analyze()

    def convert_time_to_seconds(self, hrs, min, sec):
        return float(hrs) * 3600 + float(min) * 60 + float(sec)

    def extract_tests(self):
        # Strip ANSI color codes from lines, since they mess up the regex.
        # Taken from https://stackoverflow.com/a/14693789
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.M)
        for line in get_job_lines(self.folds):
            # Assume everything is test related
            line = ansi_escape.sub('', line)
            self.test_lines.append(line)

    def analyze_tests(self):
        failed_tests_started = False

        for line in self.test_lines:
            # play
            run_results = re.search(
                r'(Passed|Failed): Total (\d+), Failed (\d+), Errors (\d+), Passed (\d+)(, Skipped (\d+))?', line, re.M)
            # None
            num_failed_tests = re.search(r'Tests run: (\d+), Failures: (\d+)', line, re.M)
            # None
            num_passed_tests = re.search(r'OK \((\d+) tests\)', line, re.M)

            failed_test_match = re.search(r'] Test (.+) failed:', line, re.M)

            if run_results:
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.num_tests_run += int(run_results.group(2))
                self.num_tests_failed += int(run_results.group(3)) + int(run_results.group(4))
                if run_results.group(6):
                    self.num_tests_skipped += int(run_results.group(7))
                continue
            elif num_failed_tests:
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.num_tests_run += int(num_failed_tests.group(1))
                self.num_tests_failed += int(num_failed_tests.group(2))
                continue
            elif num_passed_tests:
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.num_tests_run += int(num_passed_tests.group(1))
                continue
            elif failed_test_match:
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.tests_failed.append(failed_test_match.group(1))

            # play
            if not failed_tests_started:
                match = re.search(r'Failed tests:', line, re.M)
                if match:
                    self.did_tests_fail = True
                    failed_tests_started = True
                    continue

            if failed_tests_started:
                test_name = re.search(r'\t(.*)', line, re.M)
                if test_name:
                    self.tests_failed_lines.append(test_name.group(1))
                else:
                    failed_tests_started = False

            # play
            time_match1 = re.search(r'Total time: (\d+) s, completed .*', line, re.M)
            # None
            time_match2 = re.search(r'Build time: (\d+):(\d+):(\d+)', line, re.M)

            if time_match1:
                failed_tests_started = False
                self.test_duration = float(time_match1.group(1))
            elif time_match2:
                failed_tests_started = False
                self.test_duration = self.convert_time_to_seconds(time_match2.group(1), time_match2.group(2),
                                                                  time_match2.group(3))

        if len(self.tests_failed_lines) > 0 and len(self.tests_failed) == 0:
            # Extract failed tests' class
            for line in self.tests_failed_lines:
                self.tests_failed.append('(' + line + ')')
        self.uninit_ok_tests()

    def bool_tests_failed(self):
        if hasattr(self, 'tests_failed') and self.tests_failed:
            return True
        if hasattr(self, 'num_tests_failed') and self.num_tests_failed > 0:
            return True
        return False
