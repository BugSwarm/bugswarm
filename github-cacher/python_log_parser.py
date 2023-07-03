import re
from collections import defaultdict
from operator import itemgetter

# https://stackoverflow.com/a/14693789/
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Regular expression for extract_python_from_virtual_env()
VIRTUAL_ENV_REGEX = re.compile(r'source.*(python[0-9\.]+)/bin/activate')

# Regular expression for extract_packages()
EXTRACT_PACKAGES_REGEX = re.compile(r'^Successfully installed (.+)(?:$|\n)')

# Source types identified by determine_source()
PACKAGE_SOURCE_ALREADY_SATISFIED = 0
PACKAGE_SOURCE_GIT = 1
PACKAGE_SOURCE_INDEX = 2
PACKAGE_SOURCE_WHL = 3

# Regular expression for determine_source()
DETERMINE_SOURCE_REGEX = re.compile(
    r'\bRequirement already satisfied \([^\(\)]+\): ([\w\-\=\.\<\>\!\~]+) in\b|'
    r'\bObtaining ([\w\-\=\.\<\>\!\~]+) from\b|'
    r'\bCollecting ([\w\-\=\.\<\>\!\~]+)\b|'
    r'\bProcessing ([\w\-\=\.\<\>\!\~/]+)\b'
)


def extract_python_from_pip_version(line):
    """
    Get python and pip version from the line after "pip --version"
    e.g.
        pip 6.0.7 from /home/travis/virtualenv/python3.4.2/lib/python3.4/site-packages (python 3.4)
        pip 9.0.1 from /home/travis/virtualenv/python3.6.3/lib/python3.6/site-packages (python 3.6)
    """
    python_regex = r'(python[0-9\.]*)/site-packages'
    searched = re.search(python_regex, line)
    if searched:
        python_version = searched.groups()[0]
    else:
        python_version = ''

    pip_regex = r'pip ([0-9\.]+) from'
    searched = re.search(pip_regex, line)
    if searched:
        pip_version = 'pip=={}'.format(searched.groups()[0])
    else:
        pip_version = ''

    return python_version, pip_version


def extract_python_from_virtual_env(matched):
    """
    Get python version from source virtualenv command
    e.g.
        $ source ~/virtualenv/python3.6/bin/activate
    """
    return matched.groups()[0]


def split_package_and_version(package_argum):
    """
    Split package and version in the "Successfully installed" line
    This function does not do version validation, so you may get package-0.1.1+dev, package-9.0.1+build, etc
    """
    package = version = None
    if '-' in package_argum:
        package, version = package_argum.rsplit('-', 1)
        # if any(x.isalpha() for x in version):
        #     return package, None
    return package, version


def remove_version_specifier(spec):
    """
    Remove version specifiers in a string. Also replace '_' with '-'
    e.g.
        'nose==1.3.3' -> 'nose'
        'ngshare' -> 'ngshare'
        'sphinx_autodoc_typehints==1.3.0' -> 'sphinx-autodoc-typehints'
    asciimoo-searx-361196589: can have '.' in package name
        plone.testing==5.0.0 zope.testrunner==4.5.1
    Ref: https://www.python.org/dev/peps/pep-0440/#version-specifiers
    Ref: https://www.python.org/dev/peps/pep-0508/
        "'<=' | '<' | '!=' | '==' | '>=' | '>' | '~=' | '==='"
    Ref: https://packaging.python.org/tutorials/packaging-projects/#configuring-metadata
        "only contains letters, numbers, _ , and -."
    """
    matched = re.match(r'^([\w\-\.]+)(?:[\<\>]=?|[\!\=\~]=|===|$)', spec)
    if matched:
        return matched.groups()[0].replace('_', '-')
    else:
        return spec


def extract_packages(matched, package_source):
    """
    Extract packages installed in the "Successfully installed" line
    e.g.
        Successfully installed Abjad Jinja2-2.10 MarkupSafe-1.0 PyPDF2-1.26.0 Pygments-2.2.0 alabaster-0.7.10 \
        babel-2.5.1 bleach-2.1.2 decorator-4.1.2 docutils-0.14 entrypoints-0.2.3 html5lib-1.0.1 imagesize-0.7.1 \
        ipykernel-4.7.0 ipython-6.2.1 ipython-genutils-0.2.0 ipywidgets-7.1.0 jedi-0.11.1 jsonschema-2.6.0 \
        jupyter-1.0.0 jupyter-client-5.2.1 jupyter-console-5.2.0 jupyter-core-4.4.0 mistune-0.8.3 nbconvert-5.3.1 \
        nbformat-4.4.0 notebook-5.2.2 pandocfilters-1.4.2 parso-0.1.1 pexpect-4.3.1 pickleshare-0.7.4 \
        prompt-toolkit-1.0.15 ....
    """
    result = []
    package_list = matched.groups()[0].split(' ')
    for package in package_list:
        package, version = split_package_and_version(package)
        if not version or not package:
            continue
        else:
            source = package_source.get(package)
            if source is None:
                continue
            # The following line is recommended when developing
            # assert source == PACKAGE_SOURCE_INDEX
            result.append('{}=={}'.format(package, version))
    return result


def determine_source(matched):
    """
    Determine the source of a package from pip output
    Note that the strings may not be always be at the start of the line
    e.g. (Cal-CS-61A-Staff-ok-71124742, ccnmtl-dmt-287718761, pydanny-cookiecutter-django-83499747)
        Requirement already satisfied (use --upgrade to upgrade): docutils==0.11 in /home/travis/virtualenv/...
        Collecting nose==1.3.3 (from -r server_requirements.txt (line 17))
        Obtaining linkenv-master from git+git://github.com/ze-phyr-us/linkenv.git@ae463b3211cb8dcc8868e88176...
        Collecting Django==1.11.6 (from -r requirements.txt (line 1))
        Processing ./requirements/src/django_taggit_templatetags2-1.4.1.ccnmtl-py2.py3-none-any.whl
        41% |█████████████▍                  Collecting isodate==0.6.0 (from -r requirements.txt (line 40))
        Collecting git+git://github.com/mverteuil/pytest-ipdb.git (from -r requirements.txt (line 13))
    """
    source, spec = next(filter(itemgetter(1), enumerate(matched.groups())))
    return remove_version_specifier(spec), source


def parse_log(log_path):
    pip_install_list = defaultdict(dict)
    python_version = 'python2'
    package_source = {}
    if 1:   # TODO: tmp code
        global log_path_
        log_path_ = log_path
    with open(log_path) as file:
        lines = list(map(lambda x: ANSI_ESCAPE.sub('', x), file.readlines()))
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            line = line.strip()
            if 'pip --version' in line:
                py_version, pip_version = extract_python_from_pip_version(lines[idx + 1])
                python_version = py_version if py_version else python_version
                if pip_version:
                    pip_install_list[python_version]['default'] = pip_version
                idx += 2
                continue
            matched = VIRTUAL_ENV_REGEX.search(line)
            if matched:
                result = extract_python_from_virtual_env(matched)
                python_version = result if result is not None else python_version
                idx += 1
                continue
            matched = EXTRACT_PACKAGES_REGEX.search(line)
            if matched:
                package_list = pip_install_list[python_version].get('packages', [])
                package_list += extract_packages(matched, package_source)
                pip_install_list[python_version]['packages'] = package_list
                idx += 1
                continue
            matched = DETERMINE_SOURCE_REGEX.search(line)
            if matched:
                name, source = determine_source(matched)
                package_source[name] = source
                idx += 1
                continue
            idx += 1
    return pip_install_list
