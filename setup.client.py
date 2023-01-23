import os
from datetime import datetime

from setuptools import find_packages, setup

today = datetime.utcnow()
version = f'{today.year}.{today.month:02}.{today.day:02}'


def bs_common_version():
    in_ci = bool(os.environ.get('CI'))

    if in_ci:
        if os.environ.get('BSC_UPDATED') == 'true':
            # There was a new version of bugswarm-common in this same CI run; use today's date as the version
            return f'=={version}'

        # Otherwise, get latest version from PyPI API
        import requests
        response = requests.get('https://pypi.org/pypi/bugswarm-common/json')
        response.raise_for_status()
        return '=={}'.format(response.json()['version'])

    # Use the value of the BUGSWARM_COMMON environment variable, if present
    if 'BUGSWARM_COMMON' in os.environ:
        return '=={}'.format(os.environ['BUGSWARM_COMMON'])

    # Don't pin bugswarm-common
    return ''


setup(
    name='bugswarm-client',
    version=version,
    url='https://github.com/BugSwarm/bugswarm',
    author='BugSwarm',
    author_email='dev.bugswarm@gmail.com',

    description='The official command line client for the BugSwarm artifact dataset',
    long_description='The official command line client for the BugSwarm artifact dataset',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: BSD License',
    ],
    zip_safe=False,
    packages=find_packages(include=['bugswarm.client*']),
    namespace_packages=[
        'bugswarm',
    ],
    install_requires=[
        'click==6.7',
        'requests>=2.20.0',
        'bugswarm-common' + bs_common_version(),
    ],
    entry_points={
        'console_scripts': [
            'bugswarm = bugswarm.client.bugswarm:cli',
        ],
    },
)
