import json
import unittest
import warnings
from os import listdir
from os.path import isfile, join
from unittest.mock import patch

import requests_mock

from bugswarm.analyzer.analyzer import Analyzer
from bugswarm.analyzer.gha_dispatcher import GHADispatcher
from bugswarm.common.github_wrapper import GitHubWrapper

GITHUB_GET = GitHubWrapper.get


def github_get_cached_name(url: str):
    return join('github_data/github_cache/', url.replace('/', '-'))


def github_get_use_cache(self, url: str):
    with open(github_get_cached_name(url), 'r') as f:
        ans = json.load(f)
    with requests_mock.Mocker() as m:
        m.get(url, text=json.dumps(ans))
        return GITHUB_GET(self, url)


@patch('bugswarm.common.github_wrapper.GitHubWrapper.get', github_get_use_cache)
class GitHubAnalyzerTest(unittest.TestCase):
    data_dir = 'github_data/'
    ant = data_dir + 'ant/'
    gradle = data_dir + 'gradle/'
    maven = data_dir + 'maven/'
    python = data_dir + 'python/'
    build_language_not_java = data_dir + 'build_language_not_java/'
    build_system_testing = data_dir + 'build_system_testing/'
    logs = data_dir + 'logs/'
    other = data_dir + 'other/'
    ruby = data_dir + 'ruby/'
    terminated = data_dir + 'terminated/'
    unknowns = data_dir + 'unknowns/'
    javascript_mocha = data_dir + 'javascript/mocha/'
    javascript_jest = data_dir + 'javascript/jest/'
    javascript_multiple_frameworks = data_dir + 'javascript/multiple_frameworks/'
    github_cache = data_dir + 'github_cache/'
    result_comparer = data_dir + 'result_comparer/'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatcher = GHADispatcher()
        self.analyzer = Analyzer()

    @staticmethod
    def my_split(l):
        arr = []
        i_start = 0
        in_quote = 0
        for i_curr in range(len(l)):
            if l[i_curr] == ',' and in_quote == 0:
                w = l[i_start:i_curr]
                arr.append(w)
                i_start = i_curr + 1
            elif l[i_curr] == "'":
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
        if isinstance(s, str):
            if len(s) > 2:
                if s[0] == "'" and s[len(s) - 1] == "'":
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
                    splitted = l.strip().split(',')
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
        return string.replace('"', '')

    # Silence superfluous ResourceWarnings thrown by requests
    # (fix taken from https://github.com/boto/boto3/issues/454#issuecomment-380900404)
    def setUp(self):
        warnings.filterwarnings('ignore', category=ResourceWarning, message='unclosed.*<ssl.SSLSocket.*>')

    # detect_logs_with_build_language_not_in_java
    def test_analyze_primary_language_1(self):
        logs_folder = self.build_language_not_java
        for log in listdir(logs_folder):
            file_path = join(logs_folder, log)
            if isfile(file_path) and log[-4:] == '.log':
                lines, time_lines = GHADispatcher.read_log_into_lines(file_path)
                folds = GHADispatcher.split(lines, time_lines)
                primary_language = GHADispatcher.analyze_primary_language(folds)
                self.check_build_language_not_java(primary_language)

    """
    # detect_logs_with_build_language is ruby
    def test_analyze_primary_language_2(self):
        logs_folder = self.ruby
        for log in listdir(logs_folder):
            file_path = join(logs_folder, log)
            if isfile(file_path) and log[-4:] == '.log':
                lines = GHADispatcher.read_log_into_lines(file_path)
                folds = GHADispatcher.split(lines)
                primary_language = GHADispatcher.analyze_primary_language(folds)
                self.check_build_language(primary_language, 'ruby')
    """

    # detect_logs_with_build_language is unknown
    def test_analyze_primary_language_3(self):
        logs_folder = self.unknowns
        for log in listdir(logs_folder):
            file_path = join(logs_folder, log)
            if isfile(file_path) and log[-4:] == '.log':
                lines, time_lines = GHADispatcher.read_log_into_lines(file_path)
                folds = GHADispatcher.split(lines, time_lines)
                primary_language = GHADispatcher.analyze_primary_language(folds)
                self.check_build_language(primary_language, 'unknown')

    def compare_status(self, result, should_be):
        self.assertEqual(result['tr_log_status'], should_be)

    def compare_analyzer(self, result, should_be):
        self.assertEqual(result['tr_log_analyzer'], should_be)

    def compare_build_system(self, result, should_be):
        self.assertEqual(result['tr_build_system'], should_be)

    def compare_frameworks(self, result, should_be):
        self.assertEqual(result['tr_log_frameworks'], should_be)

    def compare_bool_t_ran(self, result, should_be):
        self.assertEqual(result['tr_log_bool_tests_ran'], should_be)

    def compare_bool_t_failed(self, result, should_be):
        self.assertEqual(result['tr_log_bool_tests_failed'], should_be)

    def compare_num_t_ok(self, result, should_be):
        self.assertEqual(result['tr_log_num_tests_ok'], should_be)

    def compare_num_t_failed(self, result, should_be):
        self.assertEqual(result['tr_log_num_tests_failed'], should_be)

    def compare_num_t_run(self, result, should_be):
        self.assertEqual(result['tr_log_num_tests_run'], should_be)

    def compare_num_t_skipped(self, result, should_be):
        self.assertEqual(result['tr_log_num_tests_skipped'], should_be)

    def compare_t_failed(self, result, should_be):
        self.assertEqual(result['tr_log_tests_failed'], should_be)

    def compare_tr_t_failed(self, result, should_be):
        self.assertEqual(result['tr_log_tests_failed'], should_be)

    def compare_t_duration(self, result, should_be):
        self.assertTrue(self.assert_equal_tolerance(result['tr_log_testduration'], should_be))

    def compare_dep_error(self, result, shouldbe):
        self.assertEqual(result['tr_could_not_resolve_dep'], shouldbe)

    @staticmethod
    def assert_equal_tolerance(p1, p2):
        if p1 - p2 <= 0.01:
            return True
        return False

    def compare_buildduration(self, result, should_be):
        self.assertTrue(self.assert_equal_tolerance(result['tr_log_buildduration'], should_be))

    def compare_setup_time(self, result, should_be):
        self.assertTrue(self.assert_equal_tolerance(result['tr_log_setup_time'], should_be))

    def check_build_language(self, build_log_lang, lang):
        self.assertEqual(build_log_lang, lang)

    def check_build_language_not_java(self, lang):
        self.assertNotEqual(lang, 'java')

    def compare_rc_match(self, result, should_be):
        self.assertEqual(result[0], should_be)
        if result[0]:
            self.assertEqual(result[1], [])
        else:
            self.assertNotEqual(result[1], [])

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
            self.compare_rc_tr_t_failed(target_attr['reproduced'], target_attr['orig'], expected_repr, expected_orig)
        else:
            should_be = {'attr': attr_name, 'reproduced': expected_repr, 'orig': expected_orig}
            self.assertEqual(target_attr, should_be)

    def test_detect_analyzer_maven(self):
        logs_folder = self.maven
        with open(logs_folder + 'test_detect_analyzer_maven.json', 'r') as f:
            data = json.load(f)
        for log in listdir(logs_folder):
            file_path = join(logs_folder, log)
            if isfile(file_path) and file_path[-4:] == '.log':
                job_id = log.split('-')[0]
                trigger_sha = data[job_id]['trigger_sha']
                repo = data[job_id]['repo']
                result = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
                self.compare_analyzer(result, 'java-maven')

    def test_detect_analyzer_gradle(self):
        logs_folder = self.gradle
        with open(logs_folder + 'test_detect_analyzer_gradle.json', 'r') as f:
            data = json.load(f)
        for log in listdir(logs_folder):
            file_path = join(logs_folder, log)
            if isfile(file_path) and log[-4:] == '.log':
                job_id = log.split('-')[0]
                trigger_sha = data[job_id]['trigger_sha']
                repo = data[job_id]['repo']
                result = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
                self.compare_analyzer(result, 'java-gradle')

    def test_detect_failed_function_name_1(self):
        log = 'f0ef4543509d239d4a576d2ce0aea16a1cbc80e5.log'
        job_id = 2295120025
        file_path = join(self.logs, log)
        trigger_sha = 'f0ef4543509d239d4a576d2ce0aea16a1cbc80e5'
        repo = 'alibaba/fastjson2'
        result = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.assertIn('com.alibaba.fastjson2.JSONReaderStrTest', result['tr_log_tests_failed'])

    def test_detect_failed_function_name_2(self):
        log = 'e15bdd7e3d09047d5fed70117b7c3dfd26f3a36e.log'
        job_id = 2499875153
        file_path = join(self.logs, log)
        trigger_sha = 'e15bdd7e3d09047d5fed70117b7c3dfd26f3a36e'
        repo = 'apache/nifi'
        result = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.assertIn(
            'testComponentsRecreatedOnRestart(org.apache.nifi.tests.system.clustering.FlowSynchronizationIT)',
            result['tr_log_tests_failed'])

    def test_maven_0(self):
        log = '1932650872-orig.log'
        job_id = 1932650872
        file_path = join(self.maven, log)
        trigger_sha = 'd8254a834de1b8fe138522a6b7af594be575b508'
        repo = 'codecentric/spring-boot-admin'
        maven0 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven0, 'broken')
        self.compare_analyzer(maven0, 'java-maven')
        self.compare_num_t_run(maven0, 0)
        self.compare_num_t_ok(maven0, 'NA')
        self.compare_num_t_failed(maven0, 0)
        self.compare_num_t_skipped(maven0, 'NA')
        self.compare_bool_t_ran(maven0, False)
        self.compare_bool_t_failed(maven0, False)

    def test_maven_1(self):
        log = '2295120025-orig.log'
        job_id = 2295120025
        file_path = join(self.maven, log)
        trigger_sha = 'f0ef4543509d239d4a576d2ce0aea16a1cbc80e5'
        repo = 'alibaba/fastjson2'
        maven1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven1, 'broken')
        self.compare_analyzer(maven1, 'java-maven')
        self.compare_num_t_run(maven1, 2731)
        self.compare_num_t_ok(maven1, 2730)
        self.compare_num_t_failed(maven1, 1)
        self.compare_num_t_skipped(maven1, 0)
        self.compare_bool_t_ran(maven1, True)
        self.compare_bool_t_failed(maven1, True)
        self.compare_tr_t_failed(maven1, 'test_UUID(com.alibaba.fastjson2.JSONReaderStrTest)')

    def test_maven_2(self):
        log = '2172769214-orig.log'
        job_id = 2172769214
        file_path = join(self.maven, log)
        trigger_sha = '35072801ff54a0f905cc8c617726ac5fea620a11'
        repo = 'Adobe-Consulting-Services/acs-aem-commons'
        maven2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven2, 'broken')
        self.compare_analyzer(maven2, 'java-maven')
        self.compare_num_t_run(maven2, 1868)
        self.compare_num_t_ok(maven2, 1868)
        self.compare_num_t_failed(maven2, 0)
        self.compare_num_t_skipped(maven2, 0)
        self.compare_bool_t_ran(maven2, True)
        self.compare_bool_t_failed(maven2, False)

    def test_maven_3(self):
        log = '2003301608-orig.log'
        job_id = 2003301608
        file_path = join(self.maven, log)
        trigger_sha = 'e3564d66768a87ff4ce643fa4c6f720516057b33'
        repo = 'codecentric/spring-boot-admin'
        maven3 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven3, 'broken')
        self.compare_analyzer(maven3, 'java-maven')
        self.compare_num_t_run(maven3, 505)
        self.compare_num_t_ok(maven3, 504)
        self.compare_num_t_failed(maven3, 1)
        self.compare_num_t_skipped(maven3, 0)
        self.compare_bool_t_ran(maven3, True)
        self.compare_bool_t_failed(maven3, True)
        self.compare_tr_t_failed(maven3, 'lifecycle(de.codecentric.boot.admin.server.cloud.AdminApplicationDiscovery'
                                         'Test)#lifecycle(de.codecentric.boot.admin.server.cloud.AdminApplicationDis'
                                         'coveryTest)#lifecycle(de.codecentric.boot.admin.server.cloud.AdminApplicat'
                                         'ionDiscoveryTest)')

    def test_maven_4(self):
        log = '2320033275-orig.log'
        job_id = 2320033275
        file_path = join(self.maven, log)
        trigger_sha = 'ad9c8d5d3e85e532577ce6d0a686f452c48f0694'
        repo = 'alibaba/fastjson2'
        maven4 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven4, 'broken')
        self.compare_analyzer(maven4, 'java-maven')
        self.compare_num_t_run(maven4, 3627)
        self.compare_num_t_ok(maven4, 3626)
        self.compare_num_t_failed(maven4, 1)
        self.compare_num_t_skipped(maven4, 0)
        self.compare_bool_t_ran(maven4, True)
        self.compare_bool_t_failed(maven4, True)
        self.compare_frameworks(maven4, 'JUnit')
        self.compare_tr_t_failed(maven4, 'test_null(com.alibaba.fastjson.JSONObjectTest)')

    def test_maven_5(self):
        log = '1749803252-orig.log'
        job_id = 1749803252
        file_path = join(self.maven, log)
        trigger_sha = '7c8d22c973fcdc9443a4e22d8cd72ffeb8913db2'
        repo = 'raphw/byte-buddy'
        maven5 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven5, 'broken')
        self.compare_analyzer(maven5, 'java-maven')
        self.compare_num_t_run(maven5, 51)
        self.compare_num_t_ok(maven5, 51)
        self.compare_num_t_failed(maven5, 0)
        self.compare_num_t_skipped(maven5, 0)
        self.compare_bool_t_ran(maven5, True)
        self.compare_bool_t_failed(maven5, False)

    def test_maven_6(self):
        log = '2397394521-orig.log'
        job_id = 2397394521
        file_path = join(self.maven, log)
        trigger_sha = '6afe5ab7a72ec73e34ec100e89ff6a04f94365cb'
        repo = 'qos-ch/slf4j'
        maven6 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven6, 'broken')
        self.compare_analyzer(maven6, 'java-maven')
        self.compare_num_t_run(maven6, 81)
        self.compare_num_t_ok(maven6, 80)
        self.compare_num_t_failed(maven6, 1)
        self.compare_num_t_skipped(maven6, 1)
        self.compare_bool_t_ran(maven6, True)
        self.compare_bool_t_failed(maven6, True)
        self.compare_tr_t_failed(maven6, 'multiThreadedInitialization(org.slf4j.simple.SimpleLoggerMultithreaded'
                                         'InitializationTest)')

    def test_maven_7(self):
        log = '2324344952-orig.log'
        job_id = 2324344952
        file_path = join(self.maven, log)
        trigger_sha = '56c1f30d0f6a6101ff8b340aea3f22ac8e3b00f3'
        repo = 'MyCATApache/Mycat2'
        maven7 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven7, 'broken')
        self.compare_analyzer(maven7, 'java-maven')
        self.compare_num_t_run(maven7, 329)
        self.compare_num_t_ok(maven7, 328)
        self.compare_num_t_failed(maven7, 1)
        self.compare_num_t_skipped(maven7, 6)
        self.compare_bool_t_ran(maven7, True)
        self.compare_bool_t_failed(maven7, True)
        self.compare_tr_t_failed(maven7, 'testInterrupt(io.mycat.exception.ThreadTest)')

    def test_maven_8(self):
        log = '2346499639-orig.log'
        job_id = 2346499639
        file_path = join(self.maven, log)
        trigger_sha = 'b11c77ebcd94c9deb34103c41a789df45eb1b99c'
        repo = 'qos-ch/logback'
        maven8 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven8, 'broken')
        self.compare_analyzer(maven8, 'java-maven')
        self.compare_num_t_run(maven8, 950)
        self.compare_num_t_ok(maven8, 943)
        self.compare_num_t_failed(maven8, 7)
        self.compare_num_t_skipped(maven8, 42)
        self.compare_bool_t_ran(maven8, True)
        self.compare_bool_t_failed(maven8, True)
        self.compare_tr_t_failed(maven8, 'compositePropertyShouldCombineWithinAndWithoutSiftElement(ch.qos.logback.clas'
                                         'sic.sift.SiftingAppenderTest)#propertyDefinedWithinSiftElementShouldBeVisible'
                                         '(ch.qos.logback.classic.sift.SiftingAppenderTest)#fileAppenderCollision(ch.qo'
                                         's.logback.classic.sift.SiftingAppenderTest)#multipleNesting(ch.qos.logback.cl'
                                         'assic.sift.SiftingAppenderTest)#defaultLayoutRule(ch.qos.logback.classic.sift'
                                         '.SiftingAppenderTest)#zeroNesting(ch.qos.logback.classic.sift.SiftingAppender'
                                         'Test)#localPropertiesShouldBeVisible(ch.qos.logback.classic.sift.SiftingAppen'
                                         'derTest)')

    def test_maven_9(self):
        log = '7885474901-orig.log'
        job_id = 7885474901
        file_path = join(self.maven, log)
        trigger_sha = '463a1da96198166f1c0de4fd7b40806a92397078'
        repo = 'scijava/scijava-common'
        maven9 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven9, 'broken')
        self.compare_analyzer(maven9, 'java-maven')
        self.compare_num_t_run(maven9, 768)
        self.compare_num_t_ok(maven9, 766)
        self.compare_num_t_failed(maven9, 2)
        self.compare_num_t_skipped(maven9, 0)
        self.compare_bool_t_ran(maven9, True)
        self.compare_bool_t_failed(maven9, True)
        self.compare_tr_t_failed(maven9, 'testArrayConvertFromStringCommandWildcardGenerics(org.scijava.command.Command'
                                         'ArrayConverterTest)#testArrayConvertFromStringCommandRaw(org.scijava.command'
                                         '.CommandArrayConverterTest)')

    def test_status_terminated(self):
        log = '2026328035.log'
        job_id = 2026328035
        file_path = join(self.terminated, log)
        trigger_sha = '9b1628f2663ac68fd89f8802c61af3c032ba2506'
        repo = 'apache/dubbo'
        result = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(result, 'cancelled')

    def test_status_empty_log(self):
        log = '8859027590.log'
        job_id = 8859027590
        file_path = join(self.other, log)
        trigger_sha = 'fa4dc5fc63cd6c27fbf53b4677007246fa258fb2'
        repo = 'Xilinx/RapidWright'
        result = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(result, 'ok')

    def test_python_0(self):
        # Nosetests
        log = '2422710472-orig.log'
        job_id = 2422710472
        file_path = join(self.python, log)
        python0 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python0, 'broken')
        self.compare_analyzer(python0, 'python')
        self.compare_num_t_run(python0, 7)
        self.compare_num_t_ok(python0, 6)
        self.compare_num_t_failed(python0, 1)
        self.compare_num_t_skipped(python0, 1)
        self.compare_bool_t_ran(python0, True)
        self.compare_bool_t_failed(python0, True)
        self.compare_t_duration(python0, 130.309)
        self.compare_tr_t_failed(python0, 'test.rosdistro_verify_test.test_verify_files_identical')
        self.compare_frameworks(python0, 'unittest')

    def test_python_1(self):
        log = '2446151667-orig.log'
        job_id = 2446151667
        file_path = join(self.python, log)
        python1 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python1, 'broken')
        self.compare_analyzer(python1, 'python')
        self.compare_num_t_run(python1, 3)
        self.compare_num_t_ok(python1, 2)
        self.compare_num_t_failed(python1, 1)
        self.compare_num_t_skipped(python1, 0)
        self.compare_bool_t_ran(python1, True)
        self.compare_bool_t_failed(python1, True)
        self.compare_t_duration(python1, 19.26)
        self.compare_tr_t_failed(python1, 'tests.bench::test_text_extraction')
        self.compare_frameworks(python1, 'pytest')

    def test_python_2(self):
        log = '2360239904-orig.log'
        job_id = 2360239904
        file_path = join(self.python, log)
        python2 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python2, 'broken')
        self.compare_analyzer(python2, 'python')
        self.compare_num_t_run(python2, 393)
        self.compare_num_t_ok(python2, 383)
        self.compare_num_t_failed(python2, 10)
        self.compare_num_t_skipped(python2, 17)
        self.compare_bool_t_ran(python2, True)
        self.compare_bool_t_failed(python2, True)
        self.compare_t_duration(python2, 243.93)
        self.compare_tr_t_failed(python2, 'tests.deployment.sagemaker.test_sagemaker::'
                                          'test_sagemaker_apply_fail_not_local_repo#'
                                          'tests.deployment.sagemaker.test_sagemaker::test_sagemaker_apply_success#'
                                          'tests.deployment.sagemaker.test_sagemaker::'
                                          'test_sagemaker_apply_create_model_fail#'
                                          'tests.deployment.sagemaker.test_sagemaker::'
                                          'test_sagemaker_apply_delete_model_fail#'
                                          'tests.deployment.sagemaker.test_sagemaker::'
                                          'test_sagemaker_apply_duplicate_endpoint#'
                                          'tests.deployment.sagemaker.test_sagemaker::'
                                          'test_sagemaker_update_deployment_with_new_bento_service_tag#'
                                          'tests.yatai.test_grpc_server_interceptor::TestMetrics::test_grpc_server_'
                                          'metrics_0_grpc_server_started_total_grpc_method_Execute_grpc_service_bentoml'
                                          '_MockService_grpc_type_UNARY_#tests.yatai.test_grpc_server_interceptor::'
                                          'TestMetrics::test_grpc_server_metrics_1_grpc_server_started_total_grpc_'
                                          'method_Execute_grpc_service_bentoml_MockService_grpc_type_UNARY_#'
                                          'tests.yatai.test_grpc_server_interceptor::TestMetrics::'
                                          'test_grpc_server_metrics_2_grpc_server_started_total_grpc_method_Execute_'
                                          'grpc_service_bentoml_MockService_grpc_type_UNARY_#'
                                          'tests.yatai.test_grpc_server_interceptor::TestMetrics::test_grpc_server_'
                                          'metrics_3_grpc_server_handled_total_grpc_code_OK_grpc_method_Execute_grpc_'
                                          'service_bentoml_MockService_grpc_type_UNARY_')
        self.compare_frameworks(python2, 'pytest')

    def test_python_3(self):
        log = '2511451902-orig.log'
        job_id = 2511451902
        file_path = join(self.python, log)
        python3 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python3, 'broken')
        self.compare_analyzer(python3, 'python')
        self.compare_num_t_run(python3, 175)
        self.compare_num_t_ok(python3, 174)
        self.compare_num_t_failed(python3, 1)
        self.compare_num_t_skipped(python3, 22)
        self.compare_bool_t_ran(python3, True)
        self.compare_bool_t_failed(python3, True)
        self.compare_t_duration(python3, 156.56)
        self.compare_tr_t_failed(python3, 'test_d2go_runner_train_qat_hook_update_stat (runner.test_runner_default_'
                                          'runner.TestDefaultRunner)')
        self.compare_frameworks(python3, 'unittest')

    def test_python_4(self):
        log = '2283578153-orig.log'
        job_id = 2283578153
        file_path = join(self.python, log)
        python4 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python4, 'broken')
        self.compare_analyzer(python4, 'python')
        self.compare_num_t_run(python4, 1957)
        self.compare_num_t_ok(python4, 1956)
        self.compare_num_t_failed(python4, 1)
        self.compare_num_t_skipped(python4, 0)
        self.compare_bool_t_ran(python4, True)
        self.compare_bool_t_failed(python4, True)
        self.compare_t_duration(python4, 356.48)
        self.compare_tr_t_failed(python4, 'gammapy.irf.psf.tests.test_parametric::test_psf_king_containment_radius')
        self.compare_frameworks(python4, 'pytest')

    def test_python_5(self):
        log = '2024423709-orig.log'
        job_id = 2024423709
        file_path = join(self.python, log)
        python5 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python5, 'broken')
        self.compare_analyzer(python5, 'python')
        self.compare_num_t_run(python5, 1098)
        self.compare_num_t_ok(python5, 1062)
        self.compare_num_t_failed(python5, 36)
        self.compare_num_t_skipped(python5, 544)
        self.compare_bool_t_ran(python5, True)
        self.compare_bool_t_failed(python5, True)
        self.compare_t_duration(python5, 48.40)
        # Too many failed tests, select few unique one to match
        self.assertEqual(len(python5['tr_log_tests_failed'].split('#')), 36)
        self.assertIn('gammapy.datasets.tests.test_map::test_downsample_energy', python5['tr_log_tests_failed'])
        self.assertIn('gammapy.datasets.tests.test_spectrum::TestSpectrumOnOff::test_to_from_ogip_files',
                      python5['tr_log_tests_failed'])
        self.assertIn('gammapy.estimators.map.tests.test_core::test_get_flux_point', python5['tr_log_tests_failed'])
        self.assertIn('gammapy.irf.edisp.tests.test_map::test_edisp_from_diagonal_response[0d 0d]',
                      python5['tr_log_tests_failed'])
        self.assertIn('gammapy.irf.edisp.tests.test_map::test_edisp_from_diagonal_response[180d -90d]',
                      python5['tr_log_tests_failed'])
        self.assertIn('gammapy.irf.edisp.tests.test_kernel::TestEDispKernel::test_io', python5['tr_log_tests_failed'])
        self.assertIn('gammapy.irf.edisp.tests.test_kernel::TestEDispKernel::test_peek', python5['tr_log_tests_failed'])
        self.compare_frameworks(python5, 'pytest')

    def test_python_6(self):
        log = '2267219366-orig.log'
        job_id = 2267219366
        file_path = join(self.python, log)
        python6 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python6, 'broken')
        self.compare_analyzer(python6, 'python')
        self.compare_num_t_run(python6, 1934)
        self.compare_num_t_ok(python6, 1933)
        self.compare_num_t_failed(python6, 1)
        self.compare_num_t_skipped(python6, 0)
        self.compare_bool_t_ran(python6, True)
        self.compare_bool_t_failed(python6, True)
        self.compare_t_duration(python6, 150.93)
        self.compare_tr_t_failed(python6, 'tests.integration.test_mongodb::TestMongoCache::test_ttl')
        self.compare_frameworks(python6, 'pytest')

    def test_python_7(self):
        log = '2506527647-orig.log'
        job_id = 2506527647
        file_path = join(self.python, log)
        python7 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python7, 'broken')
        self.compare_analyzer(python7, 'python')
        self.compare_num_t_run(python7, 47)
        self.compare_num_t_ok(python7, 46)
        self.compare_num_t_failed(python7, 1)
        self.compare_num_t_skipped(python7, 0)
        self.compare_bool_t_ran(python7, True)
        self.compare_bool_t_failed(python7, True)
        self.compare_t_duration(python7, 20.273)
        self.compare_tr_t_failed(python7, 'test_parameters (test_part.PartTest)')
        self.compare_frameworks(python7, 'unittest')

    def test_python_8(self):
        log = '2512030835-orig.log'
        job_id = 2512030835
        file_path = join(self.python, log)
        python8 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python8, 'broken')
        self.compare_analyzer(python8, 'python')
        self.compare_num_t_run(python8, 5)
        self.compare_num_t_ok(python8, 0)
        self.compare_num_t_failed(python8, 5)
        self.compare_num_t_skipped(python8, 0)
        self.compare_bool_t_ran(python8, True)
        self.compare_bool_t_failed(python8, True)
        self.compare_t_duration(python8, 1.81)
        self.compare_tr_t_failed(python8, '(kubernetes.e2e_test.test_apps)#(kubernetes.e2e_test.test_batch)#'
                                          '(kubernetes.e2e_test.test_client)#(kubernetes.e2e_test.test_utils)#'
                                          '(kubernetes.e2e_test.test_watch)')
        self.compare_frameworks(python8, 'pytest')

    def test_python_9(self):
        log = '2512051754-orig.log'
        job_id = 2512051754
        file_path = join(self.python, log)
        python9 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python9, 'ok')
        self.compare_analyzer(python9, 'python')
        self.compare_num_t_run(python9, 32)
        self.compare_num_t_ok(python9, 32)
        self.compare_num_t_failed(python9, 0)
        self.compare_num_t_skipped(python9, 0)
        self.compare_bool_t_ran(python9, True)
        self.compare_bool_t_failed(python9, False)
        self.compare_t_duration(python9, 48.55)
        self.compare_tr_t_failed(python9, '')
        self.compare_frameworks(python9, 'pytest')

    def test_python_10(self):
        log = '2424147467-orig.log'
        job_id = 2424147467
        file_path = join(self.python, log)
        python10 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python10, 'broken')
        self.compare_analyzer(python10, 'python')
        self.compare_num_t_run(python10, 43261)
        self.compare_num_t_ok(python10, 43260)
        self.compare_num_t_failed(python10, 1)
        self.compare_num_t_skipped(python10, 4)
        self.compare_bool_t_ran(python10, True)
        self.compare_bool_t_failed(python10, True)
        self.compare_t_duration(python10, 761.24)
        self.compare_tr_t_failed(python10, 'functional.autoprompt.test_prompttoolkit::TestCompletions::'
                                           'test_switch_to_multicolumn_mode')
        self.compare_frameworks(python10, 'pytest')

    def test_python_11(self):
        log = '2511268285-orig.log'
        job_id = 2511268285
        file_path = join(self.python, log)
        python11 = self.dispatcher.analyze(file_path, job_id)
        self.compare_analyzer(python11, 'python')
        self.compare_num_t_run(python11, 55)
        self.compare_num_t_ok(python11, 37)
        self.compare_num_t_failed(python11, 18)
        self.compare_num_t_skipped(python11, 0)
        self.compare_bool_t_ran(python11, True)
        self.compare_bool_t_failed(python11, True)
        self.compare_t_duration(python11, 6.865)
        self.compare_frameworks(python11, 'unittest')
        self.compare_tr_t_failed(python11, 'tests.test_detectron2 (unittest.loader._FailedTest)#'
                                           'tests.test_layer (unittest.loader._FailedTest)#'
                                           'test_convert_original_predictions_with_mask_output '
                                           '(tests.test_mmdetectionmodel.TestMmdetDetectionModel)#'
                                           'test_convert_original_predictions_without_mask_output '
                                           '(tests.test_mmdetectionmodel.TestMmdetDetectionModel)#'
                                           'test_load_model (tests.test_mmdetectionmodel.TestMmdetDetectionModel)#'
                                           'test_perform_inference_with_mask_output '
                                           '(tests.test_mmdetectionmodel.TestMmdetDetectionModel)#'
                                           'test_perform_inference_without_mask_output '
                                           '(tests.test_mmdetectionmodel.TestMmdetDetectionModel)#'
                                           'test_coco_json_prediction (tests.test_predict.TestPredict)#'
                                           'test_get_prediction_automodel_yolov5 (tests.test_predict.TestPredict)#'
                                           'test_get_prediction_mmdet (tests.test_predict.TestPredict)#'
                                           'test_get_prediction_yolov5 (tests.test_predict.TestPredict)#'
                                           'test_get_sliced_prediction_mmdet (tests.test_predict.TestPredict)#'
                                           'test_get_sliced_prediction_yolov5 (tests.test_predict.TestPredict)#'
                                           'test_video_prediction (tests.test_predict.TestPredict)#'
                                           'test_convert_original_predictions '
                                           '(tests.test_yolov5model.TestYolov5DetectionModel)#'
                                           'test_load_model (tests.test_yolov5model.TestYolov5DetectionModel)#'
                                           'test_perform_inference (tests.test_yolov5model.TestYolov5DetectionModel)#'
                                           'test_set_model (tests.test_yolov5model.TestYolov5DetectionModel)')

    def test_python_12(self):
        log = '2511279398-orig.log'
        job_id = 2511279398
        file_path = join(self.python, log)
        python12 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python12, 'ok')
        self.compare_analyzer(python12, 'python')
        self.compare_num_t_run(python12, 55)
        self.compare_num_t_ok(python12, 55)
        self.compare_num_t_failed(python12, 0)
        self.compare_num_t_skipped(python12, 0)
        self.compare_bool_t_ran(python12, True)
        self.compare_bool_t_failed(python12, False)
        self.compare_t_duration(python12, 91.890)
        self.compare_frameworks(python12, 'unittest')
        self.compare_tr_t_failed(python12, '')

    def test_python_13(self):
        log = '2496945256-orig.log'
        job_id = 2496945256
        file_path = join(self.python, log)
        python13 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python13, 'broken')
        self.compare_analyzer(python13, 'python')
        self.compare_num_t_run(python13, 2604)
        self.compare_num_t_ok(python13, 2603)
        self.compare_num_t_failed(python13, 1)
        self.compare_num_t_skipped(python13, 914)
        self.compare_bool_t_ran(python13, True)
        self.compare_bool_t_failed(python13, True)
        self.compare_frameworks(python13, 'unittest')
        self.compare_tr_t_failed(python13, 'test_The_watch_helper_must_not_throw_a_custom_exception_when_executed_'
                                           'against_a_single_server_topology,_but_instead_depend_on_a_server_error '
                                           '(test_change_stream.TestUnifiedChangeStreamsErrors)')

    def test_python_14(self):
        # Multiple tests were killed due to segfault.
        log = '2512083654-orig.log'
        job_id = 2512083654
        file_path = join(self.python, log)
        python14 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python14, 'broken')
        self.compare_analyzer(python14, 'python')
        self.compare_num_t_run(python14, 0)
        self.compare_num_t_ok(python14, 0)
        self.compare_num_t_failed(python14, 0)
        self.compare_num_t_skipped(python14, 0)
        self.compare_bool_t_ran(python14, True)
        self.compare_bool_t_failed(python14, False)
        self.compare_frameworks(python14, 'pytest')
        self.compare_tr_t_failed(python14, '')

    def test_python_15(self):
        # Extremely long test status
        log = '2163834915-orig.log'
        job_id = 2163834915
        file_path = join(self.python, log)
        python15 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python15, 'broken')
        self.compare_analyzer(python15, 'python')
        self.compare_num_t_run(python15, 803)
        self.compare_num_t_ok(python15, 802)
        self.compare_num_t_failed(python15, 1)
        self.compare_num_t_skipped(python15, 66)
        self.compare_bool_t_ran(python15, True)
        self.compare_bool_t_failed(python15, True)
        self.compare_t_duration(python15, 1284.21)
        self.compare_frameworks(python15, 'pytest')
        self.compare_tr_t_failed(python15, 'tests.test_core::test_sys_entities_normalized_token_span'
                                           '[ok 2:30pm now-valid_spans10-sys_time]')

    def test_python_16(self):
        # Language detection failed. It needs to repo to detect primary language.
        log = '2516961170-orig.log'
        job_id = 2516961170
        file_path = join(self.python, log)
        trigger_sha = '3eef7e3febd6b74595be61373569a9c95bd83c76'
        repo = 'commaai/openpilot'
        python16 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(python16, 'broken')
        self.compare_analyzer(python16, 'python')
        self.compare_num_t_run(python16, 414)
        self.compare_num_t_ok(python16, 413)
        self.compare_num_t_failed(python16, 1)
        self.compare_num_t_skipped(python16, 178)
        self.compare_bool_t_ran(python16, True)
        self.compare_bool_t_failed(python16, True)
        self.compare_frameworks(python16, 'unittest')
        self.compare_tr_t_failed(
            python16, 'test_no_duplicate_fw_versions (tests.test_fw_fingerprint.TestFwFingerprint)')

    def test_python_17(self):
        # Nosetests
        log = '2477898638-orig.log'
        job_id = 2477898638
        file_path = join(self.python, log)
        python17 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python17, 'broken')
        self.compare_analyzer(python17, 'python')
        self.compare_num_t_run(python17, 7)
        self.compare_num_t_ok(python17, 3)
        self.compare_num_t_failed(python17, 4)
        self.compare_num_t_skipped(python17, 1)
        self.compare_bool_t_ran(python17, True)
        self.compare_bool_t_failed(python17, True)
        self.compare_frameworks(python17, 'unittest')
        self.compare_tr_t_failed(
            python17, 'test.rosdep_duplicates_test.test_rosdep_duplicates#'
            'test.rosdistro_check_urls_test.test_rosdistro_urls#'
            'test.rosdistro_verify_test.test_verify_files_identical#'
            'test.test_build_caches.test_build_caches')

    def test_python_18(self):
        # No run tests, stopped due to errors during setup (pytest)
        log = '2350842179-orig.log'
        job_id = 2350842179
        file_path = join(self.python, log)
        python18 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python18, 'broken')
        self.compare_analyzer(python18, 'python')
        self.compare_num_t_run(python18, 11)
        self.compare_num_t_ok(python18, 0)
        self.compare_num_t_failed(python18, 11)
        self.compare_num_t_skipped(python18, 0)
        self.compare_bool_t_ran(python18, True)
        self.compare_bool_t_failed(python18, True)
        self.compare_frameworks(python18, 'pytest')
        self.compare_tr_t_failed(python18, '(tests.bert_corrector_test)#(tests.detector_test)#'
                                           '(tests.en_spell_bug_fix_test)#(tests.en_spell_correct_test)#'
                                           '(tests.ernie_csc_corrector_test)#(tests.file_correct_test)#'
                                           '(tests.kenlm_test)#(tests.macbert_corrector_test)#'
                                           '(tests.simplified_traditional_sentence_test)#'
                                           '(tests.speed_test)#(tests.trigram_test)')

    def test_python_19(self):
        # Tests didn't run due to exception
        log = '2468864400-orig.log'
        job_id = 2468864400
        file_path = join(self.python, log)
        python19 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python19, 'broken')
        self.compare_analyzer(python19, 'python')
        self.compare_num_t_run(python19, 0)
        self.compare_num_t_ok(python19, 'NA')
        self.compare_num_t_failed(python19, 0)
        self.compare_num_t_skipped(python19, 'NA')
        self.compare_bool_t_ran(python19, False)
        self.compare_bool_t_failed(python19, False)
        self.compare_frameworks(python19, '')
        self.compare_tr_t_failed(python19, '')

    def test_python_20(self):
        # No path to class (missing tests file)
        log = '2505733928-orig.log'
        job_id = 2505733928
        file_path = join(self.python, log)
        python20 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python20, 'broken')
        self.compare_analyzer(python20, 'python')
        self.compare_num_t_run(python20, 43)
        self.compare_num_t_ok(python20, 40)
        self.compare_num_t_failed(python20, 3)
        self.compare_num_t_skipped(python20, 0)
        self.compare_bool_t_ran(python20, True)
        self.compare_bool_t_failed(python20, True)
        self.compare_frameworks(python20, 'pytest')
        self.compare_tr_t_failed(
            python20, 'kat[MergeSlashesDisabled]#kat[MergeSlashesEnabled]#kat[LongClusterNameMapping]')

    def test_python_21(self):
        # No run tests, stopped due to errors during setup, no short summary (pytest)
        log = '2062223369-orig.log'
        job_id = 2062223369
        file_path = join(self.python, log)
        python21 = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(python21, 'broken')
        self.compare_analyzer(python21, 'python')
        self.compare_num_t_run(python21, 13)
        self.compare_num_t_ok(python21, 0)
        self.compare_num_t_failed(python21, 13)
        self.compare_num_t_skipped(python21, 0)
        self.compare_bool_t_ran(python21, True)
        self.compare_bool_t_failed(python21, True)
        self.compare_t_duration(python21, 3.74)
        self.compare_frameworks(python21, 'pytest')
        self.compare_tr_t_failed(python21, '(test.unittests.audio.test_service)#(test.unittests.audio.test_speech)#'
                                           '(test.unittests.client.test_audio_consumer)#'
                                           '(test.unittests.client.test_hotword_factory)#'
                                           '(test.unittests.client.test_local_recognizer)#'
                                           '(test.unittests.stt.test_stt)#(test.unittests.tts.test_cache)#'
                                           '(test.unittests.tts.test_espeak_tts)#(test.unittests.tts.test_google_tts)#'
                                           '(test.unittests.tts.test_mimic2_tts)#(test.unittests.tts.test_mimic_tts)#'
                                           '(test.unittests.tts.test_tts)#(test.unittests.util.test_plugins)')

    """
    def test_python_22(self):
        log = '327327997-latest.log'
        job_id = 3327327997
        file_path = join(self.python, log)
        python22 = self.dispatcher.analyze(file_path, job_id)
        self.compare_analyzer(python22, 'python')
        self.compare_num_t_ok(python22, 212)
        self.compare_num_t_failed(python22, 0)
        self.compare_num_t_skipped(python22, 14)
        self.compare_bool_t_ran(python22, True)
        self.compare_bool_t_failed(python22, False)
        self.compare_t_duration(python22, 114.16)
        self.compare_num_t_run(python22, 212)
        self.compare_frameworks(python22, 'pytest')
    """

    def test_gradle_0(self):
        log = '2085562467-orig.log'
        job_id = 2085562467
        file_path = join(self.gradle, log)
        trigger_sha = '92f8e211e05f5a762f583a6f6c7165a879fe45e7'
        repo = 'junit-team/junit5'
        gradle0 = self.dispatcher.analyze(file_path, job_id,
                                          trigger_sha=trigger_sha, repo=repo)

        self.compare_status(gradle0, 'broken')
        self.compare_analyzer(gradle0, 'java-gradle')
        self.compare_num_t_run(gradle0, 0)
        self.compare_num_t_failed(gradle0, 0)
        self.compare_bool_t_ran(gradle0, False)
        self.compare_bool_t_failed(gradle0, False)

    def test_gradle_1(self):
        log = '2063953546-orig.log'
        job_id = 2063953546
        file_path = join(self.gradle, log)
        trigger_sha = '16fd4912b4824879ce87d4e978b8f91eead220fe'
        repo = 'michel-kraemer/gradle-download-task'
        gradle1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle1, 'broken')
        self.compare_analyzer(gradle1, 'java-gradle')
        self.compare_num_t_run(gradle1, 182)
        self.compare_num_t_ok(gradle1, 177,)
        self.compare_num_t_failed(gradle1, 5)
        self.compare_num_t_skipped(gradle1, 1)
        self.compare_bool_t_ran(gradle1, True)
        self.compare_bool_t_failed(gradle1, True)
        self.compare_tr_t_failed(gradle1, 'DownloadExtensionTest.downloadSingleFileError()#'
                                          'FunctionalDownloadTest.downloadExtensionShouldNotFailTask()#'
                                          'FunctionalDownloadTest.downloadExtensionShouldNotFailTask()#'
                                          'FunctionalDownloadTest.downloadExtensionShouldNotFailTask()#'
                                          'FunctionalDownloadTest.downloadExtensionShouldNotFailTask()')

    def test_gradle_2(self):
        log = '2287628269-orig.log'
        job_id = 2287628269
        file_path = join(self.gradle, log)
        trigger_sha = 'ab7da674eb6cfffd28b9b5f6bc597055f8d4c0e0'
        repo = 'nokeedev/gradle-native'
        gradle2 = self.dispatcher.analyze(file_path, job_id,
                                          trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle2, 'broken')
        self.compare_analyzer(gradle2, 'java-gradle')
        self.compare_num_t_run(gradle2, 705)
        self.compare_num_t_ok(gradle2, 684)
        self.compare_num_t_failed(gradle2, 21)
        self.compare_num_t_skipped(gradle2, 213)
        self.compare_bool_t_ran(gradle2, True)
        self.compare_bool_t_failed(gradle2, True)
        self.compare_tr_t_failed(gradle2, 'ConfigurationCacheDetectsXcodeProjectInitializationFunctionalTest.'
                                          'initializationError#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceChangesFunctionalTest.'
                                          'doesNotReuseConfigurationCacheWhenWorkspaceContentChange()#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceChangesFunctionalTest.'
                                          'reuseConfigurationCacheWhenWorkspaceContentChangeInNonMeaningfulWay()#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceChangesFunctionalTest.'
                                          'reuseConfigurationCacheWhenOnlyUserDataChanged()#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceChangesFunctionalTest.'
                                          'doesNotReuseConfigurationCacheWhenNewWorkspaceFound()#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceInitializationFunctionalTest.'
                                          'initializationError#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceInitializationOverriding'
                                          'XcodeProjectFunctionalTest.initializationError')

    def test_gradle_3(self):
        log = '2464471085-orig.log'
        job_id = 2464471085
        file_path = join(self.gradle, log)
        trigger_sha = '0e38d94b62619294e5d184d6c874b52e6e3a956d'
        repo = 'apple/servicetalk'
        gradle3 = self.dispatcher.analyze(file_path, job_id,
                                          trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle3, 'broken')
        self.compare_analyzer(gradle3, 'java-gradle')
        self.compare_num_t_run(gradle3, 3867)
        self.compare_num_t_ok(gradle3, 3866)
        self.compare_num_t_failed(gradle3, 1)
        self.compare_num_t_skipped(gradle3, 91)
        self.compare_bool_t_ran(gradle3, True)
        self.compare_bool_t_failed(gradle3, True)
        self.compare_tr_t_failed(
            gradle3,
            'io.servicetalk.http.netty.ClientEffectiveStrategyTest.clientStrategy(BuilderType, HttpExecutionStrategy, '
            'HttpExecutionStrategy, HttpExecutionStrategy, HttpExecutionStrategy)[3]')

    def test_gradle_4(self):
        log = '2160401079-orig.log'
        job_id = 2160401079
        file_path = join(self.gradle, log)
        trigger_sha = '4141e33b965c52491197e1ef64bb624c15354596'
        repo = 'apple/servicetalk'
        gradle4 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle4, 'broken')
        self.compare_analyzer(gradle4, 'java-gradle')
        self.compare_num_t_run(gradle4, 705)
        self.compare_num_t_ok(gradle4, 684)
        self.compare_num_t_failed(gradle4, 21)
        self.compare_num_t_skipped(gradle4, 213)
        self.compare_bool_t_ran(gradle4, True)
        self.compare_bool_t_failed(gradle4, True)
        self.compare_tr_t_failed(gradle4, 'ConfigurationCacheDetectsXcodeProjectInitializationFunctionalTest.'
                                          'initializationError#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceChangesFunctionalTest.'
                                          'doesNotReuseConfigurationCacheWhenWorkspaceContentChange()#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceChangesFunctionalTest.'
                                          'reuseConfigurationCacheWhenWorkspaceContentChangeInNonMeaningfulWay()#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceChangesFunctionalTest.'
                                          'reuseConfigurationCacheWhenOnlyUserDataChanged()#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceChangesFunctionalTest.'
                                          'doesNotReuseConfigurationCacheWhenNewWorkspaceFound()#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceInitializationFunctionalTest.'
                                          'initializationError#'
                                          'ConfigurationCacheDetectsXcodeWorkspaceInitializationOverriding'
                                          'XcodeProjectFunctionalTest.initializationError')

    def test_gradle_5(self):
        log = '2307899709-orig.log'
        job_id = 2307899709
        file_path = join(self.gradle, log)
        trigger_sha = 'bc6be6387118cd2651ae733ed09f50b69d661162'
        repo = 'open-telemetry/opentelemetry-java'
        gradle5 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle5, 'broken')
        self.compare_analyzer(gradle5, 'java-gradle')
        self.compare_num_t_run(gradle5, 40)
        self.compare_num_t_ok(gradle5, 39)
        self.compare_num_t_failed(gradle5, 1)
        self.compare_num_t_skipped(gradle5, 0)
        self.compare_bool_t_ran(gradle5, True)
        self.compare_bool_t_failed(gradle5, True)
        self.compare_tr_t_failed(gradle5, 'RetryInterceptorTest.connectTimeout()')

    def test_gradle_6(self):
        log = '2371715232-orig.log'
        job_id = 2371715232
        file_path = join(self.gradle, log)
        trigger_sha = '176f64cfe3e6f566d650f0730e2e5ec1522d7d3a'
        repo = 'apache/poi'
        gradle6 = self.dispatcher.analyze(file_path, job_id,
                                          trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle6, 'broken')
        self.compare_analyzer(gradle6, 'java-gradle')
        self.compare_num_t_run(gradle6, 6870)
        self.compare_num_t_ok(gradle6, 6866)
        self.compare_num_t_failed(gradle6, 4)
        self.compare_num_t_skipped(gradle6, 28)
        self.compare_bool_t_ran(gradle6, True)
        self.compare_bool_t_failed(gradle6, True)
        self.compare_frameworks(gradle6, 'JUnit')
        self.compare_tr_t_failed(gradle6, 'org.apache.poi.ss.formula.eval.TestFormulasFromSpreadsheet.'
                                          'processFunctionRow(String, int, int)[48]#'
                                          'org.apache.poi.ss.formula.eval.TestFormulasFromSpreadsheet.'
                                          'processFunctionRow(String, int, int)[135]#'
                                          'TestMathX.testFloor()#TestMathX.testCeiling()')

    def test_gradle_7(self):
        log = '2398880548-orig.log'
        job_id = 2398880548
        file_path = join(self.gradle, log)
        trigger_sha = '6dbd1d8f586f0fbfecee1ca57665ea75bd06b838'
        repo = 'grpc/grpc-java'
        gradle7 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle7, 'broken')
        self.compare_analyzer(gradle7, 'java-gradle')
        self.compare_num_t_run(gradle7, 375)
        self.compare_num_t_ok(gradle7, 374)
        self.compare_num_t_failed(gradle7, 1)
        self.compare_num_t_skipped(gradle7, 28)
        self.compare_bool_t_ran(gradle7, True)
        self.compare_bool_t_failed(gradle7, True)
        self.compare_frameworks(gradle7, 'JUnit')
        self.compare_tr_t_failed(gradle7, 'io.grpc.testing.integration.NettyFlowControlTest.largeBdp')

    def test_gradle_8(self):
        # Has super long and complex tests_failed
        log = '2489325318-orig.log'
        job_id = 2489325318
        file_path = join(self.gradle, log)
        trigger_sha = '0784d64a659abd4fdaa82cdb599a250a7514facf'
        repo = 'apache/iceberg'
        gradle8 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle8, 'broken')
        self.compare_analyzer(gradle8, 'java-gradle')
        self.compare_num_t_run(gradle8, 873)
        self.compare_num_t_ok(gradle8, 871)
        self.compare_num_t_failed(gradle8, 2)
        self.compare_num_t_skipped(gradle8, 32)
        self.compare_bool_t_ran(gradle8, True)
        self.compare_bool_t_failed(gradle8, True)
        self.compare_frameworks(gradle8, 'JUnit')
        self.compare_tr_t_failed(gradle8, 'org.apache.iceberg.spark.extensions.TestCopyOnWriteUpdate.testUpdateWithout'
                                          'Condition[catalogName = testhive, implementation = org.apache.iceberg.spark'
                                          '.SparkCatalog, config = {type=hive, default-namespace=default}, format = or'
                                          'c, vectorized = true, distributionMode = none]#'
                                          'org.apache.iceberg.spark.extensions.TestCopyOnWriteUpdate.testUpdateWithout'
                                          'Condition[catalogName = spark_catalog, implementation = org.apache.iceberg.'
                                          'spark.SparkSessionCatalog, config = {type=hive, default-namespace=default, '
                                          'clients=1, parquet-enabled=false, cache-enabled=false}, format = avro, vect'
                                          'orized = false, distributionMode = range]')

    def test_gradle_9(self):
        # No failed test
        log = '2556516385-orig.log'
        job_id = 2556516385
        file_path = join(self.gradle, log)
        trigger_sha = 'c60743cfab4e31214207da5dab44fc4426d53764'
        repo = 'traccar/traccar'
        gradle9 = self.dispatcher.analyze(file_path, job_id,
                                          trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle9, 'ok')
        self.compare_analyzer(gradle9, 'java-gradle')
        self.compare_num_t_run(gradle9, 0)
        self.compare_num_t_ok(gradle9, 'NA')
        self.compare_num_t_failed(gradle9, 0)
        self.compare_num_t_skipped(gradle9, 'NA')
        self.compare_bool_t_ran(gradle9, False)
        self.compare_bool_t_failed(gradle9, False)
        self.compare_tr_t_failed(gradle9, '')

    def test_gradle_10(self):
        log = '2544985503-orig.log'
        job_id = 2544985503
        file_path = join(self.gradle, log)
        trigger_sha = '6a72ddd3e1975c53043db7105b581e1ee52f6ab8'
        repo = 'JabRef/jabref'
        gradle10 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(gradle10, 'broken')
        self.compare_analyzer(gradle10, 'java-gradle')
        self.compare_num_t_run(gradle10, 8048)
        self.compare_num_t_ok(gradle10, 8047)
        self.compare_num_t_failed(gradle10, 1)
        self.compare_num_t_skipped(gradle10, 22)
        self.compare_bool_t_ran(gradle10, True)
        self.compare_bool_t_failed(gradle10, True)
        self.compare_frameworks(gradle10, 'JUnit')
        self.compare_tr_t_failed(gradle10, 'ThemeManagerTest.installThemeOnScene()')

    def test_gradle_11(self):
        # Compilation failure; no failed tests
        log = '7801445827-orig.log'
        job_id = 7801445827
        file_path = join(self.gradle, log)
        gradle11 = self.dispatcher.analyze(file_path, job_id, build_system='gradle')
        self.compare_status(gradle11, 'broken')
        self.compare_analyzer(gradle11, 'java-gradle')
        self.compare_num_t_run(gradle11, 0)
        self.compare_num_t_ok(gradle11, 'NA')
        self.compare_num_t_failed(gradle11, 0)
        self.compare_num_t_skipped(gradle11, 'NA')
        self.compare_bool_t_ran(gradle11, False)
        self.compare_bool_t_failed(gradle11, False)
        self.compare_frameworks(gradle11, '')
        self.compare_tr_t_failed(gradle11, '')

    def test_ant_0(self):
        log = '2420748513-orig.log'
        job_id = 2420748513
        file_path = join(self.ant, log)
        trigger_sha = '596bf900dc791d77e13fb0aa49a5d73c73e69386'
        repo = 'CACAO2022/CACAO2022'
        ant0 = self.dispatcher.analyze(file_path, job_id,
                                       trigger_sha=trigger_sha, repo=repo)
        self.compare_status(ant0, 'broken')
        self.compare_analyzer(ant0, 'java-ant')
        self.compare_num_t_run(ant0, 1)
        self.compare_num_t_ok(ant0, 0)
        self.compare_num_t_failed(ant0, 1)
        self.compare_num_t_skipped(ant0, 0)
        self.compare_bool_t_ran(ant0, True)
        self.compare_bool_t_failed(ant0, True)
        self.compare_frameworks(ant0, 'JUnit')
        self.compare_tr_t_failed(
            ant0, 'abstraction.FiliereParDefaultTest.testNext')

    def test_ant_1(self):
        log = '2114165124-orig.log'
        job_id = 2114165124
        file_path = join(self.ant, log)
        trigger_sha = 'ea2126bf4ff2565b95b3e319a37e34e5c0d81b7f'
        repo = 'exedio/persistence'
        ant1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(ant1, 'broken')
        self.compare_analyzer(ant1, 'java-ant')
        self.compare_num_t_run(ant1, 2339)
        self.compare_num_t_ok(ant1, 2325)
        self.compare_num_t_failed(ant1, 14)
        self.compare_num_t_skipped(ant1, 3)
        self.compare_bool_t_ran(ant1, True)
        self.compare_bool_t_failed(ant1, True)
        self.compare_frameworks(ant1, 'JUnit')
        self.compare_tr_t_failed(ant1, 'com.exedio.cope.vault.VaultFileServicePropertiesProbeTest.probeGroups#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.putStreamInfo#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.foundGetBytes#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.putStream#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.foundGetLength#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.putMany#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.putPath#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.foundGetStream#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.putBytesInfo#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.putPathInfo#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.putBytes#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.putByPath#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.directoryStructure#'
                                       'com.exedio.cope.vault.VaultFileServicePosixGroupTest.putByStream')

    def test_ant_2(self):
        log = '2496555797-orig.log'
        job_id = 2496555797
        file_path = join(self.ant, log)
        trigger_sha = '68931350487d11510090b267b341bd420c7e7ff9'
        repo = 'exedio/persistence'
        ant2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(ant2, 'broken')
        self.compare_analyzer(ant2, 'java-ant')
        self.compare_num_t_run(ant2, 2429)
        self.compare_num_t_ok(ant2, 2391)
        self.compare_num_t_failed(ant2, 38)
        self.compare_num_t_skipped(ant2, 33)
        self.compare_bool_t_ran(ant2, True)
        self.compare_bool_t_failed(ant2, True)
        self.compare_frameworks(ant2, 'JUnit')
        self.compare_tr_t_failed(ant2, 'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.putStreamInfo#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.foundGetBytes#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.notFoundGetLength#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.putStream#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.notFoundGetStream#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.foundGetLength#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.putMany#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.putPath#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.foundGetStream#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.putBytesInfo#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.notFoundGetBytes#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.putPathInfo#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.putBytes#com.exedio'
                                       '.cope.vault.VaultHttpServiceDirectoryTest.probeGenuineServiceKeyNonEmpty#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.testProbeRootExists#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.notFoundAnonymousLength#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.notFoundAnonymousSink#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.notFoundAnonymousBytes#'
                                       'com.exedio.cope.vault.VaultHttpServiceDirectoryTest.probeGenuineServiceKey#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.putStreamInfo#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.foundGetBytes#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.notFoundGetLength#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.putStream#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.notFoundGetStream#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.foundGetLength#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.putMany#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.putPath#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.foundGetStream#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.putBytesInfo#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.notFoundGetBytes#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.putPathInfo#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.putBytes#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.probeGenuineServiceKeyNonEmpty#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.testProbeRootExists#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.notFoundAnonymousLength#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.notFoundAnonymousSink#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.notFoundAnonymousBytes#'
                                       'com.exedio.cope.vault.VaultHttpServiceFlatTest.probeGenuineServiceKey')

    def test_ant_3(self):
        log = '2464642509-orig.log'
        job_id = 2464642509
        file_path = join(self.ant, log)
        trigger_sha = 'c1565fb89469cbcba67b1cc305e16d520779b270'
        repo = 'java-native-access/jna'
        ant3 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(ant3, 'broken')
        self.compare_analyzer(ant3, 'java-ant')
        self.compare_num_t_run(ant3, 624)
        self.compare_num_t_ok(ant3, 623)
        self.compare_num_t_failed(ant3, 1)
        self.compare_num_t_skipped(ant3, 0)
        self.compare_bool_t_ran(ant3, True)
        self.compare_bool_t_failed(ant3, True)
        self.compare_frameworks(ant3, 'JUnit')
        self.compare_tr_t_failed(ant3, 'com.sun.jna.DirectCallbacksTest.testInvokeCallback')

    def test_build_system_0(self):
        log = '2372881152.log'
        job_id = 2372881152
        file_path = join(self.build_system_testing, log)
        trigger_sha = 'a4797327fc36ce9a1bc151a1e3edfb366e21ce59'
        repo = 'apache/nifi'
        maven0 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_build_system(maven0, 'Maven')

    def test_build_system_1(self):
        log = '2503163025.log'
        job_id = 2503163025
        file_path = join(self.build_system_testing, log)
        trigger_sha = 'fc1402b38584ff8bc61b36f49493ea1e7a9d953a'
        repo = 'JOSM/josm'
        ant0 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_build_system(ant0, 'Ant')

    def test_build_system_2(self):
        log = '2487500667.log'
        job_id = 2487500667
        file_path = join(self.build_system_testing, log)
        trigger_sha = 'c1be62adf5049e79e9c4b3c06845f532260218cb'
        repo = 'vaadin/flow'
        maven1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_build_system(maven1, 'Maven')

    def test_build_system_3(self):
        log = '2029314256.log'
        job_id = 2029314256
        file_path = join(self.build_system_testing, log)
        trigger_sha = '0943d85113e77505f2a1291d7b256b9a4b1e5dec'
        repo = 'apache/beam'
        gradle0 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_build_system(gradle0, 'Gradle')

    def test_build_system_4(self):
        log = '2040687460.log'
        job_id = 2040687460
        file_path = join(self.build_system_testing, log)
        trigger_sha = 'fab01311843386e4106af61a46c9e0dbf8380b5f'
        repo = 'open-telemetry/opentelemetry-java'
        gradle1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_build_system(gradle1, 'Gradle')

    def test_build_system_5(self):
        log = '2464642509-orig.log'
        job_id = 2464642509
        file_path = join(self.ant, log)
        trigger_sha = 'c1565fb89469cbcba67b1cc305e16d520779b270'
        repo = 'java-native-access/jna'
        ant1 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_build_system(ant1, 'Ant')

    def test_build_system_6(self):
        log = '2238223005.log'
        job_id = 2238223005
        file_path = join(self.build_system_testing, log)
        trigger_sha = '59a227b87175a32b115a8c05e3427668f1fa5bbb'
        repo = 'komoot/photon'
        maven2 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_build_system(maven2, 'Maven')

    def test_build_system_7(self):
        # Test Gradle without tigger sha
        log = '6999501459.log'
        job_id = 6999501459
        file_path = join(self.build_system_testing, log)
        repo = 'itsaky/AndroidIDE'
        gradle2 = self.dispatcher.analyze(file_path, job_id, repo=repo)
        self.compare_build_system(gradle2, 'Gradle')

    def test_build_system_8(self):
        # Test Maven without tigger sha
        log = '6642948886.log'
        job_id = 6642948886
        file_path = join(self.build_system_testing, log)
        repo = 'eclipse-che/che-server'
        maven3 = self.dispatcher.analyze(file_path, job_id, repo=repo)
        self.compare_build_system(maven3, 'Maven')

    def test_build_system_9(self):
        # Test Ant without tigger sha
        log = '6991832152.log'
        job_id = 6991832152
        file_path = join(self.build_system_testing, log)
        repo = 'mwgh/ob-pos'
        ant2 = self.dispatcher.analyze(file_path, job_id, repo=repo)
        self.compare_build_system(ant2, 'Ant')

    def test_other_analyzer_0(self):
        log = '2404934395.log'
        job_id = 2404934395
        file_path = join(self.other, log)
        trigger_sha = '23acc8ea2714a4250b517de56441a872be16859e'
        repo = 'sbt/sbt-jupiter-interface'
        oa0 = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_analyzer(oa0, 'java-other')
        self.compare_build_system(oa0, 'NA')
        self.compare_bool_t_ran(oa0, True)
        self.compare_num_t_run(oa0, 216)
        self.compare_num_t_ok(oa0, 214)
        self.compare_num_t_failed(oa0, 2)
        self.compare_num_t_skipped(oa0, 6)
        self.compare_t_duration(oa0, 176.0)
        self.compare_tr_t_failed(oa0, 'basic.FooTest.failingTest#basic.FooTest.failingTest')

    def test_javascript_analyzer_0(self):
        # HabitRPG/habitica
        log = '2536167204.log'
        job_id = 2536167204
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 635)
        self.compare_num_t_ok(jsa, 634)
        self.compare_num_t_skipped(jsa, 5)
        self.compare_num_t_failed(jsa, 1)
        self.compare_t_duration(jsa, 3.0)
        self.compare_frameworks(jsa, 'mocha')
        self.compare_tr_t_failed(jsa, 'shared.ops.scoreTask scores does not modify stats when task need approval:')

    def test_javascript_analyzer_1(self):
        # handshake-org/hsd
        log = '2536837535.log'
        job_id = 2536837535
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 2188)
        self.compare_num_t_ok(jsa, 2186)
        self.compare_num_t_skipped(jsa, 5)
        self.compare_num_t_failed(jsa, 2)
        self.compare_t_duration(jsa, 112.0)
        self.compare_frameworks(jsa, 'mocha')
        self.compare_tr_t_failed(jsa, 'Lookup should lookup seed:#Lookup should fail resolve:')

    def test_javascript_analyzer_2(self):
        # motdotla/node-lambda, should pass without error
        log = '2536803026.log'
        job_id = 2536803026
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'ok')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 161)
        self.compare_num_t_ok(jsa, 161)
        self.compare_num_t_failed(jsa, 0)
        self.compare_t_duration(jsa, 180.0)
        self.compare_frameworks(jsa, 'mocha')
        self.compare_tr_t_failed(jsa, '')

    def test_javascript_analyzer_3(self):
        # sequelize/sequelize, has [], () {} in failed tests
        log = '2536680158.log'
        job_id = 2536680158
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 1640)
        self.compare_num_t_ok(jsa, 1639)
        self.compare_num_t_skipped(jsa, 2)
        self.compare_num_t_failed(jsa, 1)
        self.compare_t_duration(jsa, 180.0)
        self.compare_frameworks(jsa, 'mocha')
        self.compare_tr_t_failed(jsa, '[DB2] CLS (Async hooks) Model Hook integration passes the transaction to hooks '
                                      '{beforeUpsert,afterUpsert} when calling Model.upsert:')

    def test_javascript_analyzer_4(self):
        # Binaryify/NeteaseCloudMusicApi, failed tests are not in English
        log = '2404484958.log'
        job_id = 2404484958
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 9)
        self.compare_num_t_ok(jsa, 7)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_num_t_failed(jsa, 2)
        self.compare_t_duration(jsa, 9.0)
        self.compare_frameworks(jsa, 'mocha')
        self.compare_tr_t_failed(jsa, '测试登录是否正常 手机登录 code 应该等于200:#'
                                      '测试获取歌曲是否正常 歌曲的 url 不应该为空:')

    def test_javascript_analyzer_5(self):
        # senecajs/seneca, has problems with dependencies
        log = '2530886594.log'
        job_id = 2530886594
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, False)
        self.compare_num_t_run(jsa, 0)
        self.compare_num_t_ok(jsa, 'NA')
        self.compare_num_t_skipped(jsa, 'NA')
        self.compare_num_t_failed(jsa, 0)
        self.compare_frameworks(jsa, '')
        self.compare_tr_t_failed(jsa, '')

    def test_javascript_analyzer_6(self):
        # Retries multiple times due to tests failure
        # Need to set repo and trigger_sha because it contains setup python action
        log = '2284801118.log'
        job_id = 2284801118
        file_path = join(self.javascript_mocha, log)
        trigger_sha = '2fbc602704255d482f415722964a1f1a9d7e10cb'
        repo = 'nodegit/nodegit'
        jsa = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 1696)
        self.compare_num_t_ok(jsa, 1688)
        self.compare_num_t_skipped(jsa, 28)
        self.compare_num_t_failed(jsa, 8)
        self.compare_t_duration(jsa, 240.0)
        self.compare_frameworks(jsa, 'mocha')
        # We have '#' in our failed test name, this can cause problem.
        self.compare_tr_t_failed(jsa, 'Worker can kill worker thread while in use #0:#"after each" hook:#'
                                      'Worker can kill worker thread while in use #0:#"after each" hook:#'
                                      'Worker can kill worker thread while in use #0:#"after each" hook:#'
                                      'Worker can kill worker thread while in use #0:#"after each" hook:')

    def test_javascript_analyzer_7(self):
        # hyperledger/fabric-sdk-node, passes multiple mocha tests.
        log = '2538931529.log'
        job_id = 2538931529
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'ok')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 1631)
        self.compare_num_t_ok(jsa, 1631)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_num_t_failed(jsa, 0)
        self.compare_t_duration(jsa, 17.982)
        self.compare_frameworks(jsa, 'mocha')

    def test_javascript_analyzer_8(self):
        # ain/smartbanner.js, 4 lines failed test.
        log = '2358392288.log'
        job_id = 2358392288
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 131)
        self.compare_num_t_ok(jsa, 130)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_num_t_failed(jsa, 1)
        self.compare_t_duration(jsa, 3)
        self.compare_frameworks(jsa, 'mocha')
        self.compare_tr_t_failed(jsa, 'Detector marginedElement with jQuery Mobile "before all" hook for "expected to '
                                      'return ui-page element as first item of array":')

    def test_javascript_analyzer_9(self):
        # depcheck/depcheck, contains large amount of failure
        log = '2464267101.log'
        job_id = 2464267101
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 728)
        self.compare_num_t_ok(jsa, 455)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_num_t_failed(jsa, 273)
        self.compare_t_duration(jsa, 3.0)
        self.compare_frameworks(jsa, 'mocha')

    def test_javascript_analyzer_10(self):
        # shipshapecode/shepherd
        log = '2518112250.log'
        job_id = 2518112250
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 129)
        self.compare_num_t_ok(jsa, 124)
        self.compare_num_t_failed(jsa, 5)
        self.compare_num_t_skipped(jsa, 2)
        self.compare_t_duration(jsa, 10.831)
        self.compare_frameworks(jsa, 'jest')
        self.compare_tr_t_failed(jsa, 'components/ShepherdModal › positionModal() › sets the correct attributes when '
                                      'positioning modal opening#components/ShepherdModal › positionModal() › sets the '
                                      'correct attributes with padding#components/ShepherdModal › positionModal() › '
                                      'sets the correct attributes when positioning modal opening with border radius#'
                                      'components/ShepherdModal › positionModal() › sets the correct attributes when '
                                      'target is overflowing from scroll parent#components/ShepherdModal › position'
                                      'Modal() › sets the correct attributes when target fits inside scroll parent')

    def test_javascript_analyzer_11(self):
        # ipfs/ipfs-webui tests run without any issue
        log = '2456175610.log'
        job_id = 2456175610
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'ok')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 59)
        self.compare_num_t_ok(jsa, 59)
        self.compare_num_t_failed(jsa, 0)
        self.compare_num_t_skipped(jsa, 4)
        self.compare_t_duration(jsa, 9.09)
        self.compare_frameworks(jsa, 'jest')

    def test_javascript_analyzer_12(self):
        # svg/svgo
        log = '2320994299.log'
        job_id = 2320994299
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 432)
        self.compare_num_t_ok(jsa, 431)
        self.compare_num_t_failed(jsa, 1)
        self.compare_num_t_skipped(jsa, 3)
        self.compare_frameworks(jsa, 'jest')
        self.compare_tr_t_failed(jsa, 'output as stream when "-" is specified')

    def test_javascript_analyzer_13(self):
        # LuanRT/YouTube.js failed all test cases
        log = '2545414624.log'
        job_id = 2545414624
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 14)
        self.compare_num_t_ok(jsa, 0)
        self.compare_num_t_failed(jsa, 14)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_t_duration(jsa, 1.791)
        self.compare_frameworks(jsa, 'jest')
        self.compare_tr_t_failed(jsa, 'YouTube.js Tests › Search › Should search on YouTube#'
                                      'YouTube.js Tests › Search › Should retrieve YouTube search suggestions#'
                                      'YouTube.js Tests › Search › Should retrieve YouTube Music search suggestions#'
                                      'YouTube.js Tests › Comments › Should retrieve comments#'
                                      'YouTube.js Tests › Comments › Should retrieve comment thread continuation#'
                                      'YouTube.js Tests › Comments › Should retrieve comment replies#'
                                      'YouTube.js Tests › Playlists › Should retrieve playlist with YouTube#'
                                      'YouTube.js Tests › Playlists › Should retrieve playlist with YouTube Music#'
                                      'YouTube.js Tests › General › Should retrieve home feed#'
                                      'YouTube.js Tests › General › Should retrieve trending content#'
                                      'YouTube.js Tests › General › Should retrieve video info#'
                                      'YouTube.js Tests › General › Should download video#'
                                      'YouTube.js Tests › Deciphers › Should decipher signature#'
                                      'YouTube.js Tests › Deciphers › Should decipher ntoken')

    def test_javascript_analyzer_14(self):
        # lerna/lerna
        log = '2537485009.log'
        job_id = 2537485009
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 60)
        self.compare_num_t_ok(jsa, 55)
        self.compare_num_t_failed(jsa, 5)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_t_duration(jsa, 290.666)
        self.compare_frameworks(jsa, 'jest')
        self.compare_tr_t_failed(jsa, 'lerna changed › with a change to package-c since the last release › --json › '
                                      'should list package-a and package-c as changed in json format#'
                                      'lerna changed › with a change to package-c since the last release › --ndjson › '
                                      'should list package-a and package-c as changed in newline-delimited json format#'
                                      'lerna changed › with a change to package-c since the last release › --parseable '
                                      '› should list package-a and package-c as changed with parseable output instead '
                                      'of columnified view#lerna changed › with a change to package-c since the last '
                                      'release › -p › should list package-a and package-c as changed with parseable '
                                      'output instead of columnified view#lerna changed › with a change to package-c '
                                      'since the last release › -pla › should list package-a, package-b, and package-c '
                                      'as changed, with version and package info, in a parseable output')

    def test_javascript_analyzer_15(self):
        # apify/apify-js, multiple failed test suites
        log = '2549045719.log'
        job_id = 2549045719
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 608)
        self.compare_num_t_ok(jsa, 558)
        self.compare_num_t_failed(jsa, 50)
        self.compare_num_t_skipped(jsa, 3)
        self.compare_t_duration(jsa, 130.763)
        self.compare_frameworks(jsa, 'jest')

    def test_javascript_analyzer_16(self):
        # asyncapi/generator, failed to start test
        log = '2547772887.log'
        job_id = 2547772887
        file_path = join(self.javascript_jest, log)
        trigger_sha = '2fbc602704255d482f415722964a1f1a9d7e10cb'
        repo = 'asyncapi/generator'
        jsa = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, False)
        self.compare_num_t_run(jsa, 0)
        self.compare_num_t_ok(jsa, 'NA')
        self.compare_num_t_failed(jsa, 0)
        self.compare_num_t_skipped(jsa, 'NA')
        self.compare_frameworks(jsa, 'jest')
        self.compare_tr_t_failed(jsa, '')

    def test_javascript_analyzer_17(self):
        # vercel/ncc, has output looks like failure but no failed test
        log = '2543299414.log'
        job_id = 2543299414
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'ok')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 118)
        self.compare_num_t_ok(jsa, 118)
        self.compare_num_t_failed(jsa, 0)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_t_duration(jsa, 395.524)
        self.compare_frameworks(jsa, 'jest')
        self.compare_tr_t_failed(jsa, '')

    def test_javascript_analyzer_18(self):
        # tj/commander.js, build failed due to other commands, passed all tests.
        log = '2541668703.log'
        job_id = 2541668703
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 1048)
        self.compare_num_t_ok(jsa, 1048)
        self.compare_num_t_failed(jsa, 0)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_t_duration(jsa, 15.294)
        self.compare_frameworks(jsa, 'jest')
        self.compare_tr_t_failed(jsa, '')

    def test_javascript_analyzer_19(self):
        # FormidableLabs/victory, 2 jest tests
        log = '2544418976.log'
        job_id = 2544418976
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 916)
        self.compare_num_t_ok(jsa, 915)
        self.compare_num_t_failed(jsa, 1)
        self.compare_num_t_skipped(jsa, 7)
        self.compare_t_duration(jsa, 36.525)
        self.compare_frameworks(jsa, 'jest')
        self.compare_tr_t_failed(jsa, 'victory-core › should export everything')

    def test_javascript_analyzer_20(self):
        # kiwicom/orbit, contains jest errors
        log = '357124468.log'
        job_id = 357124468
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 566)
        self.compare_num_t_ok(jsa, 563)
        self.compare_num_t_failed(jsa, 3)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_t_duration(jsa, 203.712)
        self.compare_frameworks(jsa, 'jest')
        self.compare_tr_t_failed(jsa, 'Test suite failed to run#ComponentStructure › should have expected DOM#'
                                      'ComponentStructure › should move focus along tabs when pressing arrow keys#'
                                      "ComponentStructure › should not have tabs if there's only one platform")

    def test_javascript_21(self):
        # marko-js/marko, contains failing as expected test
        log = '2230809902.log'
        job_id = 2230809902
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'ok')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 2610)
        self.compare_num_t_ok(jsa, 2610)
        self.compare_num_t_failed(jsa, 0)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_t_duration(jsa, 120.0)
        self.compare_frameworks(jsa, 'mocha')

    def test_javascript_22(self):
        # dherault/serverless-offline, no error
        log = '2406840580.log'
        job_id = 2406840580
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'ok')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 72)
        self.compare_num_t_ok(jsa, 72)
        self.compare_num_t_failed(jsa, 0)
        self.compare_num_t_skipped(jsa, 39)
        self.compare_t_duration(jsa, 180.0)
        self.compare_frameworks(jsa, 'mocha')

    def test_javascript_23(self):
        # nchaulet/node-geocoder, no error
        log = '2525375274.log'
        job_id = 2525375274
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'ok')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 218)
        self.compare_num_t_ok(jsa, 218)
        self.compare_num_t_failed(jsa, 0)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_t_duration(jsa, 3.257)
        self.compare_frameworks(jsa, 'jest')

    def test_javascript_24(self):
        # getgauge/taiko, no error
        log = '2506840513.log'
        job_id = 2506840513
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'ok')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 1141)
        self.compare_num_t_ok(jsa, 1141)
        self.compare_num_t_failed(jsa, 0)
        self.compare_num_t_skipped(jsa, 18)
        self.compare_t_duration(jsa, 48.0)
        self.compare_frameworks(jsa, 'mocha')

    def test_javascript_25(self):
        # siimon/prom-client, no error
        log = '2499439457.log'
        job_id = 2499439457
        file_path = join(self.javascript_jest, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'ok')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, False)
        self.compare_num_t_run(jsa, 230)
        self.compare_num_t_ok(jsa, 230)
        self.compare_num_t_failed(jsa, 0)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_t_duration(jsa, 3.47)
        self.compare_frameworks(jsa, 'jest')

    def test_javascript_26(self):
        # cmake-js/cmake-js, ubuntu 22.04
        log = '2446999494.log'
        job_id = 2446999494
        file_path = join(self.javascript_mocha, log)
        jsa = self.dispatcher.analyze(file_path, job_id)
        self.compare_status(jsa, 'broken')
        self.compare_bool_t_ran(jsa, True)
        self.compare_bool_t_failed(jsa, True)
        self.compare_num_t_run(jsa, 38)
        self.compare_num_t_ok(jsa, 7)
        self.compare_num_t_failed(jsa, 31)
        self.compare_num_t_skipped(jsa, 0)
        self.compare_t_duration(jsa, 10)
        self.compare_frameworks(jsa, 'mocha')
        self.assertEqual(len(jsa['tr_log_tests_failed'].split('#')), 31)

    def test_result_comparer_1(self):
        job_id = 2320033275
        o_path = join(self.result_comparer, '{}-orig.log'.format(job_id))
        r_path = join(self.result_comparer, '{}-repr.log'.format(job_id))
        trigger_sha = 'ad9c8d5d3e85e532577ce6d0a686f452c48f0694'
        repo = 'alibaba/fastjson2'
        build_system = 'maven'
        rc1 = self.analyzer.compare_single_log(
            r_path,
            o_path,
            job_id,
            'github',
            build_system,
            trigger_sha,
            repo,
        )
        self.compare_rc_match(rc1, True)

    def test_result_comparer_2(self):
        job_id = 1749803252
        o_path = join(self.result_comparer, '{}-orig.log'.format(job_id))
        r_path = join(self.result_comparer, '{}-repr.log'.format(job_id))
        trigger_sha = '7c8d22c973fcdc9443a4e22d8cd72ffeb8913db2'
        repo = 'raphw/byte-buddy'
        rc2 = self.analyzer.compare_single_log(r_path, o_path, job_id, 'github', trigger_sha=trigger_sha, repo=repo)
        self.compare_rc_match(rc2, True)

    def test_result_comparer_3(self):
        # Unreproducible because its dependencies are gone.
        job_id = 2003301608
        o_path = join(self.result_comparer, '{}-orig.log'.format(job_id))
        r_path = join(self.result_comparer, '{}-repr.log'.format(job_id))
        trigger_sha = 'e3564d66768a87ff4ce643fa4c6f720516057b33'
        repo = 'codecentric/spring-boot-admin'
        rc3 = self.analyzer.compare_single_log(r_path, o_path, job_id, 'github', trigger_sha=trigger_sha, repo=repo)
        self.compare_rc_mismatch('tr_log_frameworks', rc3, '', 'JUnit')
        self.compare_rc_mismatch('tr_log_bool_tests_ran', rc3, False, True)
        self.compare_rc_mismatch('tr_log_bool_tests_failed', rc3, False, True)
        self.compare_rc_mismatch('tr_log_num_tests_run', rc3, 0, 505)
        self.compare_rc_mismatch('tr_log_num_tests_ok', rc3, 'NA', 504)
        self.compare_rc_mismatch('tr_log_num_tests_failed', rc3, 0, 1)
        self.compare_rc_mismatch('tr_log_num_tests_skipped', rc3, 'NA', 0)
        self.compare_rc_mismatch('tr_log_tests_failed', rc3, [],
                                 ['lifecycle(de.codecentric.boot.admin.server.cloud.AdminApplicationDiscoveryTest)'])

    def test_could_not_resolve_dep_1(self):
        log = 'ac73df56a593752d8d5741b3a1fc0e0bc4836d9d.log'
        job_id = 2540654452
        file_path = join(self.logs, log)
        trigger_sha = 'ac73df56a593752d8d5741b3a1fc0e0bc4836d9d'
        repo = 'dianping/cat'
        maven = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven, 'broken')
        self.compare_analyzer(maven, 'java-maven')
        self.compare_dep_error(maven, '#19 22.32 [ERROR] Failed to execute goal on project cat-core: Could not resolve '
                                      'dependencies for project com.dianping.cat:cat-core:jar:3.1.0: Failed to collect '
                                      'dependencies at org.unidal.framework:foundation-service:jar:3.0.2: Failed to rea'
                                      'd artifact descriptor for org.unidal.framework:foundation-service:jar:3.0.2: Cou'
                                      'ld not transfer artifact org.unidal.framework:foundation-service:pom:3.0.2 from/'
                                      'to maven-default-http-blocker (http://0.0.0.0/): Blocked mirror for repositories'
                                      ': [unidal.releases (http://unidal.org/nexus/content/repositories/releases/, defa'
                                      'ult, releases+snapshots)] -> [Help 1]')

    def test_could_not_resolve_dep_2(self):
        log = 'd1e03606f3d7514e165e12d398a63167f67b5e2e.log'
        job_id = 2557122144
        file_path = join(self.logs, log)
        trigger_sha = 'd1e03606f3d7514e165e12d398a63167f67b5e2e'
        repo = 'apache/maven'
        maven = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_status(maven, 'broken')
        self.compare_analyzer(maven, 'java-maven')
        self.compare_dep_error(maven,
                               'org.apache.maven.cli.internal.ExtensionResolutionException: Extension org.apache.maven'
                               '.extensions:maven-build-cache-extension:1.0.0-SNAPSHOT or one of its dependencies coul'
                               'd not be resolved: Could not find artifact org.apache.maven.extensions:maven-build-cac'
                               'he-extension:jar:1.0.0-SNAPSHOT')

    def test_setup_time_1(self):
        log = 'db7aede5e68772486617dfe573ddd2306be927dc.log'
        job_id = 7024441027
        file_path = join(self.logs, log)
        trigger_sha = 'db7aede5e68772486617dfe573ddd2306be927dc'
        repo = 'raphw/byte-buddy'
        maven = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_setup_time(maven, 9.61)
        self.compare_buildduration(maven, 162)

    def test_setup_time_2(self):
        # Java repo, Python CI
        log = '6d2edd6284ebc5301dbe45376a31ca8316852a77.log'
        job_id = 7312000006
        trigger_sha = '6d2edd6284ebc5301dbe45376a31ca8316852a77'
        repo = 'apache/iceberg'
        file_path = join(self.logs, log)
        python = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_setup_time(python, 4.47)

    def test_setup_time_3(self):
        log = '2bc1838f764bbcee383326ab76c82fa3dbf7c441.log'
        job_id = 2663820155
        trigger_sha = '2bc1838f764bbcee383326ab76c82fa3dbf7c441'
        repo = 'itsaky/AndroidIDE'
        file_path = join(self.logs, log)
        gradle = self.dispatcher.analyze(file_path, job_id, trigger_sha=trigger_sha, repo=repo)
        self.compare_setup_time(gradle, 24.91)
        self.compare_buildduration(gradle, 509)


if __name__ == '__main__':
    unittest.main()
