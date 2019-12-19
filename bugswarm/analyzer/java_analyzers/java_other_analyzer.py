import re

from ..log_file_analyzer import LogFileAnalyzer


class JavaOtherAnalyzer(LogFileAnalyzer):
    def __init__(self, primary_language, folds, job_id, build_system):
        super().__init__(primary_language, folds, job_id)
        self.tests_failed_lines = []
        self.analyzer = 'java-other'
        self.build_system = build_system
        self.did_tests_fail = False

    def convert_time_to_seconds(self, hrs, min, sec):
        return float(hrs) * 3600 + float(min) * 60 + float(sec)

    def extract_trigger_sha(self):
        if 'git.checkout' in self.folds:
            for line in self.folds['git.checkout']['content']:
                match = re.search(r'^\$ git checkout -qf .+', line, re.M)
                if match:
                    self.commit = match.group(0).split(" ")[-1]
                    break

    def analyze_tests(self):
        failed_tests_started = False

        for line in self.folds['out_of_fold']['content']:
            # play
            run_results = re.search(
                r'(Passed|Failed): Total (\d+), Failed (\d+), Errors (\d+), Passed (\d+)(, Skipped (\d+))?', line, re.M)
            # None
            num_failed_tests = re.search(r'Tests run: (\d+), Failures: (\d+)', line, re.M)
            # None
            num_passed_tests = re.search(r'OK \((\d+) tests\)', line, re.M)
            if run_results:
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.num_tests_run = int(run_results.group(2))
                self.num_tests_failed = int(run_results.group(3)) + int(run_results.group(4))
                if run_results.group(6):
                    self.num_tests_skipped = int(run_results.group(7))
                continue
            elif num_failed_tests:
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.num_tests_run = int(num_failed_tests.group(1))
                self.num_tests_failed = int(num_failed_tests.group(2))
                continue
            elif num_passed_tests:
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.num_tests_run = int(num_passed_tests.group(1))
                self.num_tests_failed = 0
                continue
            # play
            failed_tests_started = re.search(r'Failed tests:', line, re.M)
            if failed_tests_started:
                continue
            # play
            test_name = re.search(r'\t(.*)', line, re.M)
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

            if failed_tests_started and test_name:
                self.tests_failed_lines.append(test_name.group(1))
                continue

        self.uninit_ok_tests()

    def custom_analyze(self):
        self.analyze_tests()
        self.extract_trigger_sha()
