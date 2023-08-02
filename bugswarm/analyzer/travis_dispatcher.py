import re
from bugswarm.common import log
from bugswarm.common.github_wrapper import GitHubWrapper
from bugswarm.common.travis_wrapper import TravisWrapper
from bugswarm.common.credentials import GITHUB_TOKENS, DATABASE_PIPELINE_TOKEN
from bugswarm.common.rest_api.database_api import DatabaseAPI
from requests.exceptions import HTTPError
from .java_analyzers.java_ant_analyzer import JavaAntAnalyzer
from .java_analyzers.java_gradle_analyzer import JavaGradleAnalyzer
from .java_analyzers.java_maven_analyzer import JavaMavenAnalyzer
from .java_analyzers.java_other_analyzer import JavaOtherAnalyzer
from .python_log_file_analyzer import PythonLogFileAnalyzer
from .javascript_log_file_analyzer import JavaScriptFileAnalyzer
from .travis_analyzer import TravisLogFileAnalyzer


class JavaAnt(TravisLogFileAnalyzer, JavaAntAnalyzer):
    pass


class JavaGradle(TravisLogFileAnalyzer, JavaGradleAnalyzer):
    pass


class JavaMaven(TravisLogFileAnalyzer, JavaMavenAnalyzer):
    pass


class JavaOther(TravisLogFileAnalyzer, JavaOtherAnalyzer):
    pass


class Python(TravisLogFileAnalyzer, PythonLogFileAnalyzer):
    pass


class JavaScript(TravisLogFileAnalyzer, JavaScriptFileAnalyzer):
    pass


class TravisDispatcher(object):
    def __init__(self):
        self.build_system = {
            'maven': 0,
            'gradle': 0,
            'ant': 0,
            'play': 0,
            'NA': 0,
        }

        self.tw = TravisWrapper()

    def get_build_system_from_build_command(self, lines):
        for line in lines:
            maven1 = re.search(r'(\[0K\$ )?mvn.*install.*', line, re.M)
            maven2 = re.search(r'(\[0K\$ )?mvn.*compile test', line, re.M)
            maven3 = re.search(r'The command "mvn .*', line, re.M)
            gradle1 = re.search(r'(\[0K\$ )?.*(./)?gradle(w)?.*assemble', line, re.M)
            ant1 = re.search(r'(\[0K\$ )?ant build-all.*', line, re.M)
            ant2 = re.search(r'(\[0K\$ )?ant test.*', line, re.M)
            ant3 = re.search(r'The command "ant .*', line, re.M)
            play1 = re.search(r'(\[0K\$ )?(./)?activator-\${ACTIVATOR_VERSION}.*', line, re.M)
            play2 = re.search(r'(\$ )?export ACTIVATOR_VERSION=.*', line, re.M)

            if maven1 or maven2 or maven3:
                return 'maven'
            elif gradle1:
                return 'gradle'
            elif ant1 or ant2 or ant3:
                return 'ant'
            elif play1 or play2:
                return 'play'

        return 'NA'

    def get_build_system_from_github_api(self, repo: str, build_commit_sha: str):
        url = 'https://api.github.com/repos/{}/git/commits/{}'.format(repo, build_commit_sha)
        github_wrapper = GitHubWrapper(GITHUB_TOKENS)
        status, json_data = github_wrapper.get(url)
        build_system = 'NA'
        files_found = []

        try:
            if status is None or not status.ok:
                log.info('commit: {} not available on github. Skipping'.format(build_commit_sha))
                return build_system, files_found
            url = json_data['tree']['url']
            status, json_data = github_wrapper.get(url)
            if status is None or not status.ok:
                log.info('Unable to fetch tree: {}. Skipping'.format(status))
                return build_system, files_found
            tree = json_data['tree']
        except AttributeError:
            # no commit
            log.info('Unable to fetch commit {}. Skipping.'.format(build_commit_sha))
            return build_system, files_found
        except KeyError:
            # no tree
            log.info('Git tree not found, commit {}. Skipping'.format(build_commit_sha))
            return build_system, files_found

        for build_file in tree:
            # assume the build file always in root, otherwise need to do this recursively(very expensive)
            # 'blob' stands for normal file
            # pom.xml => Maven, build.gradle => Gradle, build.xml => Ant
            if build_file['type'] == 'blob':
                if build_file['path'] == 'pom.xml':
                    build_system = 'maven'
                    files_found.append('pom.xml')
                elif build_file['path'] == 'build.gradle':
                    build_system = 'gradle'
                    files_found.append('build.gradle')
                elif build_file['path'] == 'build.xml':
                    build_system = 'ant'
                    files_found.append('build.xml')

        # more than 1 build file or no build file, check the build commands or the travis info
        if len(files_found) > 1 or len(files_found) == 0:
            build_system = 'NA'

        return build_system, files_found

    def get_build_system_from_travis_info(self, job_id, files_found):
        build_system = 'NA'

        try:
            info = self.tw.get_job_info(job_id)
        except HTTPError:
            return build_system
        config = None
        if 'env' in info['config']:
            config = info['config']['env']
            m = config.find('maven') != -1
            g = config.find('gradle') != -1
            a = config.find('ant') != -1
            if m and ('pom.xml' in files_found):
                build_system = 'maven'
            elif g and ('build.gradle' in files_found):
                build_system = 'gradle'
            elif a and ('build.xml' in files_found):
                build_system = 'ant'

        return build_system

    def get_build_system_from_bugswarm_database(self, job_id):
        try:
            int_job_id = int(job_id)
            filters = '{"$or": [{"passed_job.job_id": %d}, {"failed_job.job_id": %d}]}' % (int_job_id, int_job_id)
            for result in DatabaseAPI(DATABASE_PIPELINE_TOKEN).filter_artifacts(filters):
                # For non-Java artifact, this will return 'NA'.
                build_system = result['build_system']
                return build_system if build_system == 'NA' else build_system.lower()
        except Exception as e:
            log.error("Unable to get build system from BugSwarm's API due to {}".format(repr(e)))
        # We call this function in analyzer.py, it expects 'None' if we cannot get build system from BugSwarm API.
        return None

    def get_build_system(self, lines, job_id, trigger_sha, repo):
        build_system = 'NA'
        files_found = []

        if trigger_sha is not None and repo is not None:
            build_system, files_found = self.get_build_system_from_github_api(repo, trigger_sha)

        if build_system == 'NA':
            build_system = self.get_build_system_from_build_command(lines)

        if build_system == 'NA':
            build_system = self.get_build_system_from_travis_info(job_id, files_found)

        return build_system

    def _get_java_analyzer(self, primary_language, lines, folds, job_id, confirmed_analyzer, trigger_sha, repo):
        if confirmed_analyzer is None:
            confirmed_analyzer = self.get_build_system(lines, job_id, trigger_sha, repo)

        # get_build_system will return 'NA' if it can not determine the build system
        if confirmed_analyzer != 'NA':
            if confirmed_analyzer == 'maven':
                self.build_system['maven'] += 1
                log.debug('Using maven Analyzer')
                return JavaMaven(primary_language, folds, job_id)
            elif confirmed_analyzer == 'gradle':
                self.build_system['gradle'] += 1
                log.debug('Using gradle Analyzer')
                return JavaGradle(primary_language, folds, job_id)
            elif confirmed_analyzer == 'ant':
                self.build_system['ant'] += 1
                log.debug('Using ant Analyzer')
                return JavaAnt(primary_language, folds, job_id)
            elif confirmed_analyzer == 'play':
                self.build_system['play'] += 1
                log.debug('Using other Analyzer')
                return JavaOther(primary_language, folds, job_id, confirmed_analyzer)
        else:
            self.build_system['NA'] += 1
            log.debug('Using other Analyzer')
            return JavaOther(primary_language, folds, job_id, 'NA')

    def _validate_input(self, build_system, trigger_sha, repo):
        if all(x is None for x in [build_system, trigger_sha, repo]):
            return False
        elif build_system is None and (trigger_sha is None or repo is None):
            return False
        return True

    def _get_specific_language_analyzer(self, primary_language, lines, folds, job_id, build_system, trigger_sha, repo,
                                        force):
        # Update this function to extend to other languages.
        lang = str(primary_language.lower())
        use_java = ['java', 'scala', 'groovy', 'clojure']
        if force:
            log.warning('Forcing Java analyzer')
            return self._get_java_analyzer('java', lines, folds, job_id, build_system, trigger_sha, repo)
        if lang == 'ruby':
            # return RubyLogFileAnalyzer(log, folds)
            return None
        elif lang in use_java:
            if not self._validate_input(build_system, trigger_sha, repo):
                log.error('Need build system or trigger sha and repo to analyze java log')
                return None
            return self._get_java_analyzer(primary_language, lines, folds, job_id, build_system, trigger_sha, repo)
        elif lang == 'node_js':
            return JavaScript(primary_language, folds, job_id)
        elif lang == 'python':
            return Python(primary_language, folds, job_id)
        else:
            # log.warning('No primary language detected. lang =', lang)
            return None

    @staticmethod
    def read_log_into_lines(log_file):
        lines = []
        with open(log_file, encoding='utf-8') as f:
            for l in f:
                lines.append(str(l.rstrip('\n')))
        return lines

    # Determine the primary language of the build.
    @staticmethod
    def analyze_primary_language(folds):
        primary_language = 'unknown'
        if 'system_info' in folds:
            for line in folds['system_info']['content']:
                line = str(line)
                match = re.search(r'^Build language: (.*)', line, re.M)
                if match:
                    primary_language = match.group(1)
        else:
            java = 0
            ruby = 0
            # In case folding does not work, make an educated guess at the language.
            for fold in folds:
                for line in folds[fold]['content']:
                    if 'java' in line:
                        java += 1
                    if 'ruby' in line:
                        ruby += 1
            if java >= 3:
                primary_language = 'java'
            elif ruby >= 3:
                primary_language = 'ruby'

        if '\\' in primary_language:
            primary_language = primary_language.split('\\')[0]
        if r'\["' in primary_language:
            primary_language = primary_language[3:-3]

        return primary_language.lower()

    # Split buildlog into different folds.
    @staticmethod
    def split(lines):
        # initialize folds with `out_of_fold`
        folds = {}
        current_fold = 'out_of_fold'
        folds[current_fold] = {}
        folds[current_fold]['content'] = []

        for line in lines:
            # line = line.uncolorize
            match = re.search(r'travis_fold:start:([\w\.]*)', line, re.M)
            if match:
                current_fold = match.group(1)
                continue

            match = re.search(r'travis_fold:end:([\w\.]*)', line, re.M)
            if match:
                current_fold = 'out_of_fold'
                continue

            if current_fold not in folds:
                folds[current_fold] = {'content': []}

            match = re.search(r'travis_time:.*?,duration=(\d*)', line, re.M)
            if match:
                try:
                    folds[current_fold]['duration'] = round((float(match.group(1)) / 1000 / 1000 / 1000))
                except ValueError:
                    pass
                continue
            folds[current_fold]['content'].append(line)
        return folds

    # force - force run analyze when we know the job is in Java, avoiding skipping based on primary language.
    def analyze(self, log_path, job_id, build_system=None, trigger_sha=None, repo=None, force=0):
        lines = TravisDispatcher.read_log_into_lines(log_path)
        folds = TravisDispatcher.split(lines)
        primary_language = TravisDispatcher.analyze_primary_language(folds)

        analyzer = self._get_specific_language_analyzer(
            primary_language, lines, folds, job_id, build_system, trigger_sha, repo, force)

        if analyzer:
            analyzer.analyze()
            return analyzer.output()
        else:
            non_analyzed = {
                'tr_job_id': job_id,
                'primary_language': primary_language,
            }
            return non_analyzed
