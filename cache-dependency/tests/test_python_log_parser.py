import sys
import unittest

sys.path.append('..')
from python_log_parser import parse_log  # noqa: E402


class TestStringMethods(unittest.TestCase):

    def test1(self):
        log_path = 'logs/web2py-web2py-84151800'
        result = parse_log(log_path)
        expect = {'python2': {'default': 'pip==6.0.7', 'packages': []}}
        assert result == expect

    def test2(self):
        log_path = 'logs/numpy-numpy-326894018'
        result = parse_log(log_path)
        expect = {'python3.6': {'default': 'pip==9.0.1',
                                'packages': ['virtualenv==14.0.6', 'cython==0.27.3', 'nose==1.3.7', 'pytz==2017.3',
                                             'numpy==1.15.0.dev0+5e346d5']}}

        assert result == expect

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

        assert result == expect

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

        assert result == expect

    def test5(self):
        log_path = 'logs/tornadoweb-tornado-87216614'
        result = parse_log(log_path)
        expect = {'python3.4': {'default': 'pip==6.0.7',
                                'packages': ['codecov==1.5.1', 'coverage==4.0.1', 'requests==2.8.1']}}
        assert result == expect

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

        assert result == expect


if __name__ == '__main__':
    unittest.main()
