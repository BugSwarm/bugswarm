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
        return int(re.findall(r'\d+', match.group(0))[0])

    def setup_javascript_tests(self):
        if not self.initialized_tests:
            self.init_tests()
            self.tests_run = True

    def analyze_test_line(self, line, current_name, start):
        mocha_test_name = re.search(r'(\s+)(\d+)\) (.*)(:)?', line)
        continue_mocha_name = re.search(r'(\s+)(.*)(:)?', line)

        if mocha_test_name:
            start = True
            current_name += mocha_test_name.group(3)
        elif start and continue_mocha_name:
            current_name += ' ' + continue_mocha_name.group(2)

        if ':' in line and current_name != '':
            start = False
            self.tests_failed.append(current_name)
            current_name = ''

        return start, current_name

    def extract_test_failures(self):
        test_failures_started = False
        start_name = False
        current_name = ''
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.M)

        for line in self.folds[self.OUT_OF_FOLD]['content']:
            line = ansi_escape.sub('', line)

            mocha_failure = re.search(r'(\d+) failing.*', line)
            mocha_pass_and_time = re.search(r'(\d+) passing \((\d+)(\w+)\).*', line)
            mocha_pending = re.search(r'(\d+) pending.*', line)

            if mocha_failure:
                self.did_tests_fail = True
                self.num_tests_failed += int(mocha_failure.group(1))
                self.num_tests_run += int(mocha_failure.group(1))
                test_failures_started = True
                continue
            elif mocha_pass_and_time:
                self.setup_javascript_tests()
                self.add_framework('mocha')
                self.num_tests_run += int(mocha_pass_and_time.group(1))
                self.test_duration += self.convert_time_to_sec(mocha_pass_and_time)
            elif mocha_pending:
                self.num_tests_skipped += int(mocha_pending.group(1))

            if test_failures_started:
                start_name, current_name = self.analyze_test_line(line, current_name, start_name)

        self.uninit_ok_tests()
