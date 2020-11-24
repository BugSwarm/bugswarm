import re
from collections import defaultdict


def extract_python_from_pip_version(line):
    # pip 6.0.7 from /home/travis/virtualenv/python3.4.2/lib/python3.4/site-packages (python 3.4)
    # pip 9.0.1 from /home/travis/virtualenv/python3.6.3/lib/python3.6/site-packages (python 3.6)
    regex = r'(?<!pip from)python[0-9\.]*(?=/site-packages)'
    matches = re.finditer(regex, line)
    for match in matches:
        return match.group(0)
    return None


def extract_python_from_virtual_env(line):
    # [0K$ source ~/virtualenv/python3.6/bin/activate
    regex = r'source.*python[0-9\.]+(?!bin/activate)'
    matches = re.findall(regex, line)
    if matches:
        match = matches[0]
        python_regex = r'python[0-9\.]*'
        py_matches = re.findall(python_regex, match)
        if py_matches:
            return py_matches[0]
    return None


def split_package_and_version(package_argum):
    # TODO: need version validation, e.g. package-0.1.1+dev package-9.0.1+build, etc
    # version_regex = r''
    package = version = None
    if '-' in package_argum:
        package, version = package_argum.rsplit('-', 1)
        # if any(x.isalpha() for x in version):
        #     return package, None
    return package, version


def extract_packages(line):
    # Successfully installed Abjad Jinja2-2.10 MarkupSafe-1.0 PyPDF2-1.26.0 Pygments-2.2.0 alabaster-0.7.10
    # babel-2.5.1 bleach-2.1.2 decorator-4.1.2 docutils-0.14 entrypoints-0.2.3 html5lib-1.0.1 imagesize-0.7.1
    # ipykernel-4.7.0 ipython-6.2.1 ipython-genutils-0.2.0 ipywidgets-7.1.0 jedi-0.11.1 jsonschema-2.6.0 jupyter-1.0.0
    # jupyter-client-5.2.1 jupyter-console-5.2.0 jupyter-core-4.4.0 mistune-0.8.3 nbconvert-5.3.1 nbformat-4.4.0
    # notebook-5.2.2 pandocfilters-1.4.2 parso-0.1.1 pexpect-4.3.1 pickleshare-0.7.4 prompt-toolkit-1.0.15 ....
    result = []
    package_list = line.split(' ')[2:]
    for package in package_list:
        package, version = split_package_and_version(package)
        if not version or not package:
            continue
        else:
            result.append('{}=={}'.format(package, version))
    return result


def parse_log(log_path):
    pip_install_list = defaultdict(list)
    python_version = 'python2'
    with open(log_path) as file:
        lines = file.readlines()
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            line = line.strip()
            if 'pip --version' in line:
                result = extract_python_from_pip_version(lines[idx + 1])
                python_version = result if result is not None else python_version
                idx += 1
            elif 'source' in line:
                result = extract_python_from_virtual_env(lines[idx])
                python_version = result if result is not None else python_version
            elif line.startswith('Successfully installed'):
                pip_install_list[python_version] += extract_packages(line)
            idx += 1
    return pip_install_list
