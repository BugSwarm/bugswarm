import bs4 as bs
import requests
import unittest
import sys

sys.path.append('../')
from webscraping_changed_files import get_num_changed_files  # noqa: E402
from webscraping_changed_files import get_changed_files  # noqa: E402

MAX = 20


class Test(unittest.TestCase):

    # TEST1
    def test1(self):  # raphw-byte-buddy-95795967 #2 changed
        url = (
            'https://github.com/raphw/byte-buddy/compare/5a2cc59b4bc18b778047c0b3775953155491cecc..'
            '61eb2bc5248803e2f1efa24cf5589a41ba435a14'
        )

        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }

        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        changed_github = [
            'byte-buddy-dep/src/main/java/net/bytebuddy/dynamic/ClassFileLocator.java',
            'byte-buddy-dep/src/test/java/net/bytebuddy/dynamic/ClassFileLocatorAgentBasedTest.java'
        ]

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)
        self.assertEqual(count, 2)
        self.assertListEqual(changed_files, changed_github)

    # TEST2
    def test2(self):  # Abjad-abjad-289716771 #4 changed
        url = (
            'https://github.com/Abjad/abjad/compare/9306968ceadf5a12d4ddbbd037a81a60369300a5..'
            'a07b59078c9121de60a0afc241f4142e5e8ee5bb'
        )

        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        changed_github = [
            'abjad/tools/agenttools/IterationAgent.py',
            'abjad/tools/quantizationtools/NaiveAttackPointOptimizer.py',
            'abjad/tools/selectiontools/Selection.py',
            'abjad/tools/selectortools/Selector.py']

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 4)
        self.assertListEqual(changed_files, changed_github)

    # TEST3
    def test3(self):  # Abjad-abjad-315458775 #1 changed
        url = (
            'https://github.com/Abjad/abjad/compare/d8cd675ef88d02b6490897b0f3ca387e97739359..'
            'daf812bdd85fe62abf62ef9363ab2e3637858cb2'
        )

        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        changed_github = ['abjad/tools/datastructuretools/Pattern.py']

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 1)
        self.assertListEqual(changed_files, changed_github)

    # TEST4
    def test4(self):  # Abjad-abjad-303759206 #19 changed
        url = (
            'https://github.com/Abjad/abjad/compare/84dddf2b4486940a4d3362f3d345b9848b70c4dc..'
            '51009919290032f9e32dac6f33233b0710ba1327'
        )

        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

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
            'abjad/tools/topleveltools/attach.py']

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 19)
        self.assertListEqual(changed_files, changed_github)

    # TEST5
    def test5(self):  # square-okhttp-99350732 #11 changed
        url = (
            'https://github.com/square/okhttp/compare/0529c693d70e92eeef44bdc818a4b4185d8462e2..'
            'fd837e36226451c5dcd987aef71ab1f3723b6649'
        )

        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

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
            'okhttp/src/main/java/okhttp3/OkHttpClient.java']

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 11)
        self.assertListEqual(changed_files, changed_github)

    # TEST6
    def test6(self):  # tananaev-traccar-85219838 #1 changed
        url = (
            'https://github.com/traccar/traccar/compare/173d054219f1e37e7089c23cac0f530915834ee4..'
            '766064092ca4f85eacfa741e1ff772ea5b981d1a'
        )

        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        changed_github = ['src/org/traccar/helper/Parser.java']

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 1)
        self.assertListEqual(changed_files, changed_github)

    # TEST7
    def test7(self):  # apache-struts-147673952 #2 changed
        url = (
            'https://github.com/apache/struts/compare/1643568095edd8e0f9a3147c0edf396cd6906b44..'
            '0bd2e705897b365740e72229dbd9eb64c8c32229'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        changed_github = [
            'core/src/main/java/org/apache/struts2/dispatcher/mapper/DefaultActionMapper.java',
            'plugins/jfreechart/pom.xml'
        ]

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 2)
        self.assertListEqual(changed_files, changed_github)

    # TEST8
    def test8(self):  # winder-Universal-G-Code-Sender-172454077 #2 changed
        url = (
            'https://github.com/winder/Universal-G-Code-Sender/compare/4e1da3358c70f391001f484630ae4f4cc89cc7dd..'
            '4f429a723a7a2f30a84d38ce6e04062f7f673304'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        changed_github = [
            'ugs-core/src/com/willwinder/universalgcodesender/GrblController.java',
            'ugs-core/test/com/willwinder/universalgcodesender/GrblControllerTest.java'
        ]

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 2)
        self.assertListEqual(changed_files, changed_github)

    # TEST9
    def test9(self):  # ImmobilienScout24-deadcode4j-131735009 #4 changed
        url = (
            'https://github.com/Scout24/deadcode4j/compare/5d32dbef57eb4c7534f45c2c3027d1c0a9a80ddd..'
            'cc3738ddb73424aef775cd9401714cb77b3bb957'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        changed_github = [
            'src/main/java/de/is24/deadcode4j/Utils.java',
            'src/main/java/de/is24/deadcode4j/analyzer/ExtendedXmlAnalyzer.java',
            'src/main/java/de/is24/deadcode4j/analyzer/SimpleXmlAnalyzer.java',
            'src/main/java/de/is24/deadcode4j/analyzer/XmlAnalyzer.java'
        ]

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 4)
        self.assertListEqual(changed_files, changed_github)

    # TEST10
    def test10(self):  # thm-projects-arsnova-backend-343416326 #11 changed
        url = (
            'https://github.com/thm-projects/arsnova-backend/compare/d4f6ef46e6c1e526ce6419540d2ba21fa9a9c615..'
            'd8382554d122e9856abe64da9147a7a64976d4ae'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

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

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 11)
        self.assertListEqual(changed_files, changed_github)

    # TEST11
    def test11(self):  # Whiley-WhileyCompiler-102007590 #15 changed
        url = (
            'https://github.com/Whiley/WhileyCompiler/compare/dd9a3e676a527c4c8ec83fb0cb5aa9862e23bb83..'
            '7c46187bee26bb919bc438bc43e6bffcc082c7cf'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

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

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 15)
        self.assertListEqual(changed_files, changed_github)

    # TEST12
    def test12(self):  # GoClipse-goclipse-126655137 #5 changed
        url = (
            'https://github.com/GoClipse/goclipse/compare/d3272165138be4e581379e84f0e0c0f293eb9c47..'
            '1b15b05debe5dfee58e616a719c319a86c206e1d'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        changed_github = [
            'plugin_ide.core.tests/src-lang/melnorme/lang/ide/core/operations/build/BuildManager_Test.java',
            'plugin_ide.core/src-lang/melnorme/lang/ide/core/operations/build/BuildTargetOperation.java',
            'plugin_ide.core/src/com/googlecode/goclipse/core/operations/GoBuildManager.java',
            'plugin_ide.ui/src-lang/melnorme/lang/ide/ui/build/EnvironmentSettingsEditor.java',
            'plugin_ide.ui/src-lang/melnorme/lang/ide/ui/fields/FieldDialog.java'
        ]

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 5)
        self.assertListEqual(changed_files, changed_github)

    # TEST13
    # NOTE: changed files has really long path names
    def test13(self):  # checkstyle-checkstyle-102599923 #8 changed
        url = (
            'https://github.com/checkstyle/checkstyle/compare/f825a147e3a5b8f13078fb2c8ec7a791ccb82ac6..'
            'd22bc699cb86d43f57677cadf7dc747e878306e9'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, changed_files = get_changed_files(soup)

        self.assertEqual(count, 8)

    # TEST14
    def test14(self):  # apache-dubbo-506092104
        url = (
            'https://github.com/apache/dubbo/compare/16cedb2a4055a98839bdf550c3c570711e49e12c..'
            '8d5e2acadc6ca09516d67ab5f68da4bb5d6304ec'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 26)

    # TEST15
    def test15(self):  # scikit-learn-scikit-learn-79576031
        url = (
            'https://github.com/scikit-learn/scikit-learn/compare/81102b435b2d6782ad6bb4f873de58aeccf02243..'
            'a17ae90a02edfb8b86ef844659d766258294b726'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 37)

    # TEST16
    def test16(self):  # charite-jannovar-249719464 #90 changed
        url = (
            'https://github.com/charite/jannovar/compare/7c7a0eaebae8869cec73e070b09cefcad9973fe6..'
            '1fd3cbfc428732b97c5c35ffe09434502e3a99be'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 90)

    # TEST17
    def test17(self):  # scikit-learn-scikit-learn-398261936
        url = (
            'https://github.com/scikit-learn/scikit-learn/compare/0a9a97a13a9851a9541a151c12f27104b0008f41..'
            '9ef853194fe9c2c3ffca9268acc55b46b2dc486d'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 91)

    # TEST18
    def test18(self):  # Azure-azure-sdk-for-java-159452848
        url = (
            'https://github.com/Azure/azure-sdk-for-java/compare/ed2ac1dc875306302b9068a387d7624460340214..'
            '266a7a7806fa39868d9940c4504d7a48551fd4c9'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 97)

    # TEST19
    def test19(self):  # scikit-learn-scikit-learn-414758534
        url = (
            'https://github.com/scikit-learn/scikit-learn/compare/803683210add5d6302e4789027be277909042811..'
            '38886dda4c1316bfc4d93be8cea67766c9d58af3'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 252)

    # TEST20
    def test20(self):  # scikit-learn-scikit-learn-409303510
        url = (
            'https://github.com/scikit-learn/scikit-learn/compare/21527b44194b1a2db5faa345da9f6f6fc37dd8ac..'
            '34df994b74fc87d5d30ada37cdbbfb90227ef103'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 270)

    # TEST21
    def test21(self):  # SonarSource-sonar-java-341335847 #WRONG 0/394
        url = (
            'https://github.com/SonarSource/sonar-java/compare/d2429a9ba90bb5aa4a007f73c243eb49423faee9..'
            '523449817cb3bc7d7a74f0b85ec442f27be7d912'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 394)

    # TEST22
    def test22(self):  # igniterealtime-Openfire-302593314
        url = (
            'https://github.com/igniterealtime/Openfire/compare/07c90d2f3ce2cc34fc9e69464851129d0883dd14..'
            'e1b39df28803e76c8e9e2ca2a56c4587567e402c'
        )
        headers = {
            "User-Agent": "Mozilla/5.0", "Accept":
                "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp, image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q=0.9"
        }
        source = requests.get(url, headers=headers)
        soup = bs.BeautifulSoup(source.text, 'lxml')

        read_count = get_num_changed_files(soup)
        if read_count > MAX:
            return

        count, _ = get_changed_files(soup)

        self.assertEqual(count, 2019)


if __name__ == '__main__':
    unittest.main()
