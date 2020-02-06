import unittest

from os import listdir
from os.path import isfile
from os.path import join

from bugswarm.analyzer.analyzer import Analyzer
from bugswarm.analyzer.dispatcher import Dispatcher
from bugswarm.common.travis_wrapper import TravisWrapper


class Test(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(Test, self).__init__(*args, **kwargs)
        self.dispatcher = Dispatcher()
        self.travis_wrapper = TravisWrapper()
        self.analyzer = Analyzer()

    def get_trigger_sha_and_repo(self, job_id):
        with self.travis_wrapper as tw:
            info = tw.get_job_info(job_id)
        trigger_sha = info["commit"]
        url = info["compare_url"]
        url = url.split("/")
        repo = url[3] + "/" + url[4]
        return trigger_sha, repo

    @staticmethod
    def my_split(l):
        arr = []
        i_start = 0
        in_quote = 0
        for i_curr in range(len(l)):
            if l[i_curr] == "," and in_quote == 0:
                w = l[i_start:i_curr]
                arr.append(w)
                i_start = i_curr + 1
            elif l[i_curr] == "\"":
                if in_quote:
                    in_quote = 0
                else:
                    in_quote = 1
            elif i_curr == len(l) - 1:
                w = l[i_start:i_curr]
                arr.append(w)
        return arr

    @staticmethod
    def remove_quote(s):
        if type(s) is str:
            if len(s) > 2:
                if s[0] == "\"" and s[len(s) - 1] == "\"":
                    return s[1:len(s) - 1]
        return s

    def read_csv(self, csvfile):
        read_header = 0
        header = []
        data = []
        rows = 0
        with open(csvfile) as f:
            for l in f:
                rows += 1

                if not read_header:
                    splitted = l.strip().split(",")
                    [header.append(h) for h in splitted]
                    read_header = 1
                else:
                    splitted = self.my_split(l)
                    splitted = list(map(self.remove_quote, splitted))
                    temp = {}
                    i = 0
                    for s in splitted:
                        if i < len(header):
                            # print (i)
                            temp[header[i]] = s
                            i += 1
                    data.append(temp)
        return data

    @staticmethod
    def strip_quote(string):
        return string.replace('"', "")

    def compare_with_tt(self, my_result, tt_data):
        """
        deprecated - compare results with TravisTorrent data
        """

        tt_result = [d for d in tt_data if d["tr_build_id"] == my_result["tr_build_id"]][0]
        for k in my_result:
            my = str(my_result[k]).lower()
            tt = tt_result[k].lower()
            if my != tt:
                if my == "na" and tt == "\"\"":
                    continue

                if my == "" and tt == "\"\"":
                    continue

                if my == "na" and tt == "":
                    continue

                if k == "tr_log_bool_tests_failed" and my == "false" and tt == "":
                    continue

                if type(my_result[k]) is float:
                    # print (k)
                    # print (my)
                    # print (tt)
                    if (float(my) - float(tt)) <= 0.01:
                        continue

                if k == "tr_log_num_tests_failed" and my_result["tr_log_analyzer"] == "java-gradle":
                    if my == "na" and tt == "0":
                        continue

                if k == "tr_log_tests_failed":
                    my_failed_tests = my.split("#")
                    tt_failed_tests = tt.split("#")
                    my_failed_tests = list(map(self.strip_quote, my_failed_tests))
                    tt_failed_tests = list(map(self.strip_quote, tt_failed_tests))
                    if my_failed_tests == tt_failed_tests:
                        continue
                    else:
                        print(my_failed_tests)
                        print(tt_failed_tests)

                print(k, " UNMATCH ", my, "|", tt)
                return False  # (1, tt_result)
        return True

    def load_travistorrent_analyzer_result_csv(self):
        """
        deprecated
        :return:
        """
        travis_csvfile = '2181java_BLA_result.csv'
        self.travis_result = self.read_csv(travis_csvfile)
        # @with_setup(load_travistorrent_analyzer_result_csv)
        # def test_compare_with_travistorrent_analyzer_result_csv(self):
        #     self.load_travistorrent_analyzer_result_csv()
        #     logs_folder = "logs/"
        #     count = 0
        #
        #     for log in listdir(logs_folder):
        #         file_path = join(logs_folder, log)
        #         if isfile(file_path) and log[-4:] == ".log":
        #
        #             result = self.buildlog_analyzer_dispatcher.analyze(file_path)
        #             if result:
        #                 count += 1
        #                 self.check_match(result, self.travis_result)
        #
        #     self.assertEqual(count, 1628)

    # detect_logs_with_build_language_not_in_java
    def test_analyze_primary_language_1(self):
        logs_folder = "build_language_not_java/"
        for log in listdir(logs_folder):
            file_path = join(logs_folder, log)
            if isfile(file_path) and log[-4:] == ".log":
                lines = Dispatcher.read_log_into_lines(file_path)
                folds = Dispatcher.split(lines)
                primary_language = Dispatcher.analyze_primary_language(folds)
                self.check_build_language_not_java(primary_language)

    # detect_logs_with_build_language is ruby
    def test_analyze_primary_language_2(self):
        logs_folder = "ruby/"
        for log in listdir(logs_folder):
            file_path = join(logs_folder, log)
            if isfile(file_path) and log[-4:] == ".log":
                lines = Dispatcher.read_log_into_lines(file_path)
                folds = Dispatcher.split(lines)
                primary_language = Dispatcher.analyze_primary_language(folds)
                self.check_build_language(primary_language, "ruby")

    # detect_logs_with_build_language is unknown
    def test_analyze_primary_language_3(self):
        logs_folder = "unknowns/"
        for log in listdir(logs_folder):
            file_path = join(logs_folder, log)
            if isfile(file_path) and log[-4:] == ".log":
                lines = Dispatcher.read_log_into_lines(file_path)
                folds = Dispatcher.split(lines)
                primary_language = Dispatcher.analyze_primary_language(folds)
                self.check_build_language(primary_language, "unknown")

    def test_detect_analyzer_gradle(self):
        logs_folder = "gradle/"
        for log in listdir(logs_folder):
            file_path = join(logs_folder, log)
            if isfile(file_path) and log[-4:] == ".log":
                job_id = log.split("-")[0]
                ts, r = self.get_trigger_sha_and_repo(job_id)
                result = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
                self.compare_analyzer(result, "java-gradle")

    def compare_status(self, result, should_be):
        self.assertEqual(result["tr_log_status"], should_be)

    def compare_analyzer(self, result, should_be):
        self.assertEqual(result["tr_log_analyzer"], should_be)

    def compare_build_system(self, result, should_be):
        self.assertEqual(result['tr_build_system'], should_be)

    def compare_frameworks(self, result, should_be):
        self.assertEqual(result["tr_log_frameworks"], should_be)

    def compare_bool_t_ran(self, result, should_be):
        self.assertEqual(result["tr_log_bool_tests_ran"], should_be)

    def compare_bool_t_failed(self, result, should_be):
        self.assertEqual(result["tr_log_bool_tests_failed"], should_be)

    def compare_num_t_ok(self, result, should_be):
        self.assertEqual(result["tr_log_num_tests_ok"], should_be)

    def compare_num_t_failed(self, result, should_be):
        self.assertEqual(result["tr_log_num_tests_failed"], should_be)

    def compare_num_t_run(self, result, should_be):
        self.assertEqual(result["tr_log_num_tests_run"], should_be)

    def compare_num_t_skipped(self, result, should_be):
        self.assertEqual(result["tr_log_num_tests_skipped"], should_be)

    def compare_t_failed(self, result, should_be):
        self.assertEqual(result["tr_log_tests_failed"], should_be)

    def compare_tr_t_failed(self, result, should_be):
        self.assertEqual(result['tr_log_tests_failed'], should_be)

    def compare_t_duration(self, result, should_be):
        self.assertTrue(self.assert_equal_tolerance(result["tr_log_testduration"], should_be))

    @staticmethod
    def assert_equal_tolerance(p1, p2):
        if p1 - p2 <= 0.01:
            return True
        return False

    def compare_buildduration(self, result, should_be):
        self.assertTrue(self.assert_equal_tolerance(result["tr_log_buildduration"], should_be))

    def check_build_language(self, build_log_lang, lang):
        self.assertEqual(build_log_lang, lang)

    def check_build_language_not_java(self, lang):
        self.assertNotEqual(lang, "java")

    def check_match(self, my_result, travis_result):
        self.assertTrue(self.compare_with_tt(my_result, travis_result))

    def compare_rc_match(self, result, should_be):
        self.assertEqual(result[0], should_be)

    def compare_rc_tr_t_failed(self, actual_repr, actual_orig, expected_repr, expected_orig):
        self.assertEqual(set(actual_repr), set(expected_repr))
        self.assertEqual(set(actual_orig), set(expected_orig))

    def compare_rc_mismatch(self, attr_name, result, expected_repr, expected_orig):
        for attr in result[1]:
            if attr['attr'] == attr_name:
                target_attr = attr
                break
        else:
            self.fail('Result does not have attr "{}"'.format(attr_name))

        if attr_name == 'tr_log_tests_failed':
            self.compare_rc_tr_t_failed(target_attr["reproduced"], target_attr["orig"], expected_repr, expected_orig)
        else:
            should_be = {"attr": attr_name, "reproduced": expected_repr, "orig": expected_orig}
            self.assertEqual(target_attr, should_be)

    def test_detect_analyzer_maven(self):
        logs_folder = "maven/"
        job_ids = [35776350, 109895373, 148851383, 190697114, 214130455, 214130456, 37935504, 28224683, 3574443]
        for i, log in enumerate(logs_folder):
            file_path = logs_folder + log
            if isfile(file_path) and log[-4:] == ".log":
                ts, r = self.get_trigger_sha_and_repo(job_ids[i])
                result = self.dispatcher.analyze(file_path, job_ids[i], trigger_sha=ts, repo=r)
                self.compare_analyzer(result, "java-maven")

    def test_detect_failed_function_name_1(self):
        log = "1f7d1fda0001e35a945299dcdf574ccf60fcba28-3.1.log"
        job_id = 18826820
        file_path = "logs/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        result = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.assertIn("redis.clients.jedis.tests.commands.ObjectCommandsTest", result["tr_log_tests_failed"])

    def test_detect_failed_function_name_2(self):
        log = "a25097b2092937b7a66212eaa2ca1b48d7d2f813-90.3.log"
        job_id = 12080983
        file_path = "logs/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        result = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.assertIn("com.github.searls.jasmine.runner.SpecRunnerExecutorTest", result["tr_log_tests_failed"])

    def test_maven_1(self):
        log = "e5586dff6dbd4e418585fba6920be9cada824b36-204.1.log"
        job_id = 10708652
        file_path = "logs/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        maven1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(maven1, "broken")
        self.compare_analyzer(maven1, "java-maven")
        self.compare_num_t_run(maven1, 531)
        self.compare_num_t_ok(maven1, 530)
        self.compare_num_t_failed(maven1, 1)
        self.compare_num_t_skipped(maven1, 8)
        self.compare_bool_t_ran(maven1, True)
        self.compare_bool_t_failed(maven1, True)
        # self.compare_tduration(maven1, 23.8)
        # self.compare_buildduration(maven1, 39.92)

    def test_maven_2(self):
        log = "8143a3795946471a966d0747aa84d172cd812743-3.1.log"
        job_id = 37935504
        file_path = "logs/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        maven2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(maven2, "ok")
        self.compare_analyzer(maven2, "java-maven")
        self.compare_num_t_run(maven2, 275)
        self.compare_num_t_ok(maven2, 275)
        self.compare_num_t_failed(maven2, 0)
        self.compare_num_t_skipped(maven2, 2)
        self.compare_bool_t_ran(maven2, True)
        self.compare_bool_t_failed(maven2, False)
        # self.compare_tduration(maven2, 123123213)
        # self.compare_buildduration(maven2, 39.92)

    def test_maven_3(self):
        log = "148851383-orig.log"
        job_id = 148851383
        file_path = "maven/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        maven3 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(maven3, "broken")
        self.compare_analyzer(maven3, "java-maven")
        self.compare_num_t_run(maven3, 1666)
        self.compare_num_t_ok(maven3, 1652)
        self.compare_num_t_failed(maven3, 14)
        self.compare_num_t_skipped(maven3, 0)
        self.compare_bool_t_ran(maven3, True)
        self.compare_bool_t_failed(maven3, True)

    def test_maven_4(self):
        log = "214130456-orig.log"
        job_id = 214130456
        file_path = "maven/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        maven4 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(maven4, "broken")
        self.compare_analyzer(maven4, "java-maven")
        self.compare_num_t_run(maven4, 1692)
        self.compare_num_t_ok(maven4, 1688)
        self.compare_num_t_failed(maven4, 4)
        self.compare_num_t_skipped(maven4, 0)
        self.compare_bool_t_ran(maven4, True)
        self.compare_bool_t_failed(maven4, True)
        self.compare_frameworks(maven4, 'testng#JUnit')

    def test_maven_5(self):
        log = "109895373-orig.log"
        job_id = 109895373
        file_path = "maven/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        maven5 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(maven5, "broken")
        self.compare_analyzer(maven5, "java-maven")
        self.compare_num_t_run(maven5, 271)
        self.compare_num_t_ok(maven5, 269)
        self.compare_num_t_failed(maven5, 2)
        self.compare_num_t_skipped(maven5, 2)
        self.compare_bool_t_ran(maven5, True)
        self.compare_bool_t_failed(maven5, True)
        self.compare_tr_t_failed(maven5, 'addList(com.tagtraum.perf.[secure].view.model.TestRecentGC'
                                         'ResourcesModel)#addString(com.tagtraum.perf.[secure].view.model'
                                         '.TestRecentGCResourcesModel)')

    def test_maven_6(self):
        log = "190697114-orig.log"
        job_id = 190697114
        file_path = "maven/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        maven6 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(maven6, "broken")
        self.compare_analyzer(maven6, "java-maven")
        self.compare_num_t_run(maven6, 1681)
        self.compare_num_t_ok(maven6, 1680)
        self.compare_num_t_failed(maven6, 1)
        self.compare_num_t_skipped(maven6, 0)
        self.compare_bool_t_ran(maven6, True)
        self.compare_bool_t_failed(maven6, True)
        self.compare_tr_t_failed(maven6, 'testAcceptFileWithMaxSize(org.apache.struts2.interceptor'
                                         '.FileUploadInterceptorTest)')

    def test_maven_7(self):
        log = "214130455-orig.log"
        job_id = 214130455
        file_path = "maven/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        maven7 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(maven7, "broken")
        self.compare_analyzer(maven7, "java-maven")
        self.compare_num_t_run(maven7, 1692)
        self.compare_num_t_ok(maven7, 1688)
        self.compare_num_t_failed(maven7, 4)
        self.compare_num_t_skipped(maven7, 0)
        self.compare_bool_t_ran(maven7, True)
        self.compare_bool_t_failed(maven7, True)
        self.compare_tr_t_failed(maven7, 'testInvalidContentTypeMultipartRequest(org.apache.struts2.'
                                         'interceptor.FileUploadInterceptorTest)#testSuccessUploadOfA'
                                         'TextFileMultipartRequest(org.apache.struts2.interceptor.'
                                         'FileUploadInterceptorTest)#testNoContentMultipartRequest(org.apache.'
                                         'struts2.interceptor.FileUploadInterceptorTest)#testMultipart'
                                         'RequestLocalizedError(org.apache.struts2.interceptor.FileUpload'
                                         'InterceptorTest)')

    def test_status_terminated(self):
        log = "33664717.log"
        job_id = 33664717
        file_path = "terminated/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        result = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(result, "terminated")

    def test_python_0(self):
        log = '250808150-orig.log'
        job_id = 250808150
        file_path = 'python/' + log
        python0 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python0, 'ok')
        self.compare_analyzer(python0, 'python')
        self.compare_num_t_run(python0, 6610)
        self.compare_num_t_ok(python0, 6610)
        self.compare_num_t_failed(python0, 0)
        self.compare_num_t_skipped(python0, 22)
        self.compare_bool_t_ran(python0, True)
        self.compare_bool_t_failed(python0, False)
        self.compare_t_duration(python0, 43.33)
        self.compare_tr_t_failed(python0, '')
        self.compare_frameworks(python0, 'unittest')

    def test_python_1(self):
        log = '78170279-orig.log'
        job_id = 78170279
        file_path = 'python/' + log
        python1 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python1, 'broken')
        self.compare_analyzer(python1, 'python')
        self.compare_num_t_run(python1, 2)
        self.compare_num_t_ok(python1, 0)
        self.compare_num_t_failed(python1, 2)
        self.compare_num_t_skipped(python1, 0)
        self.compare_bool_t_ran(python1, True)
        self.compare_bool_t_failed(python1, True)
        self.compare_t_duration(python1, 0.015)
        self.compare_tr_t_failed(python1, 'ImportError#ImportError')
        self.compare_frameworks(python1, 'unittest')

    def test_python_2(self):
        log = '73309390-orig.log'
        job_id = 73309390
        file_path = 'python/' + log
        python2 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python2, 'broken')
        self.compare_analyzer(python2, 'python')
        self.compare_num_t_run(python2, 10128)
        self.compare_num_t_ok(python2, 10127)
        self.compare_num_t_failed(python2, 1)
        self.compare_num_t_skipped(python2, 568)
        self.compare_bool_t_ran(python2, True)
        self.compare_bool_t_failed(python2, True)
        self.compare_t_duration(python2, 275.869)
        self.compare_tr_t_failed(python2, 'test_non_current (tornado.test.ioloop_test.TestIOLoopCurrent)')
        self.compare_frameworks(python2, 'unittest')

    def test_python_3(self):
        log = '78833091-orig.log'
        job_id = 78833091
        file_path = 'python/' + log
        python3 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python3, 'broken')
        self.compare_analyzer(python3, 'python')
        self.compare_num_t_run(python3, 247)
        self.compare_num_t_ok(python3, 247)
        self.compare_num_t_failed(python3, 0)
        self.compare_num_t_skipped(python3, 0)
        self.compare_bool_t_ran(python3, True)
        self.compare_bool_t_failed(python3, False)
        self.compare_t_duration(python3, 0.207)
        self.compare_tr_t_failed(python3, '')
        self.compare_frameworks(python3, 'unittest')

    def test_python_4(self):
        log = '159557987-orig.log'
        job_id = 159557987
        file_path = 'python/' + log
        python4 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python4, 'broken')
        self.compare_analyzer(python4, 'python')
        self.compare_num_t_run(python4, 43)
        self.compare_num_t_ok(python4, 42)
        self.compare_num_t_failed(python4, 1)
        self.compare_num_t_skipped(python4, 0)
        self.compare_bool_t_ran(python4, True)
        self.compare_bool_t_failed(python4, True)
        self.compare_t_duration(python4, 0.146)
        self.compare_tr_t_failed(python4, 'test_multiline_index (__main__.Test)')
        self.compare_frameworks(python4, 'unittest')

    def test_python_5(self):
        log = '109227526-orig.log'
        job_id = 109227526
        file_path = 'python/' + log
        python5 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python5, 'broken')
        self.compare_analyzer(python5, 'python')
        self.compare_num_t_run(python5, 247)
        self.compare_num_t_ok(python5, 242)
        self.compare_num_t_failed(python5, 5)
        self.compare_num_t_skipped(python5, 0)
        self.compare_bool_t_ran(python5, True)
        self.compare_bool_t_failed(python5, True)
        self.compare_t_duration(python5, 0.259)
        self.compare_tr_t_failed(python5, 'test_modified_url_encoding (verktyg.testsuite.test_requests.'
                                          'RequestsTestCase)#test_shallow_mode (verktyg.testsuite.test'
                                          '_requests.RequestsTestCase)#test_storage_classes (verktyg.'
                                          'testsuite.test_requests.RequestsTestCase)#test_base_request'
                                          ' (verktyg.testsuite.test_requests.RequestsTestCase)#test_form'
                                          '_data_ordering (verktyg.testsuite.test_requests.RequestsTestCase)')
        self.compare_frameworks(python5, 'unittest')

    def test_python_6(self):
        log = '109231519-orig.log'
        job_id = 109231519
        file_path = 'python/' + log
        python6 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python6, 'ok')
        self.compare_analyzer(python6, 'python')
        self.compare_num_t_run(python6, 247)
        self.compare_num_t_ok(python6, 247)
        self.compare_num_t_failed(python6, 0)
        self.compare_num_t_skipped(python6, 0)
        self.compare_bool_t_ran(python6, True)
        self.compare_bool_t_failed(python6, False)
        self.compare_t_duration(python6, 0.252)
        self.compare_tr_t_failed(python6, '')
        self.compare_frameworks(python6, 'unittest')

    def test_python_7(self):
        log = '212206923-orig.log'
        job_id = 212206923
        file_path = 'python/' + log
        python7 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python7, 'broken')
        self.compare_analyzer(python7, 'python')
        self.compare_num_t_run(python7, 591)
        self.compare_num_t_ok(python7, 590)
        self.compare_num_t_failed(python7, 1)
        self.compare_num_t_skipped(python7, 0)
        self.compare_bool_t_ran(python7, True)
        self.compare_bool_t_failed(python7, True)
        self.compare_t_duration(python7, 30.006)
        self.compare_tr_t_failed(python7, 'test_download_and_expand_tgz (COT.helpers.tests.test'
                                          '_helper.HelperGenericTest)')
        self.compare_frameworks(python7, 'unittest')

    def test_python_8(self):
        log = '212215615-orig.log'
        job_id = 212215615
        file_path = 'python/' + log
        python8 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python8, 'ok')
        self.compare_analyzer(python8, 'python')
        self.compare_num_t_run(python8, 591)
        self.compare_num_t_ok(python8, 591)
        self.compare_num_t_failed(python8, 0)
        self.compare_num_t_skipped(python8, 0)
        self.compare_bool_t_ran(python8, True)
        self.compare_bool_t_failed(python8, False)
        self.compare_t_duration(python8, 30.436)
        self.compare_tr_t_failed(python8, '')
        self.compare_frameworks(python8, 'unittest')

    def test_python_9(self):
        log = '210833092-orig.log'
        job_id = 210833092
        file_path = 'python/' + log
        python9 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python9, 'broken')
        self.compare_analyzer(python9, 'python')
        self.compare_num_t_run(python9, 11)
        self.compare_num_t_ok(python9, 9)
        self.compare_num_t_failed(python9, 2)
        self.compare_num_t_skipped(python9, 0)
        self.compare_bool_t_ran(python9, True)
        self.compare_bool_t_failed(python9, True)
        self.compare_t_duration(python9, 0.28)
        self.compare_tr_t_failed(python9, 'tests.unit.test_readkey::ReadKeyTest::test_page_down'
                                          '#tests.unit.test_readkey::ReadKeyTest::test_page_up')
        self.compare_frameworks(python9, 'pytest')

    def test_python_10(self):
        log = '149257173-orig.log'
        job_id = 149257173
        file_path = 'python/' + log
        python10 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python10, 'broken')
        self.compare_analyzer(python10, 'python')
        self.compare_num_t_run(python10, 445)
        self.compare_num_t_ok(python10, 435)
        self.compare_num_t_failed(python10, 10)
        self.compare_num_t_skipped(python10, 2)
        self.compare_bool_t_ran(python10, True)
        self.compare_bool_t_failed(python10, True)
        self.compare_t_duration(python10, 70.302)
        self.compare_tr_t_failed(python10, 'test_list (vistrails.core.scripting.export.TestExport)'
                                           '#test_loop_append_mixed (vistrails.core.scripting.export.'
                                           'TestExport)#test_loop_cartesian (vistrails.core.scripting.'
                                           'export.TestExport)#test_loop_cartesian_reversed (vistrails.'
                                           'core.scripting.export.TestExport)#test_loop_combined'
                                           ' (vistrails.core.scripting.export.TestExport)#test'
                                           '_loop_pairwise (vistrails.core.scripting.export.TestExport)'
                                           '#test_loop_wrap (vistrails.core.scripting.export.TestExport)'
                                           '#test_sources (vistrails.core.scripting.export.TestExport)'
                                           '#testIncorrectURL (vistrails.packages.URL.init.TestDownload'
                                           'File)#testIncorrectURL_2 (vistrails.packages.URL.init.Test'
                                           'DownloadFile)')
        self.compare_frameworks(python10, 'unittest')

    def test_python_11(self):
        log = '398075675-modified.log'
        job_id = 398075675
        file_path = 'python/' + log
        python11 = self.dispatcher.analyze(file_path, job_id)
        self.compare_analyzer(python11, 'python')
        self.compare_num_t_run(python11, 9465)
        self.compare_num_t_ok(python11, 9460)
        self.compare_num_t_failed(python11, 5)
        self.compare_num_t_skipped(python11, 27)
        self.compare_bool_t_ran(python11, True)
        self.compare_bool_t_failed(python11, True)
        self.compare_t_duration(python11, 821.23)
        self.compare_frameworks(python11, 'pytest')
        self.compare_tr_t_failed(python11, 'sklearn.ensemble.tests.test_bagging::test_parallel_classification'
                                           '#sklearn.ensemble.tests.test_bagging::test_parallel_regression'
                                           '#sklearn.ensemble.tests.test_bagging::test_base_estimator'
                                           '#sklearn.ensemble.tests.test_iforest::test_iforest_parallel'
                                           '_regression#sklearn.tests.test_common::test_parallel_fit')

    def test_python_12(self):
        log = '109787645-orig.log'
        job_id = 109787645
        file_path = 'python/' + log
        python12 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python12, 'broken')
        self.compare_analyzer(python12, 'python')
        self.compare_num_t_run(python12, 41)
        self.compare_num_t_ok(python12, 2)
        self.compare_num_t_failed(python12, 39)
        self.compare_num_t_skipped(python12, 0)
        self.compare_bool_t_ran(python12, True)
        self.compare_bool_t_failed(python12, True)
        self.compare_t_duration(python12, 3.74)
        self.compare_frameworks(python12, 'pytest')
        self.compare_tr_t_failed(python12, 'tests.test_api::TestAuth::test_api#tests.test_api::TestAuth::'
                                           'test_backup#tests.test_api::TestAuth::test_non_existant_api'
                                           '#tests.test_api::TestAuth::test_submit#tests.test_api::'
                                           'TestAuth::test_version_api#tests.test_auth::TestAuth::test'
                                           '_login#tests.test_auth::TestAuth::test_restricted#tests.test'
                                           '_auth::TestAuth::test_testing_login#tests.test_auth::TestAuth::'
                                           'test_testing_login_fail#tests.test_group::TestGroup::test_accept'
                                           '#tests.test_group::TestGroup::test_accept_not_pending#tests.'
                                           'test_group::TestGroup::test_decline#tests.test_group::TestGroup'
                                           '::test_decline_degenerate#tests.test_group::TestGroup::test'
                                           '_decline_not_pending#tests.test_group::TestGroup::test_invite'
                                           '#tests.test_group::TestGroup::test_invite_full#tests.test_group'
                                           '::TestGroup::test_invite_in_group#tests.test_group::TestGroup'
                                           '::test_invite_individual#tests.test_group::TestGroup::test_invite'
                                           '_not_enrolled#tests.test_group::TestGroup::test_locked#tests.'
                                           'test_group::TestGroup::test_log#tests.test_group::TestGroup::'
                                           'test_remove#tests.test_group::TestGroup::test_remove_degenerate'
                                           '#tests.test_group::TestGroup::test_remove_not_in_group#tests.'
                                           'test_group::TestGroup::test_remove_self#tests.test_highlight::'
                                           'TestHighlight::test_highlight_diff#tests.test_highlight::'
                                           'TestHighlight::test_highlight_file#tests.test_main::TestMain::'
                                           'test_home#tests.test_submission::TestSubmission::test_accept'
                                           '_unflag#tests.test_submission::TestSubmission::test_active_user'
                                           '_ids#tests.test_submission::TestSubmission::test_files#tests.'
                                           'test_submission::TestSubmission::test_flag#tests.test'
                                           '_submission::TestSubmission::test_no_flags#tests.test_submission'
                                           '::TestSubmission::test_sabotage#tests.test_submission::'
                                           'TestSubmission::test_two_flags#tests.test_submission::'
                                           'TestSubmission::test_unflag#tests.test_submission::'
                                           'TestSubmission::test_unflag_not_flagged#tests.test_user'
                                           '::TestUser::test_lookup#tests.test_utils::TestUtils::test_hashids')

    def test_python_13(self):
        log = '256802843-orig.log'
        job_id = 256802843
        file_path = 'python/' + log
        python13 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python13, 'broken')
        self.compare_analyzer(python13, 'python')
        self.compare_num_t_run(python13, 2555)
        self.compare_num_t_ok(python13, 2546)
        self.compare_num_t_failed(python13, 9)
        self.compare_num_t_skipped(python13, 0)
        self.compare_bool_t_ran(python13, True)
        self.compare_bool_t_failed(python13, True)
        self.compare_frameworks(python13, 'pytest')
        self.compare_tr_t_failed(python13, 'tests.h.oauth.jwt_grant_token_test::TestJWTGrantToken::test'
                                           '_issuer_raises_for_missing_iss_claim#tests.h.oauth.jwt_grant'
                                           '_token_test::TestVerifiedJWTGrantToken::test_init_raises_for'
                                           '_missing_claims[aud-audience]#tests.h.oauth.jwt_grant_token'
                                           '_test::TestVerifiedJWTGrantToken::test_init_raises_for_missing'
                                           '_claims[exp-expiry]#tests.h.oauth.jwt_grant_token_test::'
                                           'TestVerifiedJWTGrantToken::test_init_raises_for_missing'
                                           '_claims[nbf-start time]#tests.h.oauth.jwt_grant_token_test'
                                           '::TestVerifiedJWTGrantToken::test_init_raises_for_invalid'
                                           '_aud#tests.h.oauth.jwt_grant_token_test::'
                                           'TestVerifiedJWTGrantToken::test_init_raises_for_invalid'
                                           '_timestamp_types[exp-expiry]#tests.h.oauth.jwt_grant'
                                           '_token_test::TestVerifiedJWTGrantToken::test_init_raises'
                                           '_for_invalid_timestamp_types[nbf-start time]#tests.h.oauth.jwt'
                                           '_grant_token_test::TestVerifiedJWTGrantToken::test_subject'
                                           '_raises_for_missing_sub_claim#tests.h.oauth.jwt_grant_token'
                                           '_test::TestVerifiedJWTGrantToken::test_subject_raises_for_empty'
                                           '_sub_claim')

    def test_python_14(self):
        log = '299944105-orig.log'
        job_id = 299944105
        file_path = 'python/' + log
        python14 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python14, "broken")
        self.compare_analyzer(python14, "python")
        self.compare_num_t_run(python14, 203)
        self.compare_num_t_ok(python14, 195)
        self.compare_num_t_failed(python14, 8)
        self.compare_num_t_skipped(python14, 14)
        self.compare_bool_t_ran(python14, True)
        self.compare_bool_t_failed(python14, True)
        self.compare_frameworks(python14, 'pytest')
        self.compare_tr_t_failed(python14, 'tests.test_client::SSHClientTest::test_4_auto_add_policy'
                                           '#tests.test_client::SSHClientTest::test_6_cleanup#tests.test'
                                           '_client::SSHClientTest::test_client_can_be_used_as_context'
                                           '_manager#tests.test_client::SSHClientTest::test_host_key'
                                           '_negotiation_1#tests.test_client::SSHClientTest::test_host'
                                           '_key_negotiation_2#tests.test_client::SSHClientTest::test'
                                           '_host_key_negotiation_3#tests.test_client::SSHClientTest::'
                                           'test_host_key_negotiation_4#tests.test_client::SSHClientTest'
                                           '::test_update_environment')

    def test_python_15(self):
        log = '334185447-orig.log'
        job_id = 334185447
        file_path = 'python/' + log
        python15 = self.dispatcher.analyze(file_path, job_id)
        self.compare_analyzer(python15, 'python')
        self.compare_num_t_run(python15, 984)
        self.compare_num_t_ok(python15, 983)
        self.compare_num_t_failed(python15, 1)
        self.compare_num_t_skipped(python15, 64)
        self.compare_bool_t_ran(python15, True)
        self.compare_bool_t_failed(python15, True)
        self.compare_frameworks(python15, 'pytest')
        self.compare_tr_t_failed(python15, 'joblib.shelf::shelve_mmap')

    def test_python_16(self):
        log = '403765814-orig.log'
        job_id = 403765814
        file_path = 'python/' + log
        python16 = self.dispatcher.analyze(file_path, job_id)
        self.compare_analyzer(python16, 'python')
        self.compare_num_t_run(python16, 9627)
        self.compare_num_t_ok(python16, 9626)
        self.compare_num_t_failed(python16, 1)
        self.compare_num_t_skipped(python16, 29)
        self.compare_bool_t_ran(python16, True)
        self.compare_bool_t_failed(python16, True)
        self.compare_frameworks(python16, 'pytest')
        self.compare_tr_t_failed(python16, 'sklearn.cluster.bicluster::SpectralCoclustering')

    def test_python_17(self):
        log = '113007194-orig.log'
        job_id = 113007194
        file_path = 'python/' + log
        python17 = self.dispatcher.analyze(file_path, job_id)
        self.compare_analyzer(python17, 'python')
        self.compare_num_t_run(python17, 6508)
        self.compare_num_t_ok(python17, 6507)
        self.compare_num_t_failed(python17, 1)
        self.compare_num_t_skipped(python17, 0)
        self.compare_bool_t_ran(python17, True)
        self.compare_bool_t_failed(python17, True)
        self.compare_frameworks(python17, 'unittest')
        self.compare_tr_t_failed(python17, "test_repository_package_names('./repository/m.json', ...)"
                                           " (tests.test.DefaultRepositoryTests)")

    def test_python_18(self):
        log = '65721530-orig.log'
        job_id = 65721530
        file_path = 'python/' + log
        python18 = self.dispatcher.analyze(file_path, job_id)
        self.compare_analyzer(python18, 'python')
        self.compare_num_t_run(python18, 5388)
        self.compare_num_t_ok(python18, 5387)
        self.compare_num_t_failed(python18, 1)
        self.compare_num_t_skipped(python18, 16)
        self.compare_bool_t_ran(python18, True)
        self.compare_bool_t_failed(python18, True)
        self.compare_frameworks(python18, 'unittest')
        self.compare_tr_t_failed(python18, "sklearn.tests.test_common.test_all_estimators"
                                           "('GMM', <class 'sklearn.mixture.gmm.GMM'>)")

    def test_python_19(self):
        log = '309853010-orig.log'
        job_id = 309853010
        file_path = 'python/' + log
        python19 = self.dispatcher.analyze(file_path, job_id)
        self.compare_analyzer(python19, 'python')
        self.compare_num_t_run(python19, 6783)
        self.compare_num_t_ok(python19, 6782)
        self.compare_num_t_failed(python19, 1)
        self.compare_num_t_skipped(python19, 17)
        self.compare_bool_t_ran(python19, True)
        self.compare_bool_t_failed(python19, True)
        self.compare_frameworks(python19, 'unittest')
        self.compare_tr_t_failed(python19, "numpy.core.tests.test_multiarray.TestSummarization.test_2d")

    def test_python_20(self):
        log = '189738938-orig.log'
        job_id = 189738938
        file_path = 'python/' + log
        python20 = self.dispatcher.analyze(file_path, job_id)
        self.compare_analyzer(python20, 'python')
        self.compare_num_t_run(python20, 7607)
        self.compare_num_t_ok(python20, 7606)
        self.compare_num_t_failed(python20, 1)
        self.compare_num_t_skipped(python20, 62)
        self.compare_bool_t_ran(python20, True)
        self.compare_bool_t_failed(python20, True)
        self.compare_frameworks(python20, 'unittest')
        self.compare_tr_t_failed(python20, "sklearn.neighbors.classification.KNeighborsClassifier")

    def test_gradle_0(self):
        log = "88551599-orig.log"
        job_id = 88551599
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle0 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle0, "broken")
        self.compare_analyzer(gradle0, "java-gradle")
        self.compare_num_t_run(gradle0, 1160)
        self.compare_num_t_ok(gradle0, 1118)
        self.compare_num_t_failed(gradle0, 42)
        self.compare_num_t_skipped(gradle0, 0)
        self.compare_bool_t_ran(gradle0, True)
        self.compare_bool_t_failed(gradle0, True)

    def test_gradle_1(self):
        log = "68605615-orig.log"
        job_id = 68605615
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle1, "broken")
        self.compare_analyzer(gradle1, "java-gradle")
        self.compare_num_t_run(gradle1, 1143)
        self.compare_num_t_ok(gradle1, 1142)
        self.compare_num_t_failed(gradle1, 1)
        self.compare_num_t_skipped(gradle1, 0)
        self.compare_bool_t_ran(gradle1, True)
        self.compare_bool_t_failed(gradle1, True)
        self.compare_tr_t_failed(gradle1, 'test.methodinterceptors.multipleinterceptors.'
                                          'MultipleInterceptorsTest.testMultipleInterceptorsWithPreserveOrder')

    def test_gradle_2(self):
        log = "49327415-orig.log"
        job_id = 49327415
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle2, "broken")
        self.compare_analyzer(gradle2, "java-gradle")
        self.compare_num_t_run(gradle2, 42)
        self.compare_num_t_ok(gradle2, 39)
        self.compare_num_t_failed(gradle2, 3)
        self.compare_num_t_skipped(gradle2, 1)
        self.compare_bool_t_ran(gradle2, True)
        self.compare_bool_t_failed(gradle2, True)

    def test_gradle_3(self):
        log = "114088869-orig.log"
        job_id = 114088869
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle3 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle3, "broken")
        self.compare_analyzer(gradle3, "java-gradle")
        self.compare_num_t_run(gradle3, 46)
        self.compare_num_t_ok(gradle3, 45)
        self.compare_num_t_failed(gradle3, 1)
        self.compare_num_t_skipped(gradle3, 4)
        self.compare_bool_t_ran(gradle3, True)
        self.compare_bool_t_failed(gradle3, True)
        self.compare_tr_t_failed(gradle3, 'org.stagemonitor.requestmonitor.ejb.'
                                          'RemoteEjbMonitorInstrumenterTest.testMonitorRemoteCalls')

    def test_gradle_4(self):
        log = "254312312-orig.log"
        job_id = 254312312
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle4 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle4, "broken")
        self.compare_analyzer(gradle4, "java-gradle")
        self.compare_num_t_run(gradle4, 47)
        self.compare_num_t_ok(gradle4, 40)
        self.compare_num_t_failed(gradle4, 7)
        self.compare_num_t_skipped(gradle4, 0)
        self.compare_bool_t_ran(gradle4, True)
        self.compare_bool_t_failed(gradle4, True)
        self.compare_tr_t_failed(gradle4, 'org.stagemonitor.alerting.alerter.ElasticsearchAlerterTest'
                                          '.testAlert#org.stagemonitor.alerting.alerter.HttpAlerterTest'
                                          '.testAlert#org.stagemonitor.alerting.incident.'
                                          'IncidentRepositoryTest.testSaveAndGet[0: class org.stagemonitor'
                                          '.alerting.incident.ElasticsearchIncidentRepository]#org.'
                                          'stagemonitor.alerting.incident.IncidentRepositoryTest.'
                                          'testWrongVersion[0: class org.stagemonitor.alerting.'
                                          'incident.ElasticsearchIncidentRepository]#org.stagemonitor.'
                                          'alerting.incident.IncidentRepositoryTest.'
                                          'testDeleteWrongVersion[0: class org.stagemonitor.'
                                          'alerting.incident.ElasticsearchIncidentRepository]'
                                          '#org.stagemonitor.alerting.incident.IncidentRepositoryTest'
                                          '.testAlreadyCreated[0: class org.stagemonitor.alerting.'
                                          'incident.ElasticsearchIncidentRepository]#org.stagemonitor'
                                          '.alerting.incident.IncidentRepositoryTest.testDelete[0: '
                                          'class org.stagemonitor.alerting.incident.'
                                          'ElasticsearchIncidentRepository]')

    def test_gradle_5(self):
        log = "49327415-orig.log"
        job_id = 49327415
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle5 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle5, "broken")
        self.compare_analyzer(gradle5, "java-gradle")
        self.compare_num_t_run(gradle5, 42)
        self.compare_num_t_ok(gradle5, 39)
        self.compare_num_t_failed(gradle5, 3)
        self.compare_num_t_skipped(gradle5, 1)
        self.compare_bool_t_ran(gradle5, True)
        self.compare_bool_t_failed(gradle5, True)
        self.compare_tr_t_failed(gradle5, 'CapsuleTest.testWrapperCapsuleNoMain#CapsuleTest.'
                                          'testWrapperCapsule#CapsuleTest.testWrapperCapsuleNonCapsuleApp')

    def test_gradle_6(self):
        log = "144826560-orig.log"
        job_id = 144826560
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle6 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle6, "broken")
        self.compare_analyzer(gradle6, "java-gradle")
        self.compare_num_t_run(gradle6, 1278)
        self.compare_num_t_ok(gradle6, 1204)
        self.compare_num_t_failed(gradle6, 74)
        self.compare_num_t_skipped(gradle6, 2)
        self.compare_bool_t_ran(gradle6, True)
        self.compare_bool_t_failed(gradle6, True)
        self.compare_frameworks(gradle6, 'JUnit')

    def test_gradle_7(self):
        log = "88551597-orig.log"
        job_id = 88551597
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle7 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle7, "broken")
        self.compare_analyzer(gradle7, "java-gradle")
        self.compare_num_t_run(gradle7, 1160)
        self.compare_num_t_ok(gradle7, 1118)
        self.compare_num_t_failed(gradle7, 42)
        self.compare_num_t_skipped(gradle7, 0)
        self.compare_bool_t_ran(gradle7, True)
        self.compare_bool_t_failed(gradle7, True)
        self.compare_frameworks(gradle7, 'JUnit')
        self.compare_tr_t_failed(gradle7, 'test.groupinvocation.GroupSuiteTest.Regression2#test.'
                                          'groupinvocation.GroupSuiteTest.Regression2#test.groupinvocation'
                                          '.GroupSuiteTest.Regression2#test.groupinvocation.GroupSuiteTest'
                                          '.Regression2#test.groupinvocation.GroupSuiteTest.Regression2'
                                          '#test.groupinvocation.GroupSuiteTest.Regression2#test.'
                                          'groupinvocation.GroupSuiteTest.Regression2#test.'
                                          'annotationtransformer.AnnotationTransformerTest.'
                                          'Regression2#test.annotationtransformer.AnnotationTransformer'
                                          'Test.Regression2#test.preserveorder.PreserveOrderTest.'
                                          'Regression2#test.methodselectors.CommandLineTest.Method'
                                          ' selectors#test.methodselectors.CommandLineTest.Method'
                                          ' selectors#test.methodselectors.CommandLineTest.Method'
                                          ' selectors#test.methodselectors.CommandLineTest.Method'
                                          ' selectors#test.methodselectors.CommandLineTest.Method'
                                          ' selectors#test.methodselectors.CommandLineTest.Method'
                                          ' selectors#test.methodselectors.CommandLineTest.Method'
                                          ' selectors#test.methodselectors.CommandLineTest.Method'
                                          ' selectors#test.methodselectors.MethodSelectorInSuiteTest.'
                                          'Method selectors#test.methodselectors.MethodSelector'
                                          'InSuiteTest.Method selectors#test.methodselectors.'
                                          'MethodSelectorInSuiteTest.Method selectors#test.JUnitTest1'
                                          '.JUnit#test.JUnitTest1.JUnit#test.JUnitTest1.JUnit#test.'
                                          'JUnitTest1.JUnit#test.JUnitTest1.JUnit#test.JUnitTest1.'
                                          'JUnit#test.JUnitTest1.JUnit#test.CommandLineTest.JUnit'
                                          '#test.CommandLineTest.JUnit#test.JUnit4Test.JUnit#test.'
                                          'JUnit4Test.JUnit#test.JUnit4Test.JUnit#test.JUnit4Test.'
                                          'JUnit#test.JUnit4Test.JUnit#test.retryAnalyzer.'
                                          'RetryAnalyzerTest.RetryAnalyzer#test.methodinterceptors.'
                                          'multipleinterceptors.MultipleInterceptorsTest.'
                                          'MethodInterceptor#test.testng173.TestNG173Test.Bug173'
                                          '#test.testng173.TestNG173Test.Bug173#test.mixed.MixedTest.'
                                          'Mixed#test.mixed.MixedTest.Mixed#test.mixed.MixedTest.Mixed')

    def test_gradle_8(self):
        log = "111273215-orig.log"
        job_id = 111273215
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle8 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle8, "broken")
        self.compare_analyzer(gradle8, "java-gradle")
        self.compare_num_t_run(gradle8, 646)
        self.compare_num_t_ok(gradle8, 640)
        self.compare_num_t_failed(gradle8, 6)
        self.compare_num_t_skipped(gradle8, 86)
        self.compare_bool_t_ran(gradle8, True)
        self.compare_bool_t_failed(gradle8, True)
        self.compare_frameworks(gradle8, 'JUnit')
        self.compare_tr_t_failed(gradle8, 'co.paralleluniverse.fibers.FiberTest.testSerializationWith'
                                          'ThreadLocals[0]#co.paralleluniverse.fibers.FiberTest.test'
                                          'Serialization1[0]#co.paralleluniverse.fibers.FiberTest.'
                                          'testSerialization2[0]#co.paralleluniverse.fibers.FiberTest.'
                                          'testSerializationWithThreadLocals[1]#co.paralleluniverse.'
                                          'fibers.FiberTest.testSerialization1[1]#co.paralleluniverse.'
                                          'fibers.FiberTest.testSerialization2[1]')

    def test_gradle_9(self):
        log = "269855203-orig.log"
        job_id = 269855203
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle9 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle9, "broken")
        self.compare_analyzer(gradle9, "java-gradle")
        self.compare_num_t_run(gradle9, 1544)
        self.compare_num_t_ok(gradle9, 1543)
        self.compare_num_t_failed(gradle9, 1)
        self.compare_num_t_skipped(gradle9, 0)
        self.compare_bool_t_ran(gradle9, True)
        self.compare_bool_t_failed(gradle9, True)
        self.compare_frameworks(gradle9, 'JUnit')
        self.compare_tr_t_failed(gradle9, 'test.thread.parallelization.ParallelByMethodsTestCase6Scenario1.'
                                          'verifyThatTestMethodsRunInParallelThreads')

    def test_gradle_10(self):
        log = "153491211-orig.log"
        job_id = 153491211
        file_path = "gradle/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        gradle10 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(gradle10, "broken")
        self.compare_analyzer(gradle10, "java-gradle")
        self.compare_num_t_run(gradle10, 740)
        self.compare_num_t_ok(gradle10, 680)
        self.compare_num_t_failed(gradle10, 60)
        self.compare_num_t_skipped(gradle10, 16)
        self.compare_bool_t_ran(gradle10, True)
        self.compare_bool_t_failed(gradle10, True)
        self.compare_frameworks(gradle10, 'JUnit')
        self.compare_tr_t_failed(gradle10, 'com.tngtech.jgiven.examples.coffeemachine.ServeCoffeeTest.a'
                                           '_scenario_with_a_failing_test_case_for_demonstration_purposes[1:'
                                           ' false]#com.tngtech.jgiven.examples.coffeemachine.ServeCoffeeTest.'
                                           'shouldFailWithUnexpectedRuntimeException#com.tngtech.jgiven.'
                                           'examples.coffeemachine.ServeCoffeeTest.a_failing_scenario'
                                           '_for_demonstration_purposes#com.tngtech.jgiven.examples.'
                                           'nested.NestedStepsTest.a_scenario_with_a_failing_nested'
                                           '_step_on_purpose#com.tngtech.jgiven.examples.parameters'
                                           '.ParametrizedScenariosTest.a_scenario_with_many_cases[5:'
                                           ' some grouping value 0, value 5]#com.tngtech.jgiven.examples'
                                           '.parameters.ParametrizedScenariosTest.a_scenario_with_many'
                                           '_cases[15: some grouping value 1, value 5]#com.tngtech.jgiven'
                                           '.examples.parameters.ParametrizedScenariosTest.a_scenario'
                                           '_with_many_cases[25: some grouping value 2, value 5]#com.'
                                           'tngtech.jgiven.examples.parameters.ParametrizedScenariosTest'
                                           '.a_scenario_with_many_cases[35: some grouping value 3, value'
                                           ' 5]#com.tngtech.jgiven.examples.parameters.Parametrized'
                                           'ScenariosTest.a_scenario_with_many_cases[45: some grouping'
                                           ' value 4, value 5]#com.tngtech.jgiven.examples.parameters'
                                           '.ParametrizedScenariosTest.a_scenario_with_many_cases[55'
                                           ': some grouping value 5, value 5]#com.tngtech.jgiven.'
                                           'examples.parameters.ParametrizedScenariosTest.a_scenario'
                                           '_with_many_cases[65: some grouping value 6, value 5]#com'
                                           '.tngtech.jgiven.examples.parameters.ParametrizedScenarios'
                                           'Test.a_scenario_with_many_cases[75: some grouping value '
                                           '7, value 5]#com.tngtech.jgiven.examples.parameters.Param'
                                           'etrizedScenariosTest.a_scenario_with_many_cases[85: some'
                                           ' grouping value 8, value 5]#com.tngtech.jgiven.examples.pa'
                                           'rameters.ParametrizedScenariosTest.a_scenario_with_many_ca'
                                           'ses[95: some grouping value 9, value 5]#com.tngtech.jgive'
                                           'n.integration.spring.test.XmlConfiguredSpringScenarioTest'
                                           'Test.spring_can_inject_beans_into_stages#com.tngtech.jgiv'
                                           'en.examples.coffeemachine.ServeCoffeeTest.a_scenario_with'
                                           '_a_failing_test_case_for_demonstration_purposes[1: false]'
                                           '#com.tngtech.jgiven.examples.coffeemachine.ServeCoffeeTest'
                                           '.shouldFailWithUnexpectedRuntimeException#com.tngtech.jgi'
                                           'ven.examples.coffeemachine.ServeCoffeeTest.a_failing_scen'
                                           'ario_for_demonstration_purposes#com.tngtech.jgiven.exampl'
                                           'es.nested.NestedStepsTest.a_scenario_with_a_failing_nest'
                                           'ed_step_on_purpose#com.tngtech.jgiven.examples.parameters'
                                           '.ParametrizedScenariosTest.a_scenario_with_many_cases[5: s'
                                           'ome grouping value 0, value 5]#com.tngtech.jgiven.examples'
                                           '.parameters.ParametrizedScenariosTest.a_scenario_with_many'
                                           '_cases[15: some grouping value 1, value 5]#com.tngtech.jgi'
                                           'ven.examples.parameters.ParametrizedScenariosTest.a_scenar'
                                           'io_with_many_cases[25: some grouping value 2, value 5]#com'
                                           '.tngtech.jgiven.examples.parameters.ParametrizedScenariosT'
                                           'est.a_scenario_with_many_cases[35: some grouping value 3, '
                                           'value 5]#com.tngtech.jgiven.examples.parameters.Parametriz'
                                           'edScenariosTest.a_scenario_with_many_cases[45: some groupi'
                                           'ng value 4, value 5]#com.tngtech.jgiven.examples.parameter'
                                           's.ParametrizedScenariosTest.a_scenario_with_many_cases[55: '
                                           'some grouping value 5, value 5]#com.tngtech.jgiven.example'
                                           's.parameters.ParametrizedScenariosTest.a_scenario_with_man'
                                           'y_cases[65: some grouping value 6, value 5]#com.tngtech.jg'
                                           'iven.examples.parameters.ParametrizedScenariosTest.a_scena'
                                           'rio_with_many_cases[75: some grouping value 7, value 5]#co'
                                           'm.tngtech.jgiven.examples.parameters.ParametrizedScenariosT'
                                           'est.a_scenario_with_many_cases[85: some grouping value 8, v'
                                           'alue 5]#com.tngtech.jgiven.examples.parameters.Parametrize'
                                           'dScenariosTest.a_scenario_with_many_cases[95: some groupin'
                                           'g value 9, value 5]#com.tngtech.jgiven.integration.spring.'
                                           'test.XmlConfiguredSpringScenarioTestTest.spring_can_inject'
                                           '_beans_into_stages#com.tngtech.jgiven.examples.coffeemachi'
                                           'ne.ServeCoffeeTest.a_scenario_with_a_failing_test_case_for'
                                           '_demonstration_purposes[1: false]#com.tngtech.jgiven.examp'
                                           'les.coffeemachine.ServeCoffeeTest.shouldFailWithUnexpected'
                                           'RuntimeException#com.tngtech.jgiven.examples.coffeemachine'
                                           '.ServeCoffeeTest.a_failing_scenario_for_demonstration_purp'
                                           'oses#com.tngtech.jgiven.examples.nested.NestedStepsTest.a_'
                                           'scenario_with_a_failing_nested_step_on_purpose#com.tngtech'
                                           '.jgiven.examples.parameters.ParametrizedScenariosTest.a_sc'
                                           'enario_with_many_cases[5: some grouping value 0, value 5]#'
                                           'com.tngtech.jgiven.examples.parameters.ParametrizedScenari'
                                           'osTest.a_scenario_with_many_cases[15: some grouping value '
                                           '1, value 5]#com.tngtech.jgiven.examples.parameters.Paramet'
                                           'rizedScenariosTest.a_scenario_with_many_cases[25: some gro'
                                           'uping value 2, value 5]#com.tngtech.jgiven.examples.parame'
                                           'ters.ParametrizedScenariosTest.a_scenario_with_many_cases['
                                           '35: some grouping value 3, value 5]#com.tngtech.jgiven.exa'
                                           'mples.parameters.ParametrizedScenariosTest.a_scenario_with'
                                           '_many_cases[45: some grouping value 4, value 5]#com.tngtech'
                                           '.jgiven.examples.parameters.ParametrizedScenariosTest.a_sc'
                                           'enario_with_many_cases[55: some grouping value 5, value 5]'
                                           '#com.tngtech.jgiven.examples.parameters.ParametrizedScena'
                                           'riosTest.a_scenario_with_many_cases[65: some grouping val'
                                           'ue 6, value 5]#com.tngtech.jgiven.examples.parameters.Par'
                                           'ametrizedScenariosTest.a_scenario_with_many_cases[75: som'
                                           'e grouping value 7, value 5]#com.tngtech.jgiven.examples.'
                                           'parameters.ParametrizedScenariosTest.a_scenario_with_many'
                                           '_cases[85: some grouping value 8, value 5]#com.tngtech.jg'
                                           'iven.examples.parameters.ParametrizedScenariosTest.a_scen'
                                           'ario_with_many_cases[95: some grouping value 9, value 5]#c'
                                           'om.tngtech.jgiven.integration.spring.test.XmlConfiguredSpr'
                                           'ingScenarioTestTest.spring_can_inject_beans_into_stages#co'
                                           'm.tngtech.jgiven.examples.coffeemachine.ServeCoffeeTest.a_'
                                           'scenario_with_a_failing_test_case_for_demonstration_purpos'
                                           'es[1: false]#com.tngtech.jgiven.examples.coffeemachine.Ser'
                                           'veCoffeeTest.shouldFailWithUnexpectedRuntimeException#com.'
                                           'tngtech.jgiven.examples.coffeemachine.ServeCoffeeTest.a_fa'
                                           'iling_scenario_for_demonstration_purposes#com.tngtech.jgive'
                                           'n.examples.nested.NestedStepsTest.a_scenario_with_a_failing'
                                           '_nested_step_on_purpose#com.tngtech.jgiven.examples.paramet'
                                           'ers.ParametrizedScenariosTest.a_scenario_with_many_cases[5:'
                                           ' some grouping value 0, value 5]#com.tngtech.jgiven.example'
                                           's.parameters.ParametrizedScenariosTest.a_scenario_with_many'
                                           '_cases[15: some grouping value 1, value 5]#com.tngtech.jgiv'
                                           'en.examples.parameters.ParametrizedScenariosTest.a_scenario'
                                           '_with_many_cases[25: some grouping value 2, value 5]#com.tn'
                                           'gtech.jgiven.examples.parameters.ParametrizedScenariosTest.a'
                                           '_scenario_with_many_cases[35: some grouping value 3, value 5'
                                           ']#com.tngtech.jgiven.examples.parameters.ParametrizedScenari'
                                           'osTest.a_scenario_with_many_cases[45: some grouping value 4, '
                                           'value 5]#com.tngtech.jgiven.examples.parameters.Parametrized'
                                           'ScenariosTest.a_scenario_with_many_cases[55: some grouping v'
                                           'alue 5, value 5]#com.tngtech.jgiven.examples.parameters.Para'
                                           'metrizedScenariosTest.a_scenario_with_many_cases[65: some gr'
                                           'ouping value 6, value 5]#com.tngtech.jgiven.examples.paramet'
                                           'ers.ParametrizedScenariosTest.a_scenario_with_many_cases[75:'
                                           ' some grouping value 7, value 5]#com.tngtech.jgiven.examples'
                                           '.parameters.ParametrizedScenariosTest.a_scenario_with_many_c'
                                           'ases[85: some grouping value 8, value 5]#com.tngtech.jgiven.'
                                           'examples.parameters.ParametrizedScenariosTest.a_scenario_wit'
                                           'h_many_cases[95: some grouping value 9, value 5]#com.tngtech'
                                           '.jgiven.integration.spring.test.XmlConfiguredSpringScenarioT'
                                           'estTest.spring_can_inject_beans_into_stages')

    def test_ant_0(self):
        log = "264241708-orig.log"
        job_id = 264241708
        file_path = "ant/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        ant0 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(ant0, "broken")
        self.compare_analyzer(ant0, "java-ant")
        self.compare_num_t_run(ant0, 287)
        self.compare_num_t_ok(ant0, 286)
        self.compare_num_t_failed(ant0, 1)
        self.compare_num_t_skipped(ant0, 0)
        self.compare_bool_t_ran(ant0, True)
        self.compare_bool_t_failed(ant0, True)
        self.compare_frameworks(ant0, 'JUnit')
        self.compare_tr_t_failed(ant0, 'wyc.testing.AllInvalidTest.invalid[Import_Invalid_1]')

    def test_ant_1(self):
        log = "233645906-orig.log"
        job_id = 233645906
        file_path = "ant/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        ant1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_status(ant1, "broken")
        self.compare_analyzer(ant1, "java-ant")
        self.compare_num_t_run(ant1, 1367)
        self.compare_num_t_ok(ant1, 1341)
        self.compare_num_t_failed(ant1, 26)
        self.compare_num_t_skipped(ant1, 0)
        self.compare_bool_t_ran(ant1, True)
        self.compare_bool_t_failed(ant1, True)
        self.compare_frameworks(ant1, 'JUnit')
        self.compare_tr_t_failed(ant1, 'wyc.testing.AllValidVerificationTest.validVerification[Constrain'
                                       'edReference_Valid_1]#wyc.testing.AllValidVerificationTest.validV'
                                       'erification[FunctionRef_Valid_7]#wyc.testing.AllValidVerificatio'
                                       'nTest.validVerification[Lifetime_Lambda_Valid_6]#wyc.testing.AllV'
                                       'alidVerificationTest.validVerification[Lifetime_Lambda_Valid_7]#w'
                                       'yc.testing.AllValidVerificationTest.validVerification[Lifetime_Va'
                                       'lid_1]#wyc.testing.AllValidVerificationTest.validVerification[Lif'
                                       'etime_Valid_2]#wyc.testing.AllValidVerificationTest.validVerifica'
                                       'tion[Lifetime_Valid_3]#wyc.testing.AllValidVerificationTest.valid'
                                       'Verification[Lifetime_Valid_4]#wyc.testing.AllValidVerificationTe'
                                       'st.validVerification[Lifetime_Valid_5]#wyc.testing.AllValidVerifi'
                                       'cationTest.validVerification[MessageRef_Valid_2]#wyc.testing.AllV'
                                       'alidVerificationTest.validVerification[MessageSend_Valid_2]#wyc.'
                                       'testing.AllValidVerificationTest.validVerification[MessageSend_V'
                                       'alid_3]#wyc.testing.AllValidVerificationTest.validVerification[Me'
                                       'ssageSend_Valid_4]#wyc.testing.AllValidVerificationTest.validVeri'
                                       'fication[MessageSend_Valid_5]#wyc.testing.AllValidVerificationTes'
                                       't.validVerification[MethodCall_Valid_4]#wyc.testing.AllValidVerif'
                                       'icationTest.validVerification[ProcessAccess_Valid_1]#wyc.testing.'
                                       'AllValidVerificationTest.validVerification[Process_Valid_12]#wyc.'
                                       'testing.AllValidVerificationTest.validVerification[Process_Valid_4'
                                       ']#wyc.testing.AllValidVerificationTest.validVerification[Process_V'
                                       'alid_5]#wyc.testing.AllValidVerificationTest.validVerification[Pro'
                                       'cess_Valid_6]#wyc.testing.AllValidVerificationTest.validVerificat'
                                       'ion[Process_Valid_7]#wyc.testing.AllValidVerificationTest.validVer'
                                       'ification[Process_Valid_8]#wyc.testing.AllValidVerificationTest.va'
                                       'lidVerification[RecordAccess_Valid_1]#wyc.testing.AllValidVerifica'
                                       'tionTest.validVerification[Reference_Valid_1]#wyc.testing.AllValid'
                                       'VerificationTest.validVerification[Reference_Valid_7]#wyc.testing.'
                                       'AllValidVerificationTest.validVerification[Reference_Valid_8]')

    def test_build_system_0(self):
        log = "88551597.log"
        job_id = 88551597
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        mf1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(mf1, "Gradle")

    def test_build_system_1(self):
        log = "165108370.log"
        job_id = 165108370
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        mf2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(mf2, "Maven")

    def test_build_system_2(self):
        log = "144826559.log"
        job_id = 144826559
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        mf3 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(mf3, "Gradle")

    def test_build_system_3(self):
        log = "251797108.log"
        job_id = 251797108
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        mf4 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(mf4, "Maven")

    def test_build_system_4(self):
        log = "250416678.log"
        job_id = 250416678
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        mvn1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(mvn1, "Maven")

    def test_build_system_5(self):
        log = "259221978.log"
        job_id = 259221978
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        mvn2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(mvn2, "Maven")

    def test_build_system_6(self):
        log = "161141427.log"
        job_id = 161141427
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        ant1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(ant1, "Ant")

    def test_build_system_7(self):
        log = "81961806.log"
        job_id = 81961806
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        play1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(play1, "play")

    def test_build_system_8(self):
        log = "92030727.log"
        job_id = 92030727
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        play2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(play2, "play")

    def test_build_system_9(self):
        log = "160772310.log"
        job_id = 160772310
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        none2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(none2, "NA")

    def test_build_system_10(self):
        log = "156977713.log"
        job_id = 156977713
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        none3 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(none3, "NA")

    def test_build_system_11(self):
        log = "97793256.log"
        job_id = 97793256
        file_path = "build_system_testing/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        mf5 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_build_system(mf5, "Maven")

    def test_other_analyzer_0(self):
        log = "81961806.log"
        job_id = 81961806
        file_path = "other/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        oa0 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_analyzer(oa0, "java-other")
        self.compare_build_system(oa0, "play")
        self.compare_bool_t_ran(oa0, False)
        self.compare_num_t_run(oa0, 0)
        self.compare_num_t_ok(oa0, "NA")
        self.compare_num_t_failed(oa0, 0)
        self.compare_num_t_skipped(oa0, "NA")
        self.compare_t_duration(oa0, 117.0)

    def test_other_analyzer_1(self):
        log = "81965531.log"
        job_id = 81965531
        file_path = "other/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        oa1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_analyzer(oa1, "java-other")
        self.compare_build_system(oa1, "play")
        self.compare_bool_t_ran(oa1, True)
        self.compare_num_t_run(oa1, 6)
        self.compare_num_t_ok(oa1, 6)
        self.compare_num_t_failed(oa1, 0)
        self.compare_num_t_skipped(oa1, 1)
        self.compare_t_duration(oa1, 174.0)

    def test_other_analyzer_2(self):
        log = "92030727.log"
        job_id = 92030727
        file_path = "other/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        oa2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_analyzer(oa2, "java-other")
        self.compare_build_system(oa2, "play")
        self.compare_bool_t_ran(oa2, False)
        self.compare_num_t_run(oa2, 0)
        self.compare_num_t_ok(oa2, "NA")
        self.compare_num_t_failed(oa2, 0)
        self.compare_num_t_skipped(oa2, "NA")
        self.compare_t_duration(oa2, 115.0)

    def test_other_analyzer_3(self):
        log = "92031917.log"
        job_id = 92031917
        file_path = "other/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        oa3 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_analyzer(oa3, "java-other")
        self.compare_build_system(oa3, "play")
        self.compare_bool_t_ran(oa3, True)
        self.compare_num_t_run(oa3, 5)
        self.compare_num_t_ok(oa3, 5)
        self.compare_num_t_failed(oa3, 0)
        self.compare_num_t_skipped(oa3, 0)
        self.compare_t_duration(oa3, 161.0)

    def test_other_analyzer_4(self):
        log = "156977713.log"
        job_id = 156977713
        file_path = "other/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        oa4 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_analyzer(oa4, "java-other")
        self.compare_build_system(oa4, "NA")
        self.compare_bool_t_ran(oa4, False)
        self.compare_num_t_run(oa4, 0)
        self.compare_num_t_ok(oa4, "NA")
        self.compare_num_t_failed(oa4, 0)
        self.compare_num_t_skipped(oa4, "NA")

    def test_other_analyzer_5(self):
        log = "157259479.log"
        job_id = 157259479
        file_path = "other/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        oa5 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_analyzer(oa5, "java-other")
        self.compare_build_system(oa5, "NA")
        self.compare_bool_t_ran(oa5, True)
        self.compare_num_t_run(oa5, 453)
        self.compare_num_t_ok(oa5, 453)
        self.compare_num_t_failed(oa5, 0)
        self.compare_num_t_skipped(oa5, 0)
        self.compare_t_duration(oa5, 71.0)

    def test_other_analyzer_6(self):
        log = "156977714.log"
        job_id = 156977714
        file_path = "other/" + log
        ts, r = self.get_trigger_sha_and_repo(job_id)
        oa6 = self.dispatcher.analyze(file_path, job_id, trigger_sha=ts, repo=r)
        self.compare_analyzer(oa6, "java-other")
        self.compare_build_system(oa6, "NA")
        self.compare_bool_t_ran(oa6, False)
        self.compare_num_t_run(oa6, 0)
        self.compare_num_t_ok(oa6, "NA")
        self.compare_num_t_failed(oa6, 0)
        self.compare_num_t_skipped(oa6, "NA")

    def test_result_comparer_1(self):
        job_id = 251797108
        o_path = "result_comparer/{}-orig.log".format(job_id)
        r_path = "result_comparer/{}-repr.log".format(job_id)
        ts, r = self.get_trigger_sha_and_repo(job_id)
        build_system = "maven"
        rc1 = self.analyzer.compare_single_log(r_path, o_path, job_id, build_system, ts, r)
        self.compare_rc_match(rc1, False)
        self.compare_rc_mismatch("tr_log_status", rc1, "stopped", "broken")
        self.compare_rc_mismatch("tr_log_bool_tests_ran", rc1, False, True)
        self.compare_rc_mismatch("tr_log_bool_tests_failed", rc1, False, True)
        self.compare_rc_mismatch("tr_log_num_tests_run", rc1, 0, 1646)
        self.compare_rc_mismatch("tr_log_num_tests_ok", rc1, "NA", 1645)
        self.compare_rc_mismatch("tr_log_num_tests_failed", rc1, 0, 1)
        self.compare_rc_mismatch("tr_log_num_tests_skipped", rc1, "NA", 0)
        self.compare_rc_mismatch("tr_log_tests_failed", rc1,
                                 [],
                                 ["testDatasetGroupFiles(loci.plugins.in.ImporterTest)"])

    def test_result_comparer_2(self):
        job_id = 407884143
        o_path = "result_comparer/{}-orig.log".format(job_id)
        r_path = "result_comparer/{}-repr.log".format(job_id)
        ts, r = self.get_trigger_sha_and_repo(job_id)
        build_system = "maven"
        rc1 = self.analyzer.compare_single_log(r_path, o_path, job_id, build_system, ts, r)
        self.compare_rc_match(rc1, False)
        self.compare_rc_mismatch("tr_log_frameworks", "", "pytest")
        self.compare_rc_mismatch("tr_log_bool_tests_ran", rc1, False, True)
        self.compare_rc_mismatch("tr_log_bool_tests_failed", rc1, False, True)
        self.compare_rc_mismatch("tr_log_num_tests_run", rc1, 0, 9856)
        self.compare_rc_mismatch("tr_log_num_tests_ok", rc1, "NA", 9845)
        self.compare_rc_mismatch("tr_log_num_tests_failed", rc1, 0, 11)
        self.compare_rc_mismatch("tr_log_num_tests_skipped", rc1, "NA", 309)
        self.compare_rc_mismatch("tr_log_tests_failed", rc1,
                                 [],
                                 ["sklearn.datasets.tests.test_openml::test_fetch_openml_anneal_multitarget",
                                  "sklearn.datasets.tests.test_openml::test_fetch_openml_iris",
                                  "sklearn.datasets.tests.test_openml::test_fetch_openml_cpu",
                                  "sklearn.datasets.tests.test_openml::test_fetch_openml_australian",
                                  "sklearn.datasets.tests.test_openml::test_warn_ignore_attribute",
                                  "sklearn.datasets.tests.test_openml::test_fetch_openml_iris_multitarget",
                                  "sklearn.datasets.tests.test_openml::test_fetch_openml_anneal",
                                  "sklearn.datasets.tests.test_openml::test_fetch_openml_inactive",
                                  "sklearn.datasets.tests.test_openml::test_fetch_openml_miceprotein",
                                  "sklearn.datasets.tests.test_openml::test_fetch_openml_emotions",
                                  "sklearn.datasets.tests.test_openml::test_fetch_openml_notarget"])


if __name__ == '__main__':
    unittest.main()
