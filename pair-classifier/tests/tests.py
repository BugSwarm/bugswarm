import unittest
import sys

sys.path.append("../")
from pair_classifier.classify_bugs import process_error  # noqa: E402


class Test(unittest.TestCase):
    @staticmethod
    def read_file_to_list(log_path):
        lines = []
        with open(log_path) as f:
            for line in f:
                lines.append(line.rstrip())
        return lines

    def compare_error_dict(self, result: dict, should_be: dict):
        self.assertDictEqual(should_be, result)

    def compare_user_def_error(self, result: list, should_be: list):
        result, should_be = set(result), set(should_be)
        self.assertSetEqual(should_be, result)

    def compare_confidence(self, result: float, should_be: float):
        # print(result, should_be)
        self.assertEqual(should_be, result)

    def test_java_mvn_process_error_1(self):
        log = "334968079.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {"NullPointerException": 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_mvn_process_error_2(self):
        log = "71816517.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'NullPointerException': 2})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_mvn_process_error_3(self):
        log = "90868641.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'NullPointerException': 4})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_mvn_process_error_4(self):
        log = "255051211.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'NullPointerException': 146})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_mvn_process_error_5(self):
        log = "93618854.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'NullPointerException': 38,
                                             'IllegalStateException': 24, 'UnsupportedOperationException': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_mvn_process_error_6(self):
        log = "123642638.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'InvocationTargetException': 1, 'NullPointerException': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_mvn_process_error_7(self):
        log = "201546728.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'IllegalStateException': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_process_error_1(self):
        log = "84151798.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'UnboundLocalError': 2, 'URLError': 3})
        self.compare_user_def_error(user_def_errors, ['URLError'])

    def test_python_process_error_2(self):
        log = "387279901.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_process_error_3(self):
        log = "163925598.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_process_error_4(self):
        log = "79576031.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'TypeError': 39})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_unittest_process_error_5(self):
        log = "109227526.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'UnicodeDecodeError': 1, 'AssertionError': 2, 'BadRequestKeyError': 2})
        self.compare_user_def_error(user_def_errors, ['BadRequestKeyError'])

    def test_python_unittest_process_error_6(self):
        log = "71127915.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'PermissionError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_unittest_process_error_7(self):
        log = "83097609.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_unittest_process_error_8(self):
        log = "107475404.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_unittest_process_error_9(self):
        log = "356963348.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 2})
        self.compare_user_def_error(user_def_errors, [])

    # def test_python_unittest_process_error_10(self):
    #     log = "367963035.log"
    #     file_path = "logs/" + log
    #     lines = self.read_file_to_list(file_path)
    #     lang = "python"
    #     error_dict, user_def_errors, confidence = process_error(lang, lines)
    #     self.compare_error_dict(error_dict, {'ImportError': 1, 'ValueError': 1})
    #     self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_1(self):
        log = "360721043.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 10})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_2(self):
        log = "214979627.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_3(self):
        log = "331910347.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AttributeError': 4})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_4(self):
        log = "316134246.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'TypeError': 10, 'SystemExit': 10, 'RuntimeError': 4})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_5(self):
        log = "405742384_modified.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 8, 'FooBar': 36})
        self.compare_user_def_error(user_def_errors, ['FooBar'])

    def test_python_pytest_process_error_6(self):
        log = "83739366.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'TemplateSyntaxError': 5})
        self.compare_user_def_error(user_def_errors, ['TemplateSyntaxError'])

    def test_python_pytest_process_error_7(self):
        log = "107125259.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 1, 'AttributeError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_8(self):
        log = "389597748.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 6, 'SystemExit': 2})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_9(self):
        log = "403765814.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'DocTestFailure': 1})
        self.compare_user_def_error(user_def_errors, ['DocTestFailure'])

    def test_python_pytest_process_error_10(self):
        log = "330142563.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_11(self):
        log = "46673191.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'SyntaxError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_12(self):
        log = "375673938.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'ModuleNotFoundError': 94, 'ImportError': 28})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_13(self):
        log = "287718761.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'PicklingError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_process_error_14(self):
        log = "344823668.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'SyntaxError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_python_pytest_successful_build(self):
        log = "405750843.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "python"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {})
        self.compare_user_def_error(user_def_errors, [])

    # Test whether "Exception1 at [...] Caused By: Exception2 at [...]" is counted correctly in Maven logs.
    def test_java_mvn_causedby_process_error_1(self):
        log = "110208140.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'ComponentLookupException': 2, 'ProvisionException': 2})
        self.compare_user_def_error(user_def_errors, ['ProvisionException', 'ComponentLookupException'])

    def test_java_mvn_causedby_process_error_2(self):
        log = "166980116.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {
            'NullPointerException': 2, 'ExecutionException': 1, 'YamcsApiException': 1})
        self.compare_user_def_error(user_def_errors, ['YamcsApiException'])

    # Test whether the classifier catches exception names that don't end in 'Exception' or 'Error'.
    def test_java_mvn_nonstandard_name_process_error(self):
        log = "108400121.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'ArgumentsAreDifferent': 1})
        self.compare_user_def_error(user_def_errors, ['ArgumentsAreDifferent'])

    # Test whether the classifier identifies traces of the form "[INFO] java.lang.NullPointerException" (or similar)
    def test_java_mvn_text_before_exception_process_error(self):
        log = "75144750.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'ExceptionInInitializerError': 1,
                                             'RuntimeException': 2, 'InternalCompilerException': 2,
                                             'HostedModeException': 2})
        self.compare_user_def_error(user_def_errors, ['InternalCompilerException', 'HostedModeException'])

    # Test whether the classifier counts exceptions that are subclasses of other classes.
    # These come in the format "ParentClass$SubClass".
    def test_java_mvn_exception_is_subclass_process_error(self):
        log = "136259688.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertFailedException': 1})
        self.compare_user_def_error(user_def_errors, ['AssertFailedException'])

    def test_java_mvn_semicolon_after_exception_process_error(self):
        log = "102665470.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'SAXParseException': 1})
        self.compare_user_def_error(user_def_errors, [])

    # Edge case: in 408889048.log, there is no exception at the start of the stack trace after the "<<< FAILURE!".
    # Instead, there is an explanation of
    # what went wrong. The rest of the stack trace proceeds normally, with a "Caused by: java.lang.AssertionError"
    # some way down the trace. This test makes sure that AssertionError is counted.
    def test_java_mvn_no_initial_exception(self):
        log = "408889048.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_gradle_process_error_1(self):
        log = "114302339.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'NullPointerException': 11, 'AssertionError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_gradle_process_error_2(self):
        log = "67967396.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'TimeoutException': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_gradle_process_error_3(self):
        log = "64373562.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'NullPointerException': 2})
        self.compare_user_def_error(user_def_errors, [])

    # Test whether "Exception1 at [...] Caused By: Exception2 at [...]" is counted correctly in Gradle logs.
    def test_java_gradle_causedby_process_error_1(self):
        log = "64037267.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'RuntimeException': 1, 'TimeoutException': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_gradle_causedby_process_error_2(self):
        log = "144826559.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'RuntimeException': 70, 'NoSuchMethodException': 71, 'AssertionError': 3})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_gradle_causedby_process_error_3(self):
        log = "63073864.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'NullPointerException': 46})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_gradle_sameline_process_error(self):
        log = "358767427.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'AssertionError': 1})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_ant_process_error(self):
        log = "233645906.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'RuntimeException': 52})
        self.compare_user_def_error(user_def_errors, [])

    # Test to make sure that no errors are counted on successful builds
    # (with no stack traces in their logs).
    def test_java_mvn_successful_build(self):
        log = "95797603.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {})
        self.compare_user_def_error(user_def_errors, [])

    # Some logs of successful builds have stack traces from exceptions that don't make the build fail.
    # Since the classifier is only supposed to find exceptions that make the build fail,
    # it shouldn't count exceptions from those stack traces.
    def test_java_mvn_successful_build_with_stacktraces(self):
        log = "232256103.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {})
        self.compare_user_def_error(user_def_errors, [])

    # Same as test_java_mvn_successful_build, but with a log from a Gradle build.
    def test_java_gradle_successful_build(self):
        log = "64374491.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {})
        self.compare_user_def_error(user_def_errors, [])

    # Same as test_java_mvn_successful_build_with_stacktraces, but with a log from a Gradle build.
    def test_java_gradle_successful_build_with_stacktraces(self):
        log = "67980613.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {})
        self.compare_user_def_error(user_def_errors, [])

    # Same as test_java_mvn_successful_build, but with a log from an Ant build.
    def test_java_ant_successful_build(self):
        log = "233655405.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {})
        self.compare_user_def_error(user_def_errors, [])

    # Make sure the classifier doesn't count function names ending with 'exception' or 'error' as exceptions.
    # (The log this tests references a function called 'sqlException'.)
    def test_java_mvn_funcname_process_error(self):
        log = "290369132.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {'NullPointerException': 31})
        self.compare_user_def_error(user_def_errors, [])

    def test_java_mvn_bare_exception_no_causedby(self):
        log = "117115625.log"
        file_path = "logs/" + log
        lines = self.read_file_to_list(file_path)
        lang = "java"
        error_dict, user_def_errors, confidence = process_error(lang, lines)
        self.compare_error_dict(error_dict, {
            'NullPointerException': 53, 'PersistenceException': 46, 'BuilderException': 46,
            'Exception': 1})
        self.compare_user_def_error(user_def_errors, ['PersistenceException', 'BuilderException'])

    def test_java_mvn_github_actions_log(self):
        log_path = 'logs/6791988572.log'
        lines = self.read_file_to_list(log_path)

        # TODO Once we have the GitHub classifier, we'll want to change this test to use it.
        # Instead, just strip the timestamps and use the Travis classifier.
        lines = [line[29:] for line in lines]

        error_dict, user_def_errors, _ = process_error('java', lines)
        self.compare_error_dict(error_dict, {'StackOverflowError': 1, 'AssertionFailedError': 5})
        self.compare_user_def_error(user_def_errors, [])


if __name__ == '__main__':
    unittest.main()
