import re

from .log_file_analyzer import LogFileAnalyzer


class JavaScriptFileAnalyzer(LogFileAnalyzer):

    # LogFileAnalyzer initializes primary language, folds, and job id
    def init_deep(self):
        self.test_lines = []
        self.analyzer = 'javascript'

    def custom_analyze(self):
        self.init_deep()
        self.extract_test_failures()

    def convert_time_to_sec(self, mocha_pass_and_time):
        time = int(mocha_pass_and_time.group(2))
        units = mocha_pass_and_time.group(3)

        if units == 'ms':
            return time / 1000
        elif units == 'm':
            return time * 60
        else:
            # units are s
            return time

    def get_int_from_match(self, match):
        return int(re.findall(r'\d+', match)[0])

    def setup_javascript_tests(self):
        if not self.initialized_tests:
            self.init_tests()
            self.tests_run = True
            self.did_tests_fail = False

    def analyze_test_line(self, line, current_name, start):
        mocha_test_name = re.search(r'(\s+)(\d+)\) (.*)(:)?', line)
        continue_mocha_name = re.search(r'(\s+)(.*)(:)?', line)
        mocha_summary_test_name = re.search(r'(\s+)\u2716\s(.*)', line)

        if mocha_test_name:
            start = True
            current_name += mocha_test_name.group(3)
        elif start and continue_mocha_name:
            current_name += ' ' + continue_mocha_name.group(2)
        elif mocha_summary_test_name:
            self.tests_failed.append(mocha_summary_test_name.group(2))

        if ':' in line and current_name != '':
            start = False
            self.tests_failed.append(current_name)
            current_name = ''

        return start, current_name

    def extract_test_failures(self):
        jest_test_failures_started = False
        mocha_test_failures_started = False
        start_name = False
        current_name = ''
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.M)
        has_summary = False
        summary_time = 0

        for line in self.folds[self.OUT_OF_FOLD]['content']:
            line = ansi_escape.sub('', line)

            mocha_failure = re.search(r'(\d+) failing$', line)
            mocha_pass_and_time = re.search(r'(\d+) passing \((\d+)(\w+)\)$', line)
            mocha_pending = re.search(r'(\d+) pending$', line)
            summary = re.search(r'^SUMMARY:$', line)
            mocha_summary_pass = re.search(r'(\d+) test(s)? completed$', line)
            mocha_summary_skipped = re.search(r'(\d+) test(s)? skipped$', line)
            mocha_summary_failed = re.search(r'(\d+) test(s)? failed$', line)
            mocha_summary_time = re.search(r'Finished in (\d*\.?\d*) secs', line)
            mocha_summary_failed_test = re.search(r'^FAILED TESTS:$', line)

            if mocha_failure:
                self.did_tests_fail = True
                self.num_tests_failed += int(mocha_failure.group(1))
                self.num_tests_run += int(mocha_failure.group(1))
                mocha_test_failures_started = True
                continue
            elif mocha_pass_and_time:
                self.setup_javascript_tests()
                self.add_framework('mocha')
                self.num_tests_run += int(mocha_pass_and_time.group(1))
                self.test_duration += self.convert_time_to_sec(mocha_pass_and_time)
            elif mocha_pending:
                self.num_tests_skipped += int(mocha_pending.group(1))

            if summary:
                has_summary = True
                self.setup_javascript_tests()
                self.test_duration += summary_time
                summary_time = 0
                self.add_framework('mocha')

            if mocha_summary_pass and has_summary:
                self.num_tests_run += int(mocha_summary_pass.group(1))
            elif mocha_summary_skipped and has_summary:
                self.num_tests_skipped += int(mocha_summary_skipped.group(1))
            elif mocha_summary_failed and has_summary:
                self.did_tests_fail = True
                self.num_tests_failed += int(mocha_summary_failed.group(1))
                self.num_tests_run += int(mocha_summary_failed.group(1))
            elif mocha_summary_time:
                summary_time += float(mocha_summary_time.group(1))
            elif mocha_summary_failed_test and has_summary:
                mocha_test_failures_started = True

            if mocha_test_failures_started:
                if len(self.tests_failed) < self.num_tests_failed:
                    start_name, current_name = self.analyze_test_line(line, current_name, start_name)

            jest_tests = re.search(r'Tests:\s+(\d+ failed, )?(\d+ skipped, )?(\d+ passed, )?(\d+ total)', line)
            jest_failing_test = re.search(r'FAIL\s+(.*)', line)
            jest_passing_test = re.search(r'PASS\s+(.*)', line)
            jest_summary = re.search(r'Summary of all failing tests', line)
            jest_failing_test_name = re.search(r'\u25CF\s(.*)', line)
            jest_time = re.search(r'Time:(\s+)(\d*\.?\d*)s(ecs)?$', line)

            if jest_tests:
                if jest_tests.group(4):
                    self.add_framework('jest')
                    jest_total = self.get_int_from_match(jest_tests.group(4))
                    if jest_total == 0:
                        self.tests_failed = []
                        continue
                self.setup_javascript_tests()
                if jest_tests.group(1):
                    self.did_tests_fail = True
                    jest_failed = self.get_int_from_match(jest_tests.group(1))
                    self.num_tests_failed += jest_failed
                    self.num_tests_run += jest_failed
                if jest_tests.group(2):
                    jest_skipped = self.get_int_from_match(jest_tests.group(2))
                    self.num_tests_skipped += jest_skipped
                if jest_tests.group(3):
                    jest_passed = self.get_int_from_match(jest_tests.group(3))
                    self.num_tests_run += jest_passed

            if jest_time and self.tests_run:
                self.test_duration += float(jest_time.group(2))

            if jest_summary or jest_passing_test:
                jest_test_failures_started = False

            if jest_failing_test:
                jest_test_failures_started = True

            if jest_test_failures_started and jest_failing_test_name:
                if jest_failing_test_name.group(1) not in self.tests_failed:
                    self.tests_failed.append(jest_failing_test_name.group(1))

        self.uninit_ok_tests()
