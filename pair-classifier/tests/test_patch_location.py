"""
test_patch_location.py with test for errors
This checks for the classification of the diff files by CODE, BUILD, or TEST
and compares with the manual classification.
The classification options are YES, NO, or PARTIAL
Lists are given in the order of CODE, BUILD, TEST respectively
"""
import unittest
import sys

from os import listdir
from os.path import join

sys.path.append('../')
from pair_classifier.classify_bugs import process_logs  # noqa: E402
from pair_classifier.classify_bugs import process_error  # noqa: E402
from pair_classifier.classify_bugs import detect_lang  # noqa: E402
from pair_classifier.classify_bugs import is_code  # noqa: E402
from pair_classifier.classify_bugs import is_dependency as is_build  # noqa: E402
from pair_classifier.classify_bugs import is_test  # noqa: E402


class Test(unittest.TestCase):

    def check_diff(self, files_changed):
        conf_test = 0
        conf_build = 0
        conf_code = 0
        # tests if the diff occurs in TEST
        conf_test, _, remaining_files = is_test(files_changed)
        # tests if the diff occurs in BUILD
        conf_build, _, remaining_files = is_build(remaining_files, files_changed)
        # tests if the diff occurs in CODE
        conf_code, _, _ = is_code(remaining_files, files_changed)

        return conf_code, conf_build, conf_test

    def classify_diff_location(self, conf_code, conf_build, conf_test):
        conf = [conf_code, conf_build, conf_test]
        testcase_results = [None, None, None]
        for status in range(len(testcase_results)):
            if conf[status] == 0 or conf[status] is None:
                testcase_results[status] = 'No'
            elif conf[status] < 1:
                testcase_results[status] = 'Partial'
            elif conf[status] == 1:
                testcase_results[status] = 'Yes'

        return testcase_results

    def test_patch_location_1(self):  # raphw-byte-buddy-95795967
        image_tag = 'raphw-byte-buddy-95795967'
        manual_results = ['Partial', 'No', 'Partial']
        files_changed = ['byte-buddy-dep/src/main/java/net/bytebuddy/dynamic/ClassFileLocator.java',
                         'byte-buddy-dep/src/test/java/net/bytebuddy/dynamic/ClassFileLocatorAgentBasedTest.java']
        tag_language = 'java'
        build_error = {'NullPointerException': 1}

        files = ['95795967-orig.log', '95797603-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_2(self):  # apache-struts-147673952
        image_tag = 'apache-struts-147673952'
        manual_results = ['Partial', 'Partial', 'No']
        files_changed = ['core/src/main/java/org/apache/struts2/dispatcher/mapper/DefaultActionMapper.java',
                         'plugins/jfreechart/pom.xml']
        tag_language = 'java'
        build_error = {'IIOException': 1}
        files = ['147673952-orig.log', '147677822-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_3(self):  # stagemonitor-stagemonitor-131427161
        image_tag = 'stagemonitor-stagemonitor-131427161'
        manual_results = ['No', 'No', 'Yes']
        files_changed = [
            'stagemonitor/stagemonitor-jdbc/src/test/java/org/stagemonitor/jdbc/ConnectionMonitoringTransformerTest.'
            'java']
        tag_language = 'java'
        files = ['131427161-orig.log', '131433669-orig.log', 'cloc.csv', 'diff.txt']
        build_error = {'NullPointerException': 1, 'AssertionError': 1}

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_4(self):  # ImmobilienScout24-deadcode4j-108400124
        image_tag = 'ImmobilienScout24-deadcode4j-108400124'
        manual_results = ['No', 'No', 'Yes']
        files_changed = ['src/test/java/de/is24/deadcode4j/plugin/IT_PuttingItAllTogether.java']
        tag_language = 'java'
        build_error = {'ArgumentsAreDifferent': 1}
        files = ['108400124-orig.log', '108470682-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_5(self):  # openpnp-openpnp-213669200
        image_tag = 'openpnp-openpnp-213669200'
        manual_results = ['Yes', 'No', 'No']
        files_changed = ['src/main/java/org/openpnp/util/OpenCvUtils.java']
        tag_language = 'java'
        build_error = {'NullPointerException': 1}
        files = ['213669200-orig.log', '213670270-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    # Adobe-Consulting-Services-acs-aem-commons-358605962
    def test_patch_location_6(self):
        image_tag = 'Adobe-Consulting-Services-acs-aem-commons-358605962'
        manual_results = ['Partial', 'No', 'Partial']
        files_changed = ['bundle/src/main/java/com/adobe/acs/commons/mcp/impl/processes/asset/AssetIngestor.java',
                         'bundle/src/test/java/com/adobe/acs/commons/mcp/impl/processes/asset/FileAssetIngestorTest.'
                         'java',
                         'bundle/src/test/java/com/adobe/acs/commons/mcp/impl/processes/asset/S3AssetIngestorTest.java']
        tag_language = 'java'
        build_error = {'AssertionError': 7}
        files = ['358605962-orig.log', '358617230-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_7(self):  # SonarSource-sonar-java-342232104
        image_tag = 'SonarSource-sonar-java-342232104'
        manual_results = ['No', 'No', 'Yes']
        files_changed = [
            'java-checks/src/test/java/org/sonar/java/checks/UndocumentedApiCheckTest.java']
        tag_language = 'java'
        build_error = {'AssertionError': 1}
        files = ['342232104-orig.log', '342241550-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_8(self):  # SonarSource-sonar-java-382099987
        image_tag = 'SonarSource-sonar-java-382099987'
        manual_results = ['Partial', 'Partial', 'Partial']
        files_changed = ['java-checks/pom.xml',
                         'java-checks/src/main/java/org/sonar/java/checks/CheckList.java',
                         'java-checks/src/main/java/org/sonar/java/checks/SecureCookieCheck.java',
                         'java-checks/src/main/java/org/sonar/java/checks/security/CookieHttpOnlyCheck.java',
                         'java-checks/src/main/java/org/sonar/java/checks/security/InstanceShouldBeInitializedCorrectly'
                         'Base.java',
                         'java-checks/src/test/files/checks/SecureCookieCheck.java',
                         'java-checks/src/test/files/checks/security/CookieHttpOnlyCheck.java']
        tag_language = 'java'
        build_error = {}
        files = ['382099987-orig.log', '382244235-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_9(self):  # ikasanEIP-ikasan-372813694
        image_tag = 'ikasanEIP-ikasan-372813694'
        manual_results = ['No', 'No', 'Yes']
        files_changed = ['ikasaneip/test/src/main/java/org/ikasan/testharness/flow/rule/IkasanFlowTestRule.java',
                         'ikasaneip/test/src/main/java/org/ikasan/testharness/flow/rule/IkasanStandaloneFlowTestRule.'
                         'java']
        tag_language = 'java'
        build_error = {}
        files = ['372813694-orig.log', '372980908-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_10(self):  # SonarSource-sonar-java-382054648
        image_tag = 'SonarSource-sonar-java-382054648'
        manual_results = ['Partial', 'No', 'Partial']
        files_changed = ['its/ruling/src/test/resources/commons-beanutils/squid-S1125.json',
                         'its/ruling/src/test/resources/guava/squid-S1125.json',
                         'its/ruling/src/test/resources/jdk6/squid-S1125.json',
                         'java-checks/src/main/java/org/sonar/java/checks/BooleanLiteralCheck.java',
                         'java-checks/src/main/java/org/sonar/java/checks/security/SecureXmlTransformerCheck.java',
                         'java-checks/src/test/files/checks/BooleanEqualityComparisonCheck.java',
                         'java-checks/src/test/java/org/sonar/java/checks/security/SecureXmlTransformerCheckTest.java']
        tag_language = 'java'
        build_error = {}
        files = ['382054648-orig.log', '382057459-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_11(self):  # SonarSource-sonar-java-414054533
        image_tag = 'SonarSource-sonar-java-414054533'
        manual_results = ['Partial', 'Partial', 'Partial']
        files_changed = ['java-checks/src/main/java/org/sonar/java/checks/CheckList.java',
                         'java-checks/src/main/java/org/sonar/java/checks/ReuseRandomCheck.java',
                         'java-checks/src/main/resources/org/sonar/l10n/java/rules/squid/S2119_java.html',
                         'java-checks/src/main/resources/org/sonar/l10n/java/rules/squid/S2119_java.json',
                         'java-checks/src/main/resources/org/sonar/l10n/java/rules/squid/Sonar_way_profile.json',
                         'java-checks/src/test/files/checks/ReuseRandomCheck.java',
                         'java-checks/src/test/java/org/sonar/java/checks/ReuseRandomCheckTest.java',
                         'sonar-java-plugin/pom.xml']
        tag_language = 'java'
        build_error = {}
        files = ['414054533-orig.log', '414066731-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    # Adobe-Consulting-Services-acs-aem-commons-439308121
    def test_patch_location_12(self):
        image_tag = 'Adobe-Consulting-Services-acs-aem-commons-439308121'
        manual_results = ['Yes', 'No', 'No']
        files_changed = ['bundle/src/main/java/com/adobe/acs/commons/functions/CheckedBiConsumer.java',
                         'bundle/src/main/java/com/adobe/acs/commons/functions/CheckedBiFunction.java',
                         'bundle/src/main/java/com/adobe/acs/commons/functions/CheckedConsumer.java',
                         'bundle/src/main/java/com/adobe/acs/commons/functions/CheckedFunction.java',
                         'bundle/src/main/java/com/adobe/acs/commons/mcp/impl/processes/BrokenLinksReport.java']
        tag_language = 'java'
        build_error = {'AssertionError': 1}
        files = ['439308121-orig.log', '439320201-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    # Adobe-Consulting-Services-acs-aem-commons-461233051
    def test_patch_location_13(self):
        image_tag = 'Adobe-Consulting-Services-acs-aem-commons-461233051'
        manual_results = ['No', 'No', 'Yes']
        files_changed = ['bundle/src/test/java/com/adobe/acs/commons/mcp/form/SyntheticDialogTest.java']
        tag_language = 'java'
        build_error = {'AssertionError': 1}
        files = ['461233051-orig.log', '461321229-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    # Adobe-Consulting-Services-acs-aem-commons-459953339
    def test_patch_location_14(self):
        image_tag = 'Adobe-Consulting-Services-acs-aem-commons-459953339'
        manual_results = ['No', 'No', 'Yes']
        files_changed = ['bundle/src/test/java/com/adobe/acs/commons/data/SpreadsheetTest.java']
        tag_language = 'java'
        build_error = {'AssertionError': 1}
        files = ['459953339-orig.log', '459988583-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    # Adobe-Consulting-Services-acs-aem-commons-456539772
    def test_patch_location_15(self):
        image_tag = 'Adobe-Consulting-Services-acs-aem-commons-456539772'
        manual_results = ['Partial', 'No', 'Partial']
        files_changed = ['bundle/src/main/java/com/adobe/acs/commons/wcm/impl/ComponentErrorHandlerImpl.java',
                         'bundle/src/test/java/com/adobe/acs/commons/util/RunnableOnMasterTest.java',
                         'bundle/src/test/java/com/adobe/acs/commons/wcm/impl/ComponentErrorHandlerImplTest.java']
        tag_language = 'java'
        build_error = {'ServletException': 1, 'AssertionError': 2}
        files = ['456539772-orig.log', '456556287-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    # UNC-Libraries-Carolina-Digital-Repository-396988274
    def test_patch_location_16(self):
        image_tag = 'UNC-Libraries-Carolina-Digital-Repository-396988274'
        manual_results = ['Partial', 'No', 'Partial']
        files_changed = ['fcrepo-clients/src/main/java/edu/unc/lib/dl/fcrepo4/RepositoryObjectCacheLoader.java',
                         'fcrepo-clients/src/main/java/edu/unc/lib/dl/fcrepo4/RepositoryObjectLoader.java',
                         'fcrepo-clients/src/test/java/edu/unc/lib/dl/fcrepo4/TransactionalFcrepoClientTest.java',
                         'metadata/src/main/java/edu/unc/lib/dl/rdf/Cdr.java',
                         'persistence/src/main/java/edu/unc/lib/dl/persist/services/destroy/DestroyObjectsJob.java',
                         'persistence/src/main/java/edu/unc/lib/dl/persist/services/destroy/DestroyObjectsService.java',
                         'persistence/src/main/java/edu/unc/lib/dl/util/TombstonePropertySelector.java',
                         'persistence/src/test/java/edu/unc/lib/dl/persist/services/destroy/DestroyObjectsJobIT.java']
        tag_language = 'java'
        build_error = {'NullPointerException': 1}
        files = ['396988274-orig.log', '397470308-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_17(self):  # brettwooldridge-HikariCP-446093148
        image_tag = 'brettwooldridge-HikariCP-446093148'
        manual_results = ['Yes', 'No', 'No']
        files_changed = ['src/main/java/com/zaxxer/hikari/metrics/prometheus/PrometheusHistogramMetricsTracker.java']
        tag_language = 'java'
        build_error = {'NullPointerException': 1,
                       'AbstractMethodError': 1, 'Error': 1}
        files = ['446093148-orig.log', '446257230-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)

    def test_patch_location_18(self):  # raphw-byte-buddy-156672808
        image_tag = 'raphw-byte-buddy-156672808'
        manual_results = ['No', 'No', 'Yes']
        files_changed = [
            'raphw/byte-buddy/byte-buddy-gradle-plugin/src/test/java/net/bytebuddy/build/gradle/ByteBuddyPluginTest.'
            'java']
        tag_language = 'java'
        build_error = {'AssertionError': 1}
        files = ['156672808-orig.log', '156673404-orig.log', 'cloc.csv', 'diff.txt']

        # check the diffs for CODE, BUILD, TEST
        conf_code, conf_build, conf_test = self.check_diff(files_changed)
        # get classification for this test
        testcase_results = self.classify_diff_location(conf_code, conf_build, conf_test)

        artifacts_folder = 'artifacts/'
        for found_tag in listdir(artifacts_folder):
            if found_tag == image_tag:
                file_path = join(artifacts_folder, found_tag)
                failed_log = process_logs(file_path, files)
                error, build_lang = detect_lang(failed_log, quiet=1)
                error_dict, userdefined, confidence = process_error(build_lang.get('language', None), failed_log)
                break

        self.assertEqual(tag_language, build_lang['language'])
        self.assertEqual(build_error, error_dict)
        self.assertListEqual(manual_results, testcase_results)


if __name__ == '__main__':
    unittest.main()
