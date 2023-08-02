import sys
import unittest

sys.path.append('..')
from python_log_parser import (parse_log, extract_python_from_pip_version,  # noqa: E402
                               extract_python_from_virtual_env, VIRTUAL_ENV_REGEX)


class TestFunctions(unittest.TestCase):
    def test_extract_python_from_pip_version(self):
        for line, expected in [
            ('pip 6.0.7 from /home/travis/virtualenv/pypy-2.5.0/site-packages (python 2.7)\n',
             ('', 'pip==6.0.7')),
            ('pip 6.0.7 from /home/travis/virtualenv/python2.7.9/lib/python2.7/site-packages (python 2.7)\n',
             ('python2.7', 'pip==6.0.7')),
            ('pip 6.0.7 from /home/travis/virtualenv/python3.4.2/lib/python3.4/site-packages (python 3.4)\n',
             ('python3.4', 'pip==6.0.7')),
            ('pip 9.0.1 from /home/travis/virtualenv/python2.7.13/lib/python2.7/site-packages (python 2.7)\n',
             ('python2.7', 'pip==9.0.1')),
            ('pip 9.0.1 from /home/travis/virtualenv/python3.4.6/lib/python3.4/site-packages (python 3.4)\n',
             ('python3.4', 'pip==9.0.1')),
            ('pip 9.0.1 from /home/travis/virtualenv/python3.6.3/lib/python3.6/site-packages (python 3.6)\n',
             ('python3.6', 'pip==9.0.1')),
            ('Python 2.7.13\n', ('', '')),
        ]:
            self.assertEqual(extract_python_from_pip_version(line), expected)

    def test_extract_python_from_virtual_env(self):
        for line, expected in [
            ('$ source ~/virtualenv/pypy/bin/activate\n', None),
            ('$ source ~/virtualenv/python2.7/bin/activate\n', 'python2.7'),
            ('$ source ~/virtualenv/python3.4/bin/activate\n', 'python3.4'),
            ('$ source ~/virtualenv/python3.6/bin/activate\n', 'python3.6'),
            ("      adding 'build/src.linux-x86_64-3.6/numpy/core/include/numpy/config.h' to sources.\n",
             None),
            ('    building data_files sources\n', None),
            ('Changing directory to /home/travis/build/Abjad/abjad/abjad/docs/source ...\n', None),
            ('    compiling C sources\n', None),
            ('    copying numpy/lib/_datasource.py -> build/lib.linux-x86_64-3.6/numpy/lib\n', None),
            ('    Cythonizing sources\n', None),
            ('Latest sources and executables are at ftp://ftp.info-zip.org/pub/infozip,\n', None),
            ('No source for /home/travis/build/Abjad/abjad/abjad/cli/test/test_score/test_score/__init__.py\n',
             None),
            ('      - `pip install .`       (from a git repo or downloaded source\n', None),
            ('Rebuilding documentation source ...\n', None),
            ('removed â€˜/etc/apt/sources.list.d/basho_riak.listâ€™\n', None),
            ('  Removing source in /tmp/pip-e9h6x4yy-build\n', None),
            ('    Running from numpy source directory.\n', None),
            ('+source builds/venv/bin/activate\n', None),
            ('│ │   │ ├─┬ source-map@0.4.4 \n', None),
            ('│ │   │   ├── source-map@0.5.7 \n', None),
            ('│ ├── source-map@0.5.7 \n', None),
            ('Subversion is open source software, see http://subversion.apache.org/\n', None),
            ('This is free software; see the source for copying conditions.  There is NO\n', None),
            ('This is free software; see the source for copying conditions. There is NO\n', None),
            ('\tin both source and object forms from any country, including\n', None),
        ]:
            result = None
            matched = VIRTUAL_ENV_REGEX.search(line)
            if matched:
                result = extract_python_from_virtual_env(matched)
            self.assertEqual(result, expected)


class TestEntireLogs(unittest.TestCase):

    def test1(self):
        log_path = 'logs/web2py-web2py-84151800'
        result = parse_log(log_path)
        expect = {'python2': {'default': 'pip==6.0.7', 'packages': []}}
        self.assertEqual(result, expect)

    def test2(self):
        log_path = 'logs/numpy-numpy-326894018'
        result = parse_log(log_path)
        expect = {'python3.6': {'default': 'pip==9.0.1',
                                'packages': ['virtualenv==14.0.6', 'cython==0.27.3', 'nose==1.3.7', 'pytz==2017.3']}}

        self.assertEqual(result, expect)

    def test3(self):
        log_path = 'logs/Abjad-abjad-327767621'
        result = parse_log(log_path)
        expect = {'python3.6': {'default': 'pip==9.0.1',
                                'packages': ['certifi==2017.11.5', 'chardet==3.0.4', 'coverage==4.4.2',
                                             'coveralls==1.2.0', 'docopt==0.6.2', 'idna==2.6', 'requests==2.18.4',
                                             'urllib3==1.22', 'ply==3.10', 'Jinja2==2.10', 'MarkupSafe==1.0',
                                             'PyPDF2==1.26.0', 'Pygments==2.2.0', 'alabaster==0.7.10', 'babel==2.5.1',
                                             'bleach==2.1.2', 'decorator==4.1.2', 'docutils==0.14',
                                             'entrypoints==0.2.3', 'html5lib==1.0.1', 'imagesize==0.7.1',
                                             'ipykernel==4.7.0', 'ipython==6.2.1', 'ipython-genutils==0.2.0',
                                             'ipywidgets==7.1.0', 'jedi==0.11.1', 'jsonschema==2.6.0', 'jupyter==1.0.0',
                                             'jupyter-client==5.2.1', 'jupyter-console==5.2.0', 'jupyter-core==4.4.0',
                                             'mistune==0.8.3', 'nbconvert==5.3.1', 'nbformat==4.4.0', 'notebook==5.2.2',
                                             'pandocfilters==1.4.2', 'parso==0.1.1', 'pexpect==4.3.1',
                                             'pickleshare==0.7.4', 'prompt-toolkit==1.0.15', 'ptyprocess==0.5.2',
                                             'python-dateutil==2.6.1', 'pytz==2017.3', 'pyzmq==16.0.3',
                                             'qtconsole==4.3.1', 'simplegeneric==0.8.1', 'snowballstemmer==1.2.1',
                                             'sphinx==1.6.6', 'sphinx-rtd-theme==0.2.4',
                                             'sphinxcontrib-websupport==1.0.1', 'terminado==0.8.1', 'testpath==0.3.1',
                                             'tornado==4.5.3', 'traitlets==4.3.2', 'wcwidth==0.1.7',
                                             'webencodings==0.5.1', 'widgetsnbextension==3.1.0', 'quicktions==1.5']}}

        self.assertEqual(result, expect)

    def test4(self):
        log_path = 'logs/Abjad-abjad-289716771'
        result = parse_log(log_path)
        expect = {'python3.4': {'default': 'pip==9.0.1',
                                'packages': ['certifi==2017.7.27.1', 'chardet==3.0.4', 'coverage==4.4.1',
                                             'coveralls==1.2.0', 'docopt==0.6.2', 'idna==2.6', 'requests==2.18.4',
                                             'urllib3==1.22', 'ply==3.10', 'Jinja2==2.9.6', 'MarkupSafe==1.0',
                                             'PyPDF2==1.26.0', 'Pygments==2.2.0', 'alabaster==0.7.10', 'babel==2.5.1',
                                             'backports-abc==0.5', 'bleach==2.1.1', 'decorator==4.1.2',
                                             'docutils==0.14', 'entrypoints==0.2.3', 'html5lib==1.0b10',
                                             'imagesize==0.7.1', 'ipykernel==4.6.1', 'ipython==6.2.1',
                                             'ipython-genutils==0.2.0', 'ipywidgets==7.0.2', 'jedi==0.11.0',
                                             'jsonschema==2.6.0', 'jupyter==1.0.0', 'jupyter-client==5.1.0',
                                             'jupyter-console==5.2.0', 'jupyter-core==4.3.0', 'mistune==0.7.4',
                                             'nbconvert==5.3.1', 'nbformat==4.4.0', 'notebook==5.2.0',
                                             'pandocfilters==1.4.2', 'parso==0.1.0', 'pexpect==4.2.1',
                                             'pickleshare==0.7.4', 'prompt-toolkit==1.0.15', 'ptyprocess==0.5.2',
                                             'python-dateutil==2.6.1', 'pytz==2017.2', 'pyzmq==16.0.2',
                                             'qtconsole==4.3.1', 'simplegeneric==0.8.1', 'snowballstemmer==1.2.1',
                                             'sphinx==1.6.4', 'sphinx-rtd-theme==0.2.4',
                                             'sphinxcontrib-websupport==1.0.1', 'terminado==0.6', 'testpath==0.3.1',
                                             'tornado==4.5.2', 'traitlets==4.3.2', 'typing==3.6.2', 'wcwidth==0.1.7',
                                             'webencodings==0.5.1', 'widgetsnbextension==3.0.4']}}

        self.assertEqual(result, expect)

    def test5(self):
        log_path = 'logs/tornadoweb-tornado-87216614'
        result = parse_log(log_path)
        expect = {'python3.4': {'default': 'pip==6.0.7',
                                'packages': ['codecov==1.5.1', 'coverage==4.0.1', 'requests==2.8.1']}}
        self.assertEqual(result, expect)

    def test6(self):
        log_path = 'logs/Abjad-abjad-375673938'
        result = parse_log(log_path)
        expect = {'python3.6': {'default': 'pip==9.0.1',
                                'packages': ['pip==10.0.1', 'coverage==4.5.1', 'ply==3.11', 'roman==2.0.0',
                                             'Jinja2==2.10', 'MarkupSafe==1.0', 'PyPDF2==1.26.0', 'Pygments==2.2.0',
                                             'Send2Trash==1.5.0', 'Unidecode==1.0.22', 'alabaster==0.7.10',
                                             'attrs==18.1.0', 'babel==2.5.3', 'backcall==0.1.0', 'bleach==2.1.3',
                                             'certifi==2018.4.16', 'chardet==3.0.4', 'decorator==4.3.0',
                                             'docutils==0.14', 'entrypoints==0.2.3', 'html5lib==1.0.1', 'idna==2.6',
                                             'imagesize==1.0.0', 'ipykernel==4.8.2', 'ipython==6.3.1',
                                             'ipython-genutils==0.2.0', 'ipywidgets==7.2.1', 'jedi==0.12.0',
                                             'jsonschema==2.6.0', 'jupyter==1.0.0', 'jupyter-client==5.2.3',
                                             'jupyter-console==5.2.0', 'jupyter-core==4.4.0', 'mistune==0.8.3',
                                             'more-itertools==4.1.0', 'mypy==0.600', 'nbconvert==5.3.1',
                                             'nbformat==4.4.0', 'notebook==5.4.1', 'packaging==17.1',
                                             'pandocfilters==1.4.2', 'parso==0.2.0', 'pexpect==4.5.0',
                                             'pickleshare==0.7.4', 'prompt-toolkit==1.0.15', 'ptyprocess==0.5.2',
                                             'pyparsing==2.2.0', 'pytest==3.5.1', 'python-dateutil==2.7.2',
                                             'pytz==2018.4', 'pyzmq==17.0.0', 'qtconsole==4.3.1', 'requests==2.18.4',
                                             'simplegeneric==0.8.1', 'snowballstemmer==1.2.1', 'sphinx==1.7.4',
                                             'sphinx-autodoc-typehints==1.3.0', 'sphinx-rtd-theme==0.3.1',
                                             'sphinxcontrib-websupport==1.0.1', 'terminado==0.8.1', 'testpath==0.3.1',
                                             'tornado==5.0.2', 'traitlets==4.3.2', 'typed-ast==1.1.0', 'uqbar==0.2.9',
                                             'urllib3==1.22', 'wcwidth==0.1.7', 'webencodings==0.5.1',
                                             'widgetsnbextension==3.2.1', 'coveralls==1.3.0', 'docopt==0.6.2']}}

        self.assertEqual(result, expect)

    def test_git1(self):
        """
        `linkenv-master` comes from git.
        `server_requirements.txt` contains:
            `-e git://github.com/ze-phyr-us/linkenv.git@ae463b3211cb8dcc8868e88176a1101733c83b6d#egg=linkenv-master`
        """
        log_path = 'logs/Cal-CS-61A-Staff-ok-71124742'
        result = parse_log(log_path)
        expect = {'python2.7': {'default': 'pip==6.0.7',
                                'packages': ['nose==1.3.3']}}
        self.assertEqual(result, expect)

    def test_whl1(self):
        """django_taggit_templatetags2 comes from a local .whl file"""
        log_path = 'logs/ccnmtl-dmt-287718761'
        result = parse_log(log_path)
        expect = {'python2.7': {'default': 'pip==9.0.1',
                                'packages': ['BeautifulSoup==3.2.1', 'CommonMark==0.7.4', 'Django==1.11.6',
                                             'Faker==0.8.5', 'GitPython==2.1.7', 'PyYAML==3.12',
                                             'SPARQLWrapper==1.8.0', 'XlsxWriter==1.0.0', 'amqp==2.2.2',
                                             'amqplib==1.0.2', 'anyjson==0.3.3', 'appdirs==1.4.3',
                                             'asn1crypto==0.23.0', 'astroid==1.5.3', 'backports-abc==0.5',
                                             'backports.functools-lru-cache==1.4',
                                             'backports.shutil-get-terminal-size==1.0.0',
                                             'backports.ssl-match-hostname==3.5.0.1', 'bandit==1.4.0',
                                             'billiard==3.5.0.3', 'bleach==2.1.1', 'boto==2.48.0',
                                             'ccnmtlsettings==1.3.0', 'celery==3.1.25', 'certifi==2017.7.27.1',
                                             'cffi==1.11.2', 'chardet==3.0.4', 'configparser==3.5.0',
                                             'contextlib2==0.5.5', 'coverage==4.4.1', 'cryptography==2.1.1',
                                             'cssselect==1.0.1', 'decorator==4.1.2', 'django-appconf==1.0.2',
                                             'django-bootstrap3==9.0.0', 'django-braces==1.11.0',
                                             'django-cacheds3storage==0.1.2', 'django-celery==3.2.1',
                                             'django-classy-tags==0.8.0', 'django-compressor==2.2',
                                             'django-crispy-forms==1.6.1', 'django-debug-toolbar==1.8',
                                             'django-emoji==2.2.0', 'django-extensions==1.9.1',
                                             'django-extra-views==0.9.0', 'django-filter==1.0.4',
                                             'django-ga-context==0.1.0', 'django-impersonate==1.1',
                                             'django-jenkins==0.110.0', 'django-markwhat==1.5.1',
                                             'django-oauth-toolkit==1.0.0', 'django-s3sign==0.1.4',
                                             'django-smoketest==1.1.0', 'django-smtp-ssl==1.0',
                                             'django-stagingcontext==0.1.0', 'django-staticmedia==0.2.2',
                                             'django-statsd-mozilla==0.4.0', 'django-storages==1.6.5',
                                             'django-storages-redux==1.3.3', 'django-taggit==0.22.1',
                                             'django-templatetag-sugar==1.0', 'django-waffle==0.12.0',
                                             'djangorestframework==3.7.0', 'djangowind==1.0.1', 'enum34==1.1.6',
                                             'factory-boy==2.9.2', 'flake8==3.4.1', 'freezegun==0.3.9',
                                             'future==0.16.0', 'fuzzywuzzy==0.15.1', 'gitdb2==2.0.3',
                                             'gunicorn==19.7.1', 'html5lib==0.999999999', 'idna==2.6',
                                             'ipaddress==1.0.18', 'ipdb==0.10.3', 'ipython==5.5.0',
                                             'ipython-genutils==0.2.0', 'isodate==0.6.0', 'isort==4.2.15',
                                             'kombu==3.0.37', 'lazy-object-proxy==1.3.1', 'ldap3==2.3',
                                             'librabbitmq==1.6.1', 'logilab-astng==0.24.3', 'logilab-common==1.4.1',
                                             'lxml==4.0.0', 'mccabe==0.6.1', 'mechanize==0.3.6',
                                             'ndg-httpsclient==0.4.3', 'oauthlib==2.0.4', 'packaging==16.8',
                                             'parse==1.8.2', 'parse-type==0.4.2', 'path.py==10.4', 'pathlib2==2.3.0',
                                             'pep8==1.7.0', 'pexpect==4.2.1', 'pickleshare==0.7.4',
                                             'prompt-toolkit==1.0.15', 'psycopg2==2.7.3.1', 'ptyprocess==0.5.2',
                                             'pyOpenSSL==17.3.0', 'pyasn1==0.3.7', 'pycodestyle==2.3.1',
                                             'pycparser==2.18', 'pyflakes==1.6.0', 'pygments==2.2.0', 'pylint==1.7.4',
                                             'pyparsing==2.2.0', 'python-dateutil==2.6.1', 'pytz==2017.2',
                                             'pyzmq==16.0.2', 'raven==6.2.1', 'rcssmin==1.0.6', 'rdflib==4.2.2',
                                             'recordtype==1.1', 'requests==2.18.4', 'rjsmin==1.0.12', 'scandir==1.6',
                                             'selenium==3.6.0', 'shortuuid==0.5.0', 'simpleduration==0.1.0',
                                             'simplegeneric==0.8.1', 'singledispatch==3.4.0.3', 'six==1.11.0',
                                             'smmap2==2.0.3', 'splinter==0.7.6', 'sqlparse==0.2.4', 'statsd==3.2.1',
                                             'stevedore==1.27.1', 'sure==1.4.7', 'tblib==1.3.2', 'tornado==4.5.2',
                                             'traitlets==4.3.2', 'unicodecsv==0.14.1', 'unidecode==0.4.21',
                                             'urllib3==1.22', 'urlparse2==1.1.1', 'versiontools==1.9.1', 'vine==1.1.4',
                                             'wcwidth==0.1.7', 'webencodings==0.5.1', 'websocket-client==0.44.0',
                                             'wrapt==1.10.11', 'wsgi-intercept==1.5.1',
                                             'wheel==0.29.0', 'BeautifulSoup==3.2.1', 'CommonMark==0.7.4',
                                             'Django==1.11.6', 'Faker==0.8.5', 'PyYAML==3.12', 'SPARQLWrapper==1.8.0',
                                             'XlsxWriter==1.0.0', 'amqp==2.2.2', 'amqplib==1.0.2', 'anyjson==0.3.3',
                                             'appdirs==1.4.3', 'astroid==1.5.3',
                                             'backports.shutil-get-terminal-size==1.0.0',
                                             'backports.ssl-match-hostname==3.5.0.1', 'bandit==1.4.0',
                                             'billiard==3.5.0.3', 'bleach==2.1.1', 'boto==2.48.0',
                                             'ccnmtlsettings==1.3.0', 'celery==3.1.25', 'certifi==2017.7.27.1',
                                             'chardet==3.0.4', 'configparser==3.5.0', 'contextlib2==0.5.5',
                                             'coverage==4.4.1', 'cssselect==1.0.1', 'decorator==4.1.2',
                                             'django-appconf==1.0.2', 'django-bootstrap3==9.0.0',
                                             'django-braces==1.11.0', 'django-cacheds3storage==0.1.2',
                                             'django-celery==3.2.1', 'django-classy-tags==0.8.0',
                                             'django-compressor==2.2', 'django-crispy-forms==1.6.1',
                                             'django-debug-toolbar==1.8', 'django-emoji==2.2.0',
                                             'django-extensions==1.9.1', 'django-extra-views==0.9.0',
                                             'django-filter==1.0.4', 'django-ga-context==0.1.0',
                                             'django-impersonate==1.1', 'django-jenkins==0.110.0',
                                             'django-markwhat==1.5.1', 'django-oauth-toolkit==1.0.0',
                                             'django-s3sign==0.1.4', 'django-smoketest==1.1.0',
                                             'django-smtp-ssl==1.0', 'django-stagingcontext==0.1.0',
                                             'django-staticmedia==0.2.2', 'django-statsd-mozilla==0.4.0',
                                             'django-storages==1.6.5', 'django-taggit==0.22.1',
                                             'django-templatetag-sugar==1.0', 'django-waffle==0.12.0',
                                             'djangorestframework==3.7.0', 'djangowind==1.0.1', 'enum34==1.1.6',
                                             'factory-boy==2.9.2', 'flake8==3.4.1', 'freezegun==0.3.9',
                                             'future==0.16.0', 'fuzzywuzzy==0.15.1', 'gunicorn==19.7.1',
                                             'html5lib==0.999999999', 'idna==2.6', 'ipaddress==1.0.18', 'ipdb==0.10.3',
                                             'ipython==5.5.0', 'ipython-genutils==0.2.0', 'isodate==0.6.0',
                                             'kombu==3.0.37', 'lazy-object-proxy==1.3.1', 'ldap3==2.3',
                                             'librabbitmq==1.6.1', 'logilab-astng==0.24.3', 'logilab-common==1.4.1',
                                             'lxml==4.0.0', 'mccabe==0.6.1', 'mechanize==0.3.6',
                                             'ndg-httpsclient==0.4.3', 'oauthlib==2.0.4', 'parse==1.8.2',
                                             'parse-type==0.4.2', 'path.py==10.4', 'pathlib2==2.3.0', 'pbr==3.1.1',
                                             'pep8==1.7.0', 'pexpect==4.2.1', 'pickleshare==0.7.4',
                                             'prompt-toolkit==1.0.15', 'psycopg2==2.7.3.1', 'ptyprocess==0.5.2',
                                             'pyOpenSSL==17.3.0', 'pyasn1==0.3.7', 'pycodestyle==2.3.1',
                                             'pyflakes==1.6.0', 'pygments==2.2.0', 'pylint==1.7.4', 'pyparsing==2.2.0',
                                             'python-dateutil==2.6.1', 'pytz==2017.2', 'pyzmq==16.0.2', 'raven==6.2.1',
                                             'rcssmin==1.0.6', 'rdflib==4.2.2', 'recordtype==1.1', 'requests==2.18.4',
                                             'rjsmin==1.0.12', 'scandir==1.6', 'shortuuid==0.5.0',
                                             'simpleduration==0.1.0', 'simplegeneric==0.8.1', 'six==1.11.0',
                                             'splinter==0.7.6', 'sqlparse==0.2.4', 'statsd==3.2.1', 'stevedore==1.27.1',
                                             'sure==1.4.7', 'tblib==1.3.2', 'tornado==4.5.2', 'traitlets==4.3.2',
                                             'unicodecsv==0.14.1', 'urllib3==1.22', 'urlparse2==1.1.1',
                                             'versiontools==1.9.1', 'vine==1.1.4', 'wcwidth==0.1.7',
                                             'webencodings==0.5.1', 'websocket-client==0.44.0',
                                             'wrapt==1.10.11', 'wsgi-intercept==1.5.1']}}
        self.assertEqual(result, expect)


if __name__ == '__main__':
    unittest.main()
