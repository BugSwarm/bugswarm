import re
from datetime import datetime

from bugswarm.common import log
from bugswarm.common.credentials import GITHUB_TOKENS
from bugswarm.common.github_wrapper import GitHubWrapper

from .gha_analyzer import GitHubLogFileAnalyzer
from .java_analyzers.java_ant_analyzer import JavaAntAnalyzer
from .java_analyzers.java_gradle_analyzer import JavaGradleAnalyzer
from .java_analyzers.java_maven_analyzer import JavaMavenAnalyzer
from .java_analyzers.java_other_analyzer import JavaOtherAnalyzer
from .javascript_log_file_analyzer import JavaScriptFileAnalyzer
from .python_log_file_analyzer import PythonLogFileAnalyzer


class JavaAnt(GitHubLogFileAnalyzer, JavaAntAnalyzer):
    pass


class JavaGradle(GitHubLogFileAnalyzer, JavaGradleAnalyzer):
    pass


class JavaMaven(GitHubLogFileAnalyzer, JavaMavenAnalyzer):
    pass


class JavaOther(GitHubLogFileAnalyzer, JavaOtherAnalyzer):
    pass


class Python(GitHubLogFileAnalyzer, PythonLogFileAnalyzer):
    pass


class JavaScript(GitHubLogFileAnalyzer, JavaScriptFileAnalyzer):
    pass


class GHADispatcher(object):
    def __init__(self):
        self.build_system = {
            'maven': 0,
            'gradle': 0,
            'ant': 0,
            'play': 0,
            'NA': 0,
        }

    def get_build_system_from_build_command(self, lines):
        for line in lines:
            maven1 = re.search(r'mvn.*(install|compile|test)', line, re.M)
            maven2 = re.search(r'The command "mvn ', line, re.M)
            gradle1 = re.search(r'gradle(w)?.*(assemble|check|test)', line, re.M)
            gradle2 = re.search(r'\* Get more help at https://help\.gradle\.org', line, re.M)
            ant1 = re.search(r'ant (build-all|test)', line, re.M)
            ant2 = re.search(r'The command "ant ', line, re.M)
            play1 = re.search(r'activator-\${ACTIVATOR_VERSION}', line, re.M)
            play2 = re.search(r'export ACTIVATOR_VERSION=', line, re.M)
            if maven1 or maven2:
                return 'maven'
            elif gradle1 or gradle2:
                return 'gradle'
            elif ant1 or ant2:
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
            # pom.xml => Maven, build.gradle(.kts) => Gradle, build.xml => Ant
            if build_file['type'] == 'blob':
                if build_file['path'] == 'pom.xml':
                    build_system = 'maven'
                    files_found.append(build_file['path'])
                elif build_file['path'] == 'build.gradle' or build_file['path'] == 'build.gradle.kts':
                    build_system = 'gradle'
                    files_found.append(build_file['path'])
                elif build_file['path'] == 'build.xml':
                    build_system = 'ant'
                    files_found.append(build_file['path'])

        # more than 1 build file or no build file, check the build commands
        if len(files_found) > 1 or len(files_found) == 0:
            build_system = 'NA'

        return build_system, files_found

    def get_build_system(self, lines, job_id, trigger_sha, repo):
        build_system = 'NA'

        # We only have job id and repo, don't have trigger sha, find trigger sha
        if trigger_sha is None and repo is not None:
            trigger_sha = self.get_trigger_sha(job_id, repo)

        # We have repo and trigger sha, get build system from build file.
        if trigger_sha is not None and repo is not None:
            build_system, files_found = self.get_build_system_from_github_api(repo, trigger_sha)

        # Cannot find build system from build file, try again with build command
        if build_system == 'NA':
            build_system = self.get_build_system_from_build_command(lines)

        return build_system

    def get_trigger_sha(self, run_id, repo):
        url = 'https://api.github.com/repos/{}/actions/jobs/{}'.format(repo, run_id)
        github_wrapper = GitHubWrapper(GITHUB_TOKENS)
        status, json_data = github_wrapper.get(url)

        try:
            if status is None or not status.ok:
                log.info('Run: {} not available on github. Skipping'.format(run_id))
                return None
            return json_data['head_sha']
        except KeyError:
            log.info('Head is missing fro {}. Skipping'.format(run_id))
            return None

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

    def _validate_input(self, build_system, repo):
        # We need build system OR repo
        if build_system is None and repo is None:
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
            if not self._validate_input(build_system, repo):
                log.error('Need build system or repo to analyze java log')
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
        with open(log_file, encoding='utf-8') as f:
            log_text = f.read()

        if len(log_text) > 0 and log_text[0] == '\ufeff':
            # Some, but not all, logs from GitHub use UTF-8-BOM (ick) instead of plain UTF-8.
            # It messes up the time_lines check, so strip it out.
            log_text = log_text[1:]

        lines = log_text.splitlines()
        time_lines = []  # an array of date string
        if len(lines) > 0 and re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z ', lines[0], re.M):
            # Log comes from GitHub, we need to remove the date/time.
            # First line will look like this: 2022-05-09T15:18:04.1058603Z Requested labels: ubuntu-18.04
            time_lines = [line[:26] for line in lines]
            lines = [line[29:] for line in lines]
        return lines, time_lines

    # Determine the primary language of the build.
    # First analyze the workflow file, find all the setup actions and commands.
    # If Actions name doesn't work, use GitHub API to check repo's primary language
    # If GitHub API doesn't work, make an educated guess by searching keywords 'java'/'ruby'
    @staticmethod
    def analyze_primary_language(folds, repo=None):
        primary_language = 'unknown'

        # find primary language from actions/setup-<primary_language>
        potential_languages = set()
        for key in folds.keys():
            match = re.search(r'Run actions\/setup-(\w+)', key, re.M)
            if match:
                language = match.group(1).lower()
                if language in {'java', 'python', 'ruby', 'node'}:
                    # convert node to node_js
                    potential_languages.add('node_js' if language == 'node' else language)

            # If we can't find language using actions/setup-<primary_langauge>, check run commands instead.
            match = re.search(r'(python|nosetest|pip|pytest)', key, re.M)
            if match:
                potential_languages.add('python')
            match = re.search(r'mvnw?|gradlew?', key, re.M)
            if match:
                potential_languages.add('java')
            match = re.search(r'(nvm|npm) (run|test|install|build)', key, re.M)
            if match:
                potential_languages.add('node_js')
        if len(potential_languages) == 1:
            return potential_languages.pop()

        if repo is not None:
            # Check GitHub API for language
            url = 'https://api.github.com/repos/{}'.format(repo)
            github_wrapper = GitHubWrapper(GITHUB_TOKENS)
            status, json_data = github_wrapper.get(url)

            try:
                if status is not None and status.ok:
                    if json_data['language'] is not None:
                        language = json_data['language'].lower()
                        if language in {'java', 'python', 'ruby', 'javascript'}:
                            # Sometimes GitHub API will return 'inaccurate' primary language
                            # For example, it returns HTML for magellan2/magellan2.
                            if language == 'javascript':
                                return 'node_js'
                            return language
            except KeyError:
                # language attribute not found
                pass

        java = 0
        ruby = 0
        # In case api or folding do not work, go though all the lines and make an educated guess at the language.
        for fold in folds:
            for line in folds[fold]['content']:
                if re.search(r'(Welcome to Gradle|Apache Maven) \d\.\d\.\d', line):
                    return 'java'
                if 'java' in line.lower():
                    java += 1
                if 'ruby' in line.lower():
                    ruby += 1
        if java >= 10:
            primary_language = 'java'
        elif ruby >= 10:
            primary_language = 'ruby'

        return primary_language

    # Split build log into different group
    # ##[group]Title
    # ##[endgroup]
    @staticmethod
    def split(lines, time_lines=None):
        # initialize folds with `out_of_fold`
        folds = {}
        current_fold = 'out_of_fold'
        folds[current_fold] = {}
        folds[current_fold]['content'] = []

        # If lines and time_lines don't match, don't create the duration attribute
        start_time = 0 if time_lines is not None and len(lines) == len(time_lines) else -1
        previous_group = ''

        for line_number, line in enumerate(lines):
            match = re.search(r'##\[group\](.*)', line, re.M)
            if match:
                current_fold = match.group(1)

                # init folds for new group
                if current_fold not in folds:
                    folds[current_fold] = {'content': []}

                # Calculate fold duration from ##[group] to next ##[group]
                try:
                    if start_time >= 0 and previous_group != '':
                        # End time for the PREVIOUS group
                        end_time = datetime.fromisoformat(time_lines[line_number]).timestamp()
                        folds[previous_group]['duration'] = round(end_time - start_time, 2)
                except ValueError:
                    pass

                if start_time >= 0:
                    # if start_time is -1, it is a reproduced log so it doesn't have time info.
                    start_time = datetime.fromisoformat(time_lines[line_number]).timestamp()
                    previous_group = current_fold
                continue

            match = re.search(r'##\[endgroup\]', line, re.M)
            if match:
                current_fold = 'out_of_fold'
                continue

            folds[current_fold]['content'].append(line)
        return folds

    # force - force run analyze when we know the job is in Java, avoiding skipping based on primary language.
    def analyze(self, log_path, job_id, build_system=None, trigger_sha=None, repo=None, force=0):
        lines, time_lines = GHADispatcher.read_log_into_lines(log_path)
        folds = GHADispatcher.split(lines, time_lines)
        primary_language = GHADispatcher.analyze_primary_language(folds, repo)
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
