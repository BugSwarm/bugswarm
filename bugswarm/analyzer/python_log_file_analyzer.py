"""
A Mixin for Python build log analysis. Supports unittest, unittest2, pytest, and nose.
It will report unittest2 and nose as unittest as their outputs are the same.
"""
import re

from .base_log_analyzer import LogAnalyzerABC
from .utils import get_job_lines


class PythonLogFileAnalyzer(LogAnalyzerABC):
    def init_deep(self):
        self.reactor_lines = []
        self.test_lines = []
        self.tests_failed_lines = []
        self.analyzer = 'python'
        self.has_summary = False

    def custom_analyze(self):
        self.init_deep()
        self.extract_tests()
        self.analyze_tests()
        super().custom_analyze()

    def extract_tests(self):
        test_failures_started = False

        # Strip ANSI color codes from lines, since they mess up the regex.
        # Taken from https://stackoverflow.com/a/14693789
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]', re.M)

        # TODO: Possible future improvement: We could even get all executed tests (also the ones which succeed)
        # Do something similar for, e.g., the tox framework?
        lines = get_job_lines(self.folds)
        for line in lines:
            line = ansi_escape.sub('', line)
            match_obj = re.search(r'Ran .* tests? in ', line)
            if match_obj:
                self.has_summary = True
                test_failures_started = True
                continue
            match_obj = re.search(r'==+ (.+) in (.+) seconds ==+', line, re.M)
            if match_obj:
                self.has_summary = True
                test_failures_started = False
                continue
            match_obj = re.search(r'=====+ FAILURES? =====+', line, re.M)
            if match_obj:
                test_failures_started = True
                continue
            if test_failures_started:
                self.tests_failed_lines.append(line)

        if not self.test_lines:
            self.test_lines = map(lambda line: ansi_escape.sub('', line), lines)

    def setup_python_tests(self):
        if not self.initialized_tests:
            self.init_tests()
            self.tests_run = True
            self.force_tests_passed = False
            self.force_tests_failed = False

            # Pytest has a concept of "expected failures" -- tests that are run, but where the test's outcome shouldn't
            # affect the entire suite's outcome (e.g., tests for unimplemented features). xfailed == the test failed
            # (as expected); xpassed == the test passed (unexpected, but not an error).
            self.num_tests_xfailed = 0
            self.num_tests_xpassed = 0

    def uninit_ok_tests(self):
        if hasattr(self, 'num_tests_ok'):
            super().uninit_ok_tests()
            self.num_tests_ok -= self.num_tests_xfailed + self.num_tests_xpassed

    def analyze_pytest_status_info_list(self, s):
        if not s:
            return
        additional_information = s.split(', ')
        for a in additional_information:
            try:
                val, key = a.split(' ')
            except ValueError:
                # Can happen when pytest outputs a "no tests ran" message
                return

            if key.lower() == 'passed':
                self.num_tests_run += int(val)
            elif key.lower() == 'failed' or key.lower()[:5] == 'error':  # errored, errors, or error
                self.num_tests_failed += int(val)
                self.num_tests_run += int(val)
            elif key.lower() == 'xfailed':
                self.num_tests_xfailed += int(val)
                self.num_tests_run += int(val)
            elif key.lower() == 'xpassed':
                self.num_tests_xpassed += int(val)
                self.num_tests_run += int(val)
            elif key.lower() == 'skipped':
                self.num_tests_skipped += int(val)

    def analyze_status_info_list(self, s):
        if not s:
            return
        additional_information = s.split(', ')
        for a in additional_information:
            key, val = a.split('=')
            if key.lower() in ['skip', 'skipped']:
                self.num_tests_skipped += int(val)
            elif key.lower() in ['errors', 'failures', 'error', 'failure']:
                self.num_tests_failed += int(val)

    def analyze_tests(self):
        summary_seen = False
        short_summary_seen = False
        # Ignore the verbose failures in pytest logs unless we see the "===== FAILURES =====" line.
        ignore_pytest_failures = True
        pytest_test_files = []
        summary_tests_failed = []
        last_pytest_file = ''
        for line in self.test_lines:
            summary_seen = False
            if re.search(r'test session starts', line, re.M):
                self.setup_python_tests()
                self.add_framework('pytest')
                continue

            if re.search(r'==+ (FAILURES|ERRORS) ==+', line, re.M) and len(self.tests_failed) == 0:
                ignore_pytest_failures = False
                continue

            if re.search(r'==+ XFAILURES ==+', line, re.M):
                # Pytest xfailures use the same traceback format as failures, but since they're
                # expected to fail we shouldn't count them.
                ignore_pytest_failures = True
                continue

            match_obj = re.search(r'Ran (\d+) tests? in (.+s)', line, re.M)
            if match_obj:
                # Matches the unittest test summary, i.e. 'Ran 3 tests in 0.000s'
                self.setup_python_tests()
                self.add_framework('unittest')
                self.num_tests_run += int(match_obj.group(1))
                self.test_duration += float(match_obj.group(2)[:-1])
                self.has_summary = True
                summary_seen = True
                continue
            match_obj = re.search(r'=+ (.+) in ([0-9\.]+)(?:s[ )(0-9:]*| seconds) =+', line, re.M)
            if match_obj:
                # Matches the pytest test summary, now compatible with pytest 6 formatting
                # i.e. '==================== 442 passed, 2 xpassed in 50.65 seconds ===================='
                # OR '==== 20 failed, 9721 passed, 23 skipped, 1908 warnings in 541.28s (0:09:01) ====
                self.setup_python_tests()
                self.add_framework('pytest')
                self.analyze_pytest_status_info_list(match_obj.group(1))
                self.test_duration += float(match_obj.group(2))
                self.has_summary = True
                summary_seen = True
                short_summary_seen = False
                if len(self.tests_failed) <= len(summary_tests_failed):
                    # Prefer summary_tests_failed if it contains more failed tests because summary is more accurate.
                    self.tests_failed = summary_tests_failed
                continue
            match_obj = re.search(r'^((?:\d+ [a-z]+)(?:, \d+ [a-z]+)*) in ([0-9\.]+)(?:s( \([0-9:]+\))?| seconds)$',
                                  line, re.M)
            if match_obj:
                # Matches the pytest test summary when run with the --quiet switch
                # e.g. '1 failed, 164 passed, 13 skipped, 2781 deselected in 99.88s (0:01:39)'
                self.setup_python_tests()
                self.add_framework('pytest')
                self.analyze_pytest_status_info_list(match_obj.group(1))
                self.test_duration += float(match_obj.group(2))
                self.has_summary = True
                summary_seen = True
                short_summary_seen = False
                if len(self.tests_failed) <= len(summary_tests_failed):
                    # Prefer summary_tests_failed if it contains more failed tests because summary is more accurate.
                    self.tests_failed = summary_tests_failed
                continue
            match_obj = re.search(r'^OK( \((.+)\))?\s*$', line, re.M)
            if match_obj and self.has_summary:
                # This is a somewhat dangerous thing to do as 'OK' might be a common line in builds.
                # We mititgate the risk somewhat by having seen a summary
                self.setup_python_tests()
                # If we see this, we know that the overall result was that tests passed
                self.force_tests_passed = True
                self.analyze_status_info_list(match_obj.group(2))
                summary_seen = True
                continue
            match_obj = re.search(r'^FAILED( \((.+)\))?\s*$', line, re.M)
            if match_obj and self.has_summary:
                # This is a somewhat dangerous thing to do as 'FAILED' might be a common line in builds.
                # We mititgate the risk somewhat by having seen a summary
                self.setup_python_tests()
                # If we see this, we know that the overall result was that tests passed
                self.force_tests_passed = False
                self.force_tests_failed = True
                self.analyze_status_info_list(match_obj.group(2))
                summary_seen = True
                continue
            # Used to extract failing tests for unittest, unittest2, and nose
            match_obj = re.search(r'^(ERROR): (Failure:) ([^( ]+)', line, re.M)
            if match_obj and not summary_seen:
                # Matches the likes of ERROR: Failure: ImportError (No module named 'six')
                self.setup_python_tests()
                self.tests_failed.append(match_obj.group(3))
                continue
            # Used to extract failing tests for unittest, unittest2, and nose
            match_obj = re.search(r'^((FAIL)|(ERROR)): (\S+(\(.+\))? \(\S+\))', line, re.M)
            if match_obj and not summary_seen:
                # Matches the likes of FAIL: test_em (__main__.TestMarkdownPy)
                self.setup_python_tests()
                self.tests_failed.append(match_obj.group(4))
                continue
            # Used to extract failing tests for unittest, unittest2, and nose
            match_obj = re.search(r'^(FAIL|ERROR):( Doctest:)? ([\w\.]+(\(.+\))?)$', line, re.M)
            if match_obj and not summary_seen:
                # Matches the likes of FAIL: sklearn.tests.test_all_estimators('GMM', <class 'sklearn.mixture.gmm.GMM'>)
                self.setup_python_tests()
                self.tests_failed.append(match_obj.group(3))
                continue

            # For pytest
            # Used to check ===== short test summary info =====
            # Without this, test_python_4 will fail.
            match_obj = re.search(r'=====+ short test summary info =====+', line, re.M)
            if match_obj:
                # We have short test summary, we can use it instead
                short_summary_seen = True
                summary_tests_failed = []
                continue

            if short_summary_seen:
                match_obj = re.search(r'^(FAILED|ERROR) ([\w\/.]+)\.py::([\w:]+)(\[.+\])?', line, re.M)
                if match_obj:
                    # Matches the likes of
                    # FAILED gammapy/irf/psf/tests/test_parametric.py::test_psf_king_containment_radius
                    # Appends gammapy.irf.psf.tests.test_parametric::test_psf_king_containment_radius to tests_failed
                    # Or FAILED gammapy/irf/edisp/tests/test_map.py::test_edisp_from_diagonal_response[0d 0d]
                    # Appends gammapy.irf.edisp.tests.test_map::test_edisp_from_diagonal_response[0d 0d]
                    test_file = match_obj.group(2).replace('/', '.')
                    test_method = match_obj.group(3).replace('.', '::')
                    failed_test = test_file + '::' + test_method
                    if match_obj.group(4) is not None:
                        failed_test += match_obj.group(4)
                    summary_tests_failed.append(failed_test)
                    continue
                match_obj = re.search(r'^(FAILED|ERROR) ([\w\/.]+)\.py', line, re.M)
                if match_obj:
                    # class error, no method name
                    test_file = match_obj.group(2).replace('/', '.')
                    summary_tests_failed.append('(' + test_file + ')')

            # Used to extract failing tests for verbose pytest logs
            match_obj = re.search(r'^([\w\/]+)\.py((::\w+)+)(\[.+\])? FAILED(\s+\[\s*\d+%\])?$', line, re.M)
            if match_obj and not summary_seen:
                # Matches the likes of tests/test_client.py::SSHClientTest::test_host_key_1[1_0_empty] FAILED    [ 65%]
                self.setup_python_tests()
                test_file = match_obj.group(1).replace('/', '.')
                test_method = match_obj.group(2)
                failed_test = test_file + test_method
                if match_obj.group(4) is not None:
                    failed_test += match_obj.group(4)
                self.tests_failed.append(failed_test)
                continue

            # Used to extract failing doctests in verbose pytest logs (as in test_python_15)
            match_obj = re.search(r'^([\w\/]+)\.py::([\w\.]+)(\[.+\])? FAILED(\s+\[\s*\d+%\])?$', line, re.M)
            if match_obj and not summary_seen:
                # Matches the likes of joblib/shelf.py::joblib.shelf.shelve_mmap FAILED      [  0%]
                # Appends 'joblib.shelf::shelve_mmap' to self.tests_failed
                self.setup_python_tests()
                test_file = match_obj.group(1).replace('/', '.')
                test_method = match_obj.group(2)[len(test_file):].replace('.', '::')
                failed_test = test_file + test_method
                if match_obj.group(3) is not None:
                    failed_test += match_obj.group(3)
                self.tests_failed.append(failed_test)
                continue

            # Used to extract failing test *files* for pytest
            match_obj = re.search(r'^([\w\/]+)\.py ([FEXxs.]+)', line, re.M)
            if match_obj and not summary_seen:
                # Matches the likes of tests/h/oauth/jwt_grant_token_test.py ...F........FFFFFF.......FF
                # Appends 'tests.h.oauth.jwt_grant_token_test' to pytest_test_files 9 times
                last_pytest_file = match_obj.group(1).replace('/', '.')
                pytest_test_files += [last_pytest_file] * match_obj.group(2).count('F')
                continue

            match_obj = re.search(r'\[ \d+\%\] (FAILED|ERROR) ([\w\/.]+)\.py::([\w:]+)(\[.+\])?', line, re.M)
            if match_obj and not summary_seen:
                # Matches the likes of [ 88%] FAILED tests/integration/test_mongodb.py::TestMongoCache::test_ttl
                # Appends 'tests.integration.test_mongodb::TestMongoCache::test_ttl' to self.tests_failed
                test_file = match_obj.group(2).replace('/', '.')
                test_method = match_obj.group(3).replace('.', '::')
                failed_test = test_file + '::' + test_method
                if match_obj.group(4) is not None:
                    failed_test += match_obj.group(4)
                self.tests_failed.append(failed_test)
                continue

            # Helps extract failing test files
            match_obj = re.search(r'^([FEXxs.]*F[FEXxs.]*)', line, re.M)
            if match_obj and not summary_seen and last_pytest_file != '':
                # Matches the likes of ................F...............s........F.......
                # Appends the last element of pytest_test_files to pytest_test_files 2 times
                pytest_test_files += [last_pytest_file] * match_obj.group(1).count('F')
                continue

            # Used to extract failing tests *classes and methods* for pytest
            match_obj = re.search(r'^_* ((?!summary)[\w\.]+(\[.+\])?) _*$', line, re.M)
            if match_obj and not summary_seen and not ignore_pytest_failures:
                # Matches the likes of __________________________ ReadKeyTest.test_page_down __________________________
                self.setup_python_tests()
                if len(pytest_test_files) > 0:
                    test_method = match_obj.group(1).replace('.', '::')
                    self.tests_failed.append(pytest_test_files[0] + '::' + test_method)
                    pytest_test_files = pytest_test_files[1:]
                else:
                    self.tests_failed.append(match_obj.group(1))
                continue

            # Used to extract failing test *classes and methods* for doctests in pytest logs
            match_obj = re.search(r'^_* \[doctest\] ((?!summary)[\w\.]+(\[.+\])?) _*$', line, re.M)
            if match_obj and not summary_seen and not ignore_pytest_failures:
                # Matches the likes of ___________ [doctest] sklearn.cluster.bicluster.SpectralCoclustering ___________
                # Appends 'sklearn.cluster.bicluster::SpectralCoclustering' to self.tests_failed,
                # assuming the relevant file is 'sklearn/cluster/bicluster.py'
                self.setup_python_tests()
                if len(pytest_test_files) > 0:
                    test_file = pytest_test_files[0]
                    test_method = match_obj.group(1)[len(test_file):].replace('.', '::')
                    self.tests_failed.append(test_file + test_method)
                    pytest_test_files = pytest_test_files[1:]
                else:
                    self.tests_failed.append(match_obj.group(1))
                continue

            # Used to extract errored test *files* for pytest
            # class error, no method name
            match_obj = re.search(r'^_+ ERROR (\w+ )?([\w\/.-]+?)(\.py)? _+$', line, re.M)
            if match_obj and not summary_seen:
                # Matches the likes of _______________ ERROR collecting test/unittests/tts/test_tts.py ________________
                # Appends '(test.unittests.tts.test_tts)' to self.tests_failed
                self.setup_python_tests()
                test_file = match_obj.group(2).replace('/', '.')
                self.tests_failed.append('(' + test_file + ')')
                continue

        self.uninit_ok_tests()

    def bool_tests_failed(self):
        if hasattr(self, 'force_tests_failed') and self.force_tests_failed:
            return True
        if hasattr(self, 'tests_failed') and self.tests_failed:
            return True
        if hasattr(self, 'num_tests_failed') and self.num_tests_failed > 0:
            return True
        if hasattr(self, 'force_tests_passed') and self.force_tests_passed:
            return False
        return False
