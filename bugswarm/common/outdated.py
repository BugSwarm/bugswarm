import re
import subprocess

from distutils.version import StrictVersion
from typing import List

import requests

from bugswarm.common import log
from .shell_wrapper import ShellWrapper


def check_package_outdated(package: str):
    """
    Checks if the installed version of a package is older than the latest non-prerelease version available on PyPI.
    If so, prints a message the asks the user to consider upgrading.

    The package must be available on PyPI and must have always used a version numbering scheme that can be parsed by
    distutils.version.StrictVersion.

    This function is meant to be used for packages in the 'bugswarm' namespace, which meet the above requirements, and
    therefore is not guaranteed to work for packages outside that namespace.

    :param package: The name of the package to check.
    """
    if not isinstance(package, str):
        raise TypeError

    try:
        installed = _get_installed_version(package)
        latest = _get_latest_version(package)
        if latest > installed:
            # A newer, non-prerelease version is available.
            log.info('You are using {} version {}, but version {} is available.'.format(package, installed, latest))
            log.info("You should consider upgrading via the 'pip3 install --upgrade {}' command.".format(package))
    except Exception as e:
        log.error('Encountered an error while checking if {} can be updated: {}'.format(package, e))


def _get_installed_version(package: str) -> StrictVersion:
    if not isinstance(package, str):
        raise TypeError

    stdout, _, returncode = ShellWrapper.run_commands('pip show {}'.format(package), stdout=subprocess.PIPE, shell=True)
    version_string = re.search(r'Version: (.*)', stdout, re.IGNORECASE).group(1)
    return StrictVersion(version_string)


def _get_latest_version(package: str) -> StrictVersion:
    if not isinstance(package, str):
        raise TypeError

    return sorted(_list_non_prerelease_versions(package), reverse=True)[0]


def _list_non_prerelease_versions(package: str) -> List[StrictVersion]:
    """
    Returns a list of StrictVersion objects representing the available, non-prerelease versions of a package, if the
    package is available on PyPI. Otherwise, returns an empty list.
    """
    url = _pypi_api_url(package)
    resp = requests.get(url)
    all_versions = list(map(StrictVersion, resp.json()['releases'].keys()))
    non_prerelease_versions = [v for v in all_versions if not v.prerelease]
    return non_prerelease_versions


def _pypi_api_url(package: str):
    return 'https://pypi.org/pypi/{}/json'.format(package)
