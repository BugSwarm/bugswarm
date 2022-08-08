import subprocess
import os
import fileinput
import re

from bugswarm.common import log
from bs4 import BeautifulSoup

_LIST_OF_DEPRECATED_URLS = ['http://repo.maven.apache.org/maven2', 'http://repo1.maven.org/maven2']
_REPLACEMENT_URL = 'http://insecure.repo1.maven.org/maven2'


# TODO: Verify this function is up to date
def modify_deprecated_links(search_dir):
    file_path_result = []

    for deprecated_url in _LIST_OF_DEPRECATED_URLS:
        grep_for_pom_command = 'grep -rl {} {}'.format(deprecated_url, search_dir)
        _, stdout, stderr, ok = _run_command(grep_for_pom_command)
        if ok:
            file_path_result += stdout.splitlines()

    for file_path in file_path_result:
        file_modified = False
        if os.path.isfile(file_path):
            extension_type = file_path.split('.')[-1]
            if extension_type == 'xml' or extension_type == 'pom':
                try:
                    soup = BeautifulSoup(open(file_path), 'lxml-xml')

                    list_of_repo_urls = soup.find_all('url')
                    for url in list_of_repo_urls:
                        stripped_url = url.getText().strip()
                        if stripped_url in _LIST_OF_DEPRECATED_URLS:
                            url.string.replace_with(_REPLACEMENT_URL)
                            file_modified = True
                    # Overwrite the existing POM with the updated POM.
                    if file_modified:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(soup.prettify())
                        log.info('Modified {} file.'.format(file_path))
                except IOError:
                    log.error('Error reading file: ', file_path)
            else:
                # square-retrofit-104397133 is an edge case example that contains a .js file that contains the
                # deprecated link and is executed at some point during the build causing the HTTPs 501 Error
                with fileinput.input(file_path, inplace=True) as f:
                    for line in f:
                        match_obj_found = False
                        for url in _LIST_OF_DEPRECATED_URLS:
                            match_obj = re.search(url, line)
                            if match_obj:
                                print(line.replace(url, _REPLACEMENT_URL).strip('\n'))
                                file_modified = True
                                match_obj_found = True
                                continue
                        if match_obj_found:
                            continue
                        else:
                            print(line.strip('\n'))
                if file_modified:
                    log.info('Modified {} file.'.format(file_path))
        else:
            log.error('Error opening file: ', file_path)


def _run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    return process, stdout, stderr, ok
