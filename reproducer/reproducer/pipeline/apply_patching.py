import subprocess

from bugswarm.common import log
from bs4 import BeautifulSoup

_LIST_OF_DEPRECATED_URLS = ['http://repo.maven.apache.org/maven2', 'http://repo1.maven.org/maven2']
_REPLACEMENT_URL = 'http://insecure.repo1.maven.org/maven2'


def modify_pom_file(search_dir):
    pom_modified = False
    file_path_result = []

    for deprecated_url in _LIST_OF_DEPRECATED_URLS:
        grep_for_pom_command = 'grep -rl {} {}'.format(deprecated_url, search_dir)
        _, stdout, stderr, ok = _run_command(grep_for_pom_command)
        if ok:
            file_path_result += stdout.splitlines()
    for file_path in file_path_result:
        try:
            soup = BeautifulSoup(open(file_path), 'lxml-xml')

            list_of_repo_urls = soup.find_all('url')
            for url in list_of_repo_urls:
                stripped_url = url.getText().strip()
                if stripped_url in _LIST_OF_DEPRECATED_URLS:
                    url.string.replace_with(_REPLACEMENT_URL)
                    pom_modified = True
            # Overwrite the existing POM with the updated POM.
            if pom_modified:
                with open(file_path, 'w') as f:
                    f.write(soup.prettify())
                log.info('Modified pom.xml file.')
            else:
                log.info('Did not modify pom.xml file.')
        except IOError:
            log.error('Error reading file: ', file_path_result)


def _run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    return process, stdout, stderr, ok
