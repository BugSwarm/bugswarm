"""
A Mixin for Gradle build log analysis.
"""

import re

from ..base_log_analyzer import LogAnalyzerABC
from ..utils import get_job_lines


class JavaGradleAnalyzer(LogAnalyzerABC):
    def __init__(self, primary_language, folds, job_id):
        super().__init__(primary_language, folds, job_id)
        self.reactor_lines = []
        self.tests_failed_lines = []
        self.analyzer = 'java-gradle'
        self.build_system = 'Gradle'
        # Assume tests did not fail unless we detect that they did.
        self.did_tests_fail = False

    def custom_analyze(self):
        self.extract_tests()
        self.analyze_tests()
        super().custom_analyze()

    def extract_tests(self):
        test_section_started = False
        line_marker = 0
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.M)

        for line in get_job_lines(self.folds):
            line = ansi_escape.sub('', line)
            # We cannot tell when the test started, so we start looking when we have the first task.
            if re.search(r'^:[^/\\:<>"?*|]', line, re.M):
                line_marker = 1
                test_section_started = True
            elif re.search(r'^:', line, re.M) and line_marker == 1:
                line_marker = 0
                test_section_started = False
            elif re.search(r'^> Task', line, re.M):
                # New version of Gradle use > Task :name instead of :name
                line_marker = 1
                test_section_started = True
            elif re.search(r'^BUILD (SUCCESSFUL|FAILED) in ', line, re.M) and line_marker == 1:
                self.test_lines.append(line)  # We still need this line
                line_marker = 0
                test_section_started = False

            if test_section_started:
                self.test_lines.append(line)

    def match_failed_test(self, line):
        # JUnit 4
        # Matches the likes of co.paralleluniverse.fibers.FiberTest > testSerializationWithThreadLocals[0] FAILED
        # Appends 'co.paralle.universe.fibers.FiberTest.testSerializationWithThreadLocals[0]' to self.tests_failed
        # <params> is .* instead of \d+ due to a weird edge case; see GitHubAnalyzerTest.test_gradle_8 for an example
        match = re.match(r'^(?P<class>[\w.]+) > (?P<method>[\w ]+(?P<params>\[.*\])?) FAILED$', line, re.M)
        if match:
            self.tests_run = True
            self.init_tests()
            self.tests_failed.append(match.group('class') + '.' + match.group('method'))
            self.did_tests_fail = True
            return

        # JUnit 5, Gradle >= 8
        # Matches the likes of TestClass1 > shouldThrow() FAILED
        #   (failed test: "TestClass1.shouldThrow()")
        # and TestClass1 > isEven(int, String) > [2] 11, orange FAILED
        #   (failed test: "TestClass1.isEven(int, String)[2]")
        # and UserEndpointTest > GetUserDetail > shouldResponseErrorIfUserNotFound() FAILED
        #   (failed test "UserEndpointTest$GetUserDetail.shouldResponseErrorIfUserNotFound()")
        # TODO: Should we include the actual parameters as well as the index?
        regex = (
            r'(?P<class>[\w.]+(?: > [\w.]+)*) > (?P<method>[\w ]+\([\w, ]*\))(?: > (?P<paramindex>\[\d+\]) '
            r'(?P<params>.*))? FAILED$'
        )
        match = re.match(regex, line, re.M)
        if match:
            self.tests_run = True
            self.init_tests()
            param_index = match.group('paramindex') or ''
            # innermost_test_class = match.group('class').split(' > ')[-1]
            # "OuterClass$InnerClass" is the standard way to denote nested classes in Java
            test_class = match.group('class').replace(' > ', '$')
            self.tests_failed.append(test_class + '.' + match.group('method') + param_index)
            self.did_tests_fail = True
            return

        # JUnit 5, Gradle <= 7
        # Matches the likes of
        # ProtocolCompatibilityTest > serviceTalkToServiceTalkClientTimeout(boolean, boolean, String) > io.servicetalk.g
        # rpc.netty.ProtocolCompatibilityTest.serviceTalkToServiceTalkClientTimeout(boolean, boolean, String)[10] FAILED
        #
        # Appends io.servicetalk.grpc.netty.ProtocolCompatibilityTest.serviceTalkToServiceTalkClientTimeout
        # (boolean, boolean, String)[10] to self.tests_failed
        regex = r'\w+ > \w+\([\w, ]+\) > (?P<classandmethod>[\w. ]+(?P<params>\(.*\)\[\d+\])?) FAILED$'
        match = re.match(regex, line, re.M)
        if match:
            self.tests_run = True
            self.init_tests()
            self.tests_failed.append(match.group('classandmethod'))
            self.did_tests_fail = True
            return

        # Newer TestNG (>= 7?)
        # Matches the likes of Suite Foo > Test Bar > org.bugswarm.TestClass1 > shouldFail FAILED
        # Appends 'org.bugswarm.TestClass1.shouldFail' to self.tests_failed
        regex = r'^[\w\s]+ > [\w\s]+ > (?P<class>\w+\.[\w.]+) > (?P<method>[\w ]+(?P<params>\[\d+\]\(.*\))?) FAILED$'
        match = re.match(regex, line, re.M)
        if match:
            self.tests_run = True
            self.init_tests()
            self.tests_failed.append(match.group('class') + '.' + match.group('method'))
            self.did_tests_fail = True
            return

        # Older TestNG (<= 6?)
        # Matches the likes of TestNG > Regression2 > test.groupinvocation.GroupSuiteTest.Regression2 FAILED
        # Appends 'test.groupinvocation.GroupSuiteTest.Regression2' to self.tests_failed
        # <classandmethod> allows spaces due to an edge case; see TravisAnalyzerTests.test_gradle_7
        regex = r'^[\w\s]+ > [\w\s]+ > (?P<classandmethod>[\w ]+\.[\w. ]+(?P<params>\[\d+\]\(.*\))?) FAILED$'
        match = re.match(regex, line, re.M)
        if match:
            self.tests_run = True
            self.init_tests()
            self.tests_failed.append(match.group('classandmethod'))
            self.did_tests_fail = True
            return

        # TestNG special case: just "path.to.TestClass.testMethod FAILED"
        # A little risky (chance of false positive); mitigated by (a) only checking test lines, (b) requiring a
        # full-line match, and (c) requiring at least one period and no spaces. Doesn't cause any problems for existing
        # artifacts as of October 2024.
        regex = r'^(\w+\.[\w.]+) FAILED$'
        match = re.match(regex, line, re.M)
        if match:
            self.tests_run = True
            self.init_tests()
            self.tests_failed.append(match.group(1))
            self.did_tests_fail = True
            return

    def analyze_tests(self):
        for line in self.test_lines:
            self.match_failed_test(line)

            match = re.search(r'(\d*) tests completed(, (\d*) failed)?(, (\d*) skipped)?', line, re.M)
            if match:
                self.tests_run = True
                self.init_tests()
                self.add_framework('JUnit')
                self.num_tests_run += int(match.group(1))
                self.num_tests_failed += 0 if match.group(3) is None else int(match.group(3))
                self.num_tests_skipped += 0 if match.group(5) is None else int(match.group(5))
                continue
            # Added a space after Total tests run:, this differs from
            # TravisTorrent's original implementation. The observed output
            # of testng has a space. Consider updating the regex if we observe
            # a testng version that outputs whitespace differently.
            match = re.search(r'^Total tests run: (\d+), Failures: (\d+), Skips: (\d+)', line, re.M)
            if match:
                self.tests_run = True
                self.init_tests()
                self.add_framework('testng')
                self.num_tests_run += int(match.group(1))
                self.num_tests_failed += int(match.group(2))
                self.num_tests_skipped += int(match.group(3))
                continue

            # Same with Maven and Ant. Only use the last build to calculate pure_build_duration
            match = re.search(r'Total time: (.*)', line, re.M)
            if match:
                self.pure_build_duration = JavaGradleAnalyzer.convert_gradle_time_to_seconds(match.group(1))

            match = re.search(r'BUILD (FAILED|SUCCESSFUL) in (.*)', line, re.M)
            if match:
                self.pure_build_duration = JavaGradleAnalyzer.convert_gradle_time_to_seconds(match.group(2))

        self.uninit_ok_tests()

    @staticmethod
    def convert_gradle_time_to_seconds(string):
        match = re.search(r'((\d+) mins)? (\d+)(\.\d+) secs', string, re.M)
        if match:
            # If we have minute, we add 60 * minutes to the seconds, final unit is seconds
            return int(match.group(3)) if match.group(2) is None else int(match.group(2)) * 60 + int(match.group(3))

        match = re.search(r'((\d+)m )?(\d+)s', string, re.M)
        if match:
            # If we have minute, we add 60 * minutes to the seconds, final unit is seconds
            return int(match.group(3)) if match.group(2) is None else int(match.group(2)) * 60 + int(match.group(3))

        return 0

    def bool_tests_failed(self):
        if hasattr(self, 'tests_failed') and self.tests_failed:
            return True
        if hasattr(self, 'num_tests_failed') and self.num_tests_failed > 0:
            return True
        return False
