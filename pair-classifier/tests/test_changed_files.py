import bs4 as bs
import unittest
import sys

from unittest import mock

sys.path.append('../')
from get_changed_files import get_changed_files, get_changed_files_metrics  # noqa: E402


class Test(unittest.TestCase):

    def _mock_response(self, status=200, content="CONTENT", json_data=None, raise_for_status=None):
        mock_resp = mock.Mock()
        # mock raise_for_status call w/ optional error
        mock_resp.raise_for_status = mock.Mock()
        if raise_for_status:
            mock_resp.raise_for_status.side_effect = raise_for_status
        mock_resp.status = status
        mock_resp.content = content
        if json_data:
            mock_resp.json = mock.Mock(
                return_value=json_data
            )
        return mock_resp

    def _mock_data(self, method_name):
        with open('webscraped_files/' + method_name + '.txt', 'r') as f:
            return f.read()

    def test_mozilla_1(self):  # raphw-byte-buddy-95795967 #2 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_1')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'byte-buddy-dep/src/main/java/net/bytebuddy/dynamic/ClassFileLocator.java',
            'byte-buddy-dep/src/test/java/net/bytebuddy/dynamic/ClassFileLocatorAgentBasedTest.java'
        ]

        count, changed_files = get_changed_files(soup)
        self.assertEqual(count, 2)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_2(self):  # Abjad-abjad-289716771 #4 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_2')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'abjad/tools/agenttools/IterationAgent.py',
            'abjad/tools/quantizationtools/NaiveAttackPointOptimizer.py',
            'abjad/tools/selectiontools/Selection.py',
            'abjad/tools/selectortools/Selector.py'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 4)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_3(self):  # Abjad-abjad-315458775 #1 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_3')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = ['abjad/tools/datastructuretools/Pattern.py']

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 1)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_4(self):  # Abjad-abjad-303759206 #19 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_4')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'abjad/__init__.py',
            'abjad/tools/indicatortools/Clef.py',
            'abjad/tools/indicatortools/SystemBreak.py',
            'abjad/tools/scoretools/Chord.py',
            'abjad/tools/scoretools/Cluster.py',
            'abjad/tools/scoretools/Component.py',
            'abjad/tools/scoretools/Container.py',
            'abjad/tools/scoretools/Context.py',
            'abjad/tools/scoretools/GraceContainer.py',
            'abjad/tools/scoretools/Inspection.py',
            'abjad/tools/scoretools/Leaf.py',
            'abjad/tools/scoretools/Measure.py',
            'abjad/tools/scoretools/Tuplet.py',
            'abjad/tools/scoretools/test/test_scoretools_Inspection_get_effective.py',
            'abjad/tools/systemtools/IndicatorWrapper.py',
            'abjad/tools/systemtools/LilyPondFormatBundle.py',
            'abjad/tools/systemtools/LilyPondFormatManager.py',
            'abjad/tools/systemtools/SlotContributions.py',
            'abjad/tools/topleveltools/attach.py'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 19)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_5(self):  # square-okhttp-99350732 #11 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_5')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'okcurl/src/main/java/okhttp3/curl/Main.java',
            'okhttp-logging-interceptor/src/test/java/okhttp3/logging/HttpLoggingInterceptorTest.java',
            'okhttp-tests/src/test/java/okhttp3/CacheTest.java',
            'okhttp-tests/src/test/java/okhttp3/ConnectionPoolTest.java',
            'okhttp-tests/src/test/java/okhttp3/ConnectionReuseTest.java',
            'okhttp-tests/src/test/java/okhttp3/URLConnectionTest.java',
            'okhttp-tests/src/test/java/okhttp3/internal/framed/HttpOverSpdyTest.java',
            'okhttp-urlconnection/src/main/java/okhttp3/internal/SystemPropertiesConnectionPool.java',
            'okhttp-urlconnection/src/test/java/okhttp3/UrlConnectionCacheTest.java',
            'okhttp/src/main/java/okhttp3/ConnectionPool.java',
            'okhttp/src/main/java/okhttp3/OkHttpClient.java'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 11)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_6(self):  # tananaev-traccar-85219838 #1 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_6')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = ['src/org/traccar/helper/Parser.java']

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 1)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_7(self):  # apache-struts-147673952 #2 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_7')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'core/src/main/java/org/apache/struts2/dispatcher/mapper/DefaultActionMapper.java',
            'plugins/jfreechart/pom.xml'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 2)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_8(self):  # winder-Universal-G-Code-Sender-172454077 #2 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_8')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'ugs-core/src/com/willwinder/universalgcodesender/GrblController.java',
            'ugs-core/test/com/willwinder/universalgcodesender/GrblControllerTest.java'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 2)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_9(self):  # ImmobilienScout24-deadcode4j-131735009 #4 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_9')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'src/main/java/de/is24/deadcode4j/Utils.java',
            'src/main/java/de/is24/deadcode4j/analyzer/ExtendedXmlAnalyzer.java',
            'src/main/java/de/is24/deadcode4j/analyzer/SimpleXmlAnalyzer.java',
            'src/main/java/de/is24/deadcode4j/analyzer/XmlAnalyzer.java'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 4)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_10(self):  # thm-projects-arsnova-backend-343416326 #11 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_10')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'pom.xml',
            'src/main/java/de/thm/arsnova/controller/AbstractEntityController.java',
            'src/main/java/de/thm/arsnova/controller/CommentController.java',
            'src/main/java/de/thm/arsnova/controller/ContentController.java',
            'src/main/java/de/thm/arsnova/controller/MotdController.java',
            'src/main/java/de/thm/arsnova/controller/RoomController.java',
            'src/main/java/de/thm/arsnova/entities/AnswerStatistics.java',
            'src/main/java/de/thm/arsnova/entities/migration/FromV2Migrator.java',
            'src/main/java/de/thm/arsnova/entities/migration/ToV2Migrator.java',
            'src/main/java/de/thm/arsnova/persistance/couchdb/CouchDbInitializer.java',
            'src/main/java/de/thm/arsnova/services/ContentServiceImpl.java'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 11)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_11(self):  # Whiley-WhileyCompiler-102007590 #15 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_11')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'modules/wyc/src/wyc/builder/CodeGenerator.java',
            'modules/wyc/src/wyc/builder/FlowTypeChecker.java',
            'modules/wyc/src/wyc/io/WhileyFileParser.java',
            'modules/wyc/src/wyc/testing/AllValidTests.java',
            'modules/wyil/src/wyil/builders/VcGenerator.java',
            'modules/wyjc/src/wyjc/testing/RuntimeValidTests.java',
            'modules/wyrt/src/whiley/lang/Array.whiley',
            'modules/wyrt/src/whiley/lang/Math.whiley',
            'tests/valid/Cast_Valid_5.whiley',
            'tests/valid/RealSplit_Valid_1.whiley',
            'tests/valid/RecordCoercion_Valid_1.whiley',
            'tests/valid/While_Valid_30.whiley',
            'tests/valid/While_Valid_33.whiley',
            'tests/valid/While_Valid_37.whiley',
            'tests/valid/While_Valid_47.whiley'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 15)
        self.assertListEqual(changed_files, changed_github)

    def test_mozilla_12(self):  # GoClipse-goclipse-126655137 #5 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_12')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_github = [
            'plugin_ide.core.tests/src-lang/melnorme/lang/ide/core/operations/build/BuildManager_Test.java',
            'plugin_ide.core/src-lang/melnorme/lang/ide/core/operations/build/BuildTargetOperation.java',
            'plugin_ide.core/src/com/googlecode/goclipse/core/operations/GoBuildManager.java',
            'plugin_ide.ui/src-lang/melnorme/lang/ide/ui/build/EnvironmentSettingsEditor.java',
            'plugin_ide.ui/src-lang/melnorme/lang/ide/ui/fields/FieldDialog.java'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 5)
        self.assertListEqual(changed_files, changed_github)

    # NOTE: changed files has really long path names
    def test_mozilla_13(self):  # checkstyle-checkstyle-102599923 #8 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_13')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 8)

    def test_mozilla_14(self):  # apache-dubbo-506092104
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_14')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 26)

    def test_mozilla_15(self):  # scikit-learn-scikit-learn-79576031
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_15')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 37)

    def test_mozilla_16(self):  # charite-jannovar-249719464 #90 changed
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_16')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 90)

    def test_mozilla_17(self):  # scikit-learn-scikit-learn-398261936
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_17')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 91)

    def test_mozilla_18(self):  # Azure-azure-sdk-for-java-159452848
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_18')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 97)

    def test_mozilla_19(self):  # scikit-learn-scikit-learn-414758534
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_19')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 252)

    def test_mozilla_20(self):  # scikit-learn-scikit-learn-409303510
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_20')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 270)

    def test_mozilla_21(self):  # SonarSource-sonar-java-341335847 #WRONG 0/394
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_21')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        metrics = get_changed_files_metrics(soup)
        self.assertEqual(metrics['num_of_changed_files'], 394)

    def test_mozilla_22(self):  # igniterealtime-Openfire-302593314
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_mozilla_22')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        metrics = get_changed_files_metrics(soup)
        self.assertEqual(metrics['num_of_changed_files'], 2019)

    def test_applewebkit_1(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_applewebkit_1')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        metrics = get_changed_files_metrics(soup)
        self.assertEqual(metrics['num_of_changed_files'], 7)

    def test_applewebkit_2(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_applewebkit_2')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        metrics = get_changed_files_metrics(soup)
        self.assertEqual(metrics['num_of_changed_files'], 3)

    def test_applewebkit_3(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_applewebkit_3')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 1)

    def test_chrome_1(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_chrome_1')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_on_github = [
            'plugins/json/src/test/java/org/apache/struts2/json/JSONInterceptorTest.java'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 1)
        self.assertEqual(changed_files, changed_on_github)

    def test_chrome_2(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_chrome_2')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_on_github = [
            'okhttp/src/main/java/okhttp3/internal/connection/StreamAllocation.java',
            'okhttp/src/main/java/okhttp3/internal/http/RetryAndFollowUpInterceptor.java'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 2)
        self.assertEqual(changed_files, changed_on_github)

    def test_chrome_3(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_chrome_3')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_on_github = [
            'testsuite/integration/src/test/java/org/keycloak/testsuite/account/AccountTest.java'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 1)
        self.assertEqual(changed_files, changed_on_github)

    def test_chrome_4(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_chrome_4')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_on_github = [
            'test.py'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 1)
        self.assertEqual(changed_files, changed_on_github)

    def test_chrome_5(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_chrome_5')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_on_github = [
            'tornado/test/web_test.py',
            'tornado/test/websocket_test.py',
            'tornado/web.py'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 3)
        self.assertEqual(changed_files, changed_on_github)

    def test_safari_1(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_safari_1')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_on_github = [
            '.gitignore',
            'docs/source/builtin_types.rst',
            'extensions/setup.py',
            'mypy/build.py',
            'mypy/errors.py',
            'mypy/main.py',
            'mypy/semanal.py',
            'mypy/semanal_pass3.py',
            'mypy/semanal_shared.py',
            'mypy/server/astdiff.py',
            'mypy/server/astmerge.py',
            'mypy/server/update.py',
            'mypy/test/helpers.py',
            'mypy/test/testcheck.py',
            'mypy/test/testerrorstream.py',
            'mypy/test/testfinegrained.py',
            'mypy/test/testgraph.py',
            'mypy/traverser.py',
            'mypy/typeanal.py',
            'test-data/unit/check-newtype.test',
            'test-data/unit/check-typeddict.test',
            'test-data/unit/check-unions.test',
            'test-data/unit/diff.test',
            'test-data/unit/errorstream.test',
            'test-data/unit/fine-grained-modules.test',
            'test-data/unit/fine-grained.test',
            'typeshed'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 27)
        self.assertEqual(changed_files, changed_on_github)

    def test_safari_2(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_safari_2')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_on_github = [
            'tests/test_plugins.py'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 1)
        self.assertEqual(changed_files, changed_on_github)

    def test_safari_3(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_safari_3')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        changed_on_github = [
            'pychron/dvc/func.py',
            'pychron/experiment/automated_run/automated_run.py',
            'pychron/experiment/automated_run/persistence_spec.py',
            'pychron/lasers/laser_managers/fusions_laser_manager.py',
            'pychron/lasers/laser_managers/pychron_laser_manager.py',
            'pychron/lasers/stage_managers/stage_manager.py',
            'pychron/lasers/stage_managers/video_stage_manager.py',
            'pychron/mv/lumen_detector.py',
            'pychron/pyscripts/extraction_line_pyscript.py',
            'pychron/tx/protocols/laser.py'
        ]

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 10)
        self.assertEqual(changed_files, changed_on_github)

    def test_safari_4(self):
        mock_resp = self._mock_response(
            json_data=self._mock_data('test_safari_4')
        )
        soup = bs.BeautifulSoup(mock_resp.json.return_value, 'lxml')

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 1)


if __name__ == '__main__':
    unittest.main()
