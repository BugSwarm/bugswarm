"""
A Mixin for Maven build log analysis.
"""

import re

from ..log_file_analyzer import LogFileAnalyzer


class JavaMavenAnalyzer(LogFileAnalyzer):
    def __init__(self, primary_language, folds, job_id):
        super().__init__(primary_language, folds, job_id)
        self.reactor_lines = []
        self.tests_failed_lines = []
        self.analyzer = 'java-maven'
        self.build_system = 'Maven'

    def custom_analyze(self):
        self.extract_tests()
        self.analyze_tests()
        self.get_offending_tests()
        self.analyze_reactor()
        # Added by BugSwarm.
        self.extract_err_msg()
        if hasattr(self, 'tests_failed') and len(self.tests_failed) < 1:
            self.extract_failed_tests_from_tests_lines()

    def extract_tests(self):
        test_section_started = False
        reactor_started = False
        line_marker = 0

        # Strip ANSI color codes from lines, since they mess up the regex.
        # Taken from https://stackoverflow.com/a/14693789
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.M)

        # Possible future improvement: We could even get all executed tests (also the ones which succeed)
        for line in self.folds[self.OUT_OF_FOLD]['content']:
            line = ansi_escape.sub('', line)
            if line[:7] == '[ERROR]':
                self.err_lines.append(line[8:])
            if 'usr/local/bin/run.sh:' in line and 'Killed' in line:
                self.err_msg.append(line)
            if '-------------------------------------------------------' in line and line_marker == 0:
                line_marker = 1
            elif re.search(r'\[INFO\] Reactor Summary(:| for)', line, re.M):
                # Matches two kinds of format:
                # [INFO] Reactor Summary for PROJECT_NAME:
                # [INFO] Reactor Summary:
                reactor_started = True
                test_section_started = False
            elif reactor_started and not re.search(r'\[.*\]', line, re.M):
                reactor_started = False
            elif re.search(r' T E S T S', line, re.M) and line_marker == 1:
                line_marker = 2
            elif line_marker == 1:
                match = re.search(r'Building ([^ ]*)', line, re.M)
                if match:
                    if match.group(1) and len(match.group(1).strip()) > 0:
                        pass
                line_marker = 0
            elif '-------------------------------------------------------' in line and line_marker == 2:
                line_marker = 3
                test_section_started = True
            elif '-------------------------------------------------------' in line and line_marker == 3:
                line_marker = 0
                test_section_started = False
            else:
                line_marker = 0

            if test_section_started:
                self.test_lines.append(line)
            elif reactor_started:
                self.reactor_lines.append(line)

    def analyze_reactor(self):
        # Same with Gradle and Ant. Only use the last build to calculate pure_build_duration
        reactor_time = 0
        for line in self.reactor_lines:
            match = re.search(r'\[INFO\] .*test.*? (\w+) \[ (.+)\]', line, re.I)
            if match:
                reactor_time += JavaMavenAnalyzer.convert_maven_time_to_seconds(match.group(2))
            match = re.search(r'Total time: (.+)', line, re.I)
            if match:
                self.pure_build_duration = JavaMavenAnalyzer.convert_maven_time_to_seconds(match.group(1))
        if not hasattr(self, 'test_duration') or (reactor_time > self.test_duration):
            # Search inside the reactor summary: if the subproject's name contains 'test', add its time to reactor_time
            self.test_duration = reactor_time

    @staticmethod
    def convert_maven_time_to_seconds(string):
        match = re.search(r'((\d+)(\.\d*)?) s', string, re.M)
        if match:
            return round(float(match.group(1)), 2)
        match = re.search(r'(\d+):(\d+) min', string, re.M)
        if match:
            return int(match.group(1)) * 60 + int(match.group(2))
        return 0

    # Returns a list of method signatures or an empty list. Therefore, you most likely want to use list.extend() instead
    # of list.append() when storing the results of this method.
    #
    # Extracts test names from lines in the following formats:
    # 1. 'testRadioButton(org.gwtbootstrap3.client.ui.RadioButtonGwt'
    # 2. 'WebClassesFinderTest.testWebClassesFinder:72 » IllegalState Unable to load class...'
    @staticmethod
    def extract_test_method_name(string):
        # Matches line: testAcceptFileWithMaxSize on instance
        # testAcceptFileWithMaxSize(org.apache.struts2.interceptor.FileUploadInterceptorTest)
        # (org.apache.struts2.interceptor.FileUploadInterceptorTest)
        # Extracts test as: testAcceptFileWithMaxSize(org.apache.struts2.interceptor.FileUploadInterceptorTest)
        match = re.search(r'(\w+(\[.+\])?\([\w.$\[\]]+\))', string)
        if match:
            return match.group(1)
        return None

    def analyze_tests(self):
        failed_tests_started = False
        running_test = False
        curr_test = ""

        for line in self.test_lines:
            if re.search(r'(Failed tests:)|(Tests in error:)', line, re.M):
                failed_tests_started = True
            if failed_tests_started:
                self.tests_failed_lines.append(line)
                if len(line.strip()) < 1:
                    failed_tests_started = False

            match = re.search(r'Tests run: .*? Time elapsed: (.* s(ec)?)', line, re.M)
            if match:
                self.init_tests()
                self.tests_run = True
                self.add_framework('JUnit')
                self.test_duration += JavaMavenAnalyzer.convert_maven_time_to_seconds(match.group(1))
                continue

            # To calculate num_tests_run, num_tests_failed, num_tests_skipped,
            # We ignore lines like Tests run: %d, Failures: %d, Errors: %d, Skipped: %d, Time elapsed: %f s - in ...
            # We only match summary lines like
            # Results :
            # ...
            # Tests run: %d, Failures: %d, Errors: %d, Skipped: %d
            match = re.search(r'Tests run: (\d*), Failures: (\d*), Errors: (\d*)(, Skipped: (\d*))?', line, re.M)
            if match:
                running_test = False
                self.init_tests()
                self.add_framework('JUnit')
                self.tests_run = True
                self.num_tests_run += int(match.group(1))
                self.num_tests_failed += (int(match.group(2)) + int(match.group(3)))
                if match.group(4):
                    self.num_tests_skipped += int(match.group(5))
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

            if line[:8] == 'Running ':
                running_test = True
                curr_test = line[8:]

            if running_test and '(See full trace by running task with --trace)' in line:
                self.tests_failed.append(curr_test)

            # Adding cucumber testing framework.
            if 'exec rake cucumber' in line:
                self.add_framework('cucumber')

            match = re.search(r'cucumber (.*) # Scenario:', line, re.M)
            if match:
                self.tests_failed.append(match.group(1))
                continue
        self.uninit_ok_tests()

    def get_offending_tests(self):
        has_indent = False
        for line in self.tests_failed_lines:
            if line[:2] == '  ':
                has_indent = True
            if has_indent and line[:2] != '  ':
                continue
            # Skip the 'Tests run: ..., Failures: ..., Errors: ..., Skipped: ...' summary line to prevent matching
            # 'run:', 'Failures:', 'Errors:', and 'Skipped:' as test names.
            if 'Tests run:' in line:
                continue
            if 'Failed tests:' in line or 'Tests in error:' in line:
                tests = line.split(':')[1].strip()
                if len(tests) > 1:
                    offending_test = JavaMavenAnalyzer.extract_test_method_name(tests)
                    if offending_test is not None:
                        self.tests_failed.append(offending_test)
            else:
                offending_test = JavaMavenAnalyzer.extract_test_method_name(line)
                if offending_test is not None:
                    self.tests_failed.append(offending_test)

    def bool_tests_failed(self):
        if hasattr(self, 'tests_failed') and self.tests_failed:
            return True
        if hasattr(self, 'num_tests_failed') and self.num_tests_failed > 0:
            return True
        return False

    # Remove empty line or useless help line
    def clean_err_msg(self):
        self.err_msg = [line for line in self.err_msg if len(line) >= 2 and line != '-> [Help 1]']

    # self.err_lines are all the lines that start with [ERROR]
    # Convert err_lines into err_msg, all the lines before the `To see the full stack trace` line
    def extract_err_msg(self):
        new_arr = self.err_msg
        for line in self.err_lines:
            if len(line) > 49 and 'To see the full stack trace of the errors' in line:
                break
            else:
                new_arr.append(line)
        self.err_msg = new_arr
        self.clean_err_msg()

    def extract_failed_tests_from_tests_lines(self):
        cur_test_class = ''
        for line in self.test_lines:
            # Matches the likes of:
            # Tests run: 11, Failures: 2, Errors: 0, Skipped: 0, Time elapsed: 0.1 sec <<< FAILURE! - in path.to.TestCls
            match = re.search(r'<<< FAILURE! - in ([\w\.]+)', line, re.M)
            if match:
                cur_test_class = match.group(1)
            elif re.search(r'(<<< FAILURE!|<<< ERROR!)\s*$', line, re.M):
                failedtest = JavaMavenAnalyzer.extract_test_method_name(line)
                if failedtest is None:
                    # Matches the likes of [ERROR] testMethod  Time elapsed: 0.011 sec  <<< FAILURE!
                    # Assuming that cur_test_class == 'path.to.TestCls', sets failedtest to 'testMethod(path.to.TestCls)
                    # '
                    match = re.search(r'^(\[ERROR\] )?(\w+)  Time elapsed:', line, re.M)
                    if match:
                        failedtest = match.group(2) + '(' + cur_test_class + ')'
                if failedtest is None and cur_test_class != '':
                    # Matches the likes of [ERROR] path.to.TestClass.testMethod  Time elapsed: 0.011 sec  <<< FAILURE!
                    # This sets failedtest to 'testMethod(path.to.TestClass)'
                    test_class = re.escape(cur_test_class)
                    match = re.search(r'^(\[ERROR\] )?{}\.(\w+)  Time elapsed:'.format(test_class), line, re.M)
                    if match:
                        failedtest = match.group(2) + '(' + cur_test_class + ')'
                if failedtest is None:
                    # Matches the likes of [ERROR] path.to.TestClass  Time elapsed: 0.011 sec  <<< FAILURE!
                    # This condition is only reached if the name of the test method is not present in the log.
                    # This sets failedtest to '(path.to.TestClass)'
                    match = re.search(r'^(\[ERROR\] )?([\w.]+)  Time elapsed:', line, re.M)
                    if match:
                        failedtest = '(' + match.group(2) + ')'
                if failedtest is not None:
                    self.tests_failed.append(failedtest)
