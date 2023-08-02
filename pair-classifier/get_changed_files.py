import time
import json
import sys
import re
import subprocess
from builtins import Exception, len, str
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from threading import RLock

from bugswarm.common import log
from bs4 import BeautifulSoup

lock = RLock()
SUPPRESS_THREAD_EXCEPTIONS = False


def get_changed_files_metrics(soup):
    """
    Returns the metrics of added, deleted, and modified files
    :param soup: beautifulsoup4 object for parsing
    :return metrics: returns a dictionary of metrics for changed files
    """
    metrics = {
        'num_of_changed_files': 0,
        'changes': 0,
        'additions': 0,
        'deletions': 0
    }

    list_of_metrics = []
    div = soup.select_one('div.toc-diff-stats')
    if div is None:
        return metrics
    button = div.select_one('button.btn-link.js-details-target')
    if button:
        result = re.search(r'[0-9]+', button.string)
        list_of_metrics.append(int(result.group()))

    # num of changed files is part of the <strong> tag if the number is large
    strong_list = div.find_all('strong')
    for strong in strong_list:
        # matches numbers similar to 1,000, 10,000, etc & then we strip out the comma
        # as our previous data is only numbers
        result = re.search(r'([0-9]+),?([0-9]+)?', strong.string)
        if ',' in result.group():
            result = result.group().replace(',', '')
            list_of_metrics.append(int(result))
        else:
            list_of_metrics.append(int(result.group()))

    if len(list_of_metrics) == 3:
        metrics['num_of_changed_files'] = list_of_metrics[0]
        metrics['additions'] = list_of_metrics[1]
        metrics['deletions'] = list_of_metrics[2]
        metrics['changes'] = list_of_metrics[1] + list_of_metrics[2]
    return metrics


# Returns the count and names of modified files
def get_changed_files(soup):
    links = soup.select('div#files div.file-info a')
    count = len(links)
    changed_files = [link['title'] for link in links]

    # If the full list of links can't be loaded for some reason, fall back to "table of contents" method
    # (Required to pass test_mozilla_14 to 20, test_mozilla_4 to 5, and test_safari_1)
    toc = soup.select('div.table-of-contents')
    toc_changed_files = []
    for link in toc:
        for a in link.find_all('a', href=lambda href: href and '#diff' in href):
            if a.find('span') is None:
                toc_changed_files.append(a.text)

    if toc_changed_files and len(toc_changed_files) != len(changed_files):
        return len(toc_changed_files), toc_changed_files

    return count, changed_files


def get_github_url(failed_sha, passed_sha, repo):
    """
    Creates the github diff url for a given failed_sha, passed_sha, and repo
    """
    # Generates the 2-dot diff url for each artifact
    url = 'https://github.com/{}/compare/{}..{}'.format(repo, failed_sha, passed_sha)
    return url


def gather_info(url):
    tag_info = {
        'url': url
    }

    command = 'node get_github_html.js {}'.format(url)
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=True)
    try:
        stdout, stderr = process.communicate(None, timeout=7200)
        stdout = stdout.decode('utf-8').strip()
        stderr = stderr.decode('utf-8').strip()
        ok = process.returncode == 0
    except subprocess.TimeoutExpired:
        stdout = ''
        stderr = 'subprocess.TimeoutExpired'
        ok = False

    if ok:
        source = stdout
        soup = BeautifulSoup(source, 'lxml')

        metrics = get_changed_files_metrics(soup)
        tag_info['metrics'] = metrics

        count, changed_files = get_changed_files(soup)
        if count == 0:
            tag_info['changed_paths'] = ['NONE FOUND']
        else:
            tag_info['changed_paths'] = changed_files

        if count != tag_info['metrics']['num_of_changed_files']:
            tag_info['error_found'] = 'ERROR, MISMATCH IN COUNT'
        else:
            tag_info['error_found'] = 'NONE'
    else:
        tag_info['num_of_changed_files'] = -1
        tag_info['changed_paths'] = ['ERROR, CANNOT FULFILL REQUEST']
        tag_info['error_found'] = 'ERROR, {}'.format(stderr)
        tag_info['metrics'] = {
            'num_of_changed_files': 0,
            'changes': 0,
            'additions': 0,
            'deletions': 0
        }
    return tag_info


def main():
    all_info = {}
    url_list = {}

    # file with image tags and their urls, separated by tabs
    with open('url_list.tsv', 'r') as f_tags:
        for line in f_tags:
            line_info = line.split('\t')

            image_tag = line_info[0]
            repo = line_info[1]
            failed_sha = line_info[2]
            passed_sha = line_info[3]

            url = get_github_url(failed_sha, passed_sha, repo)

            url_list[image_tag] = url

    t_start = time.time()

    # format: {'image_tag': {'url': url, 'num_files': num_files, 'changed_paths': changed_paths}, ...}
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_tag = {executor.submit(gather_info,
                                         url_list[image_tag]): image_tag for image_tag in url_list.keys()}
        for future in as_completed(future_to_tag):
            try:
                the_info = future.result()
                with lock:
                    if image_tag not in all_info:
                        all_info[image_tag] = the_info
            except Exception as e:
                if not SUPPRESS_THREAD_EXCEPTIONS:
                    log.error(e)
                    raise

    t_stop = time.time()
    total_time = t_stop - t_start
    print('total time:', total_time)

    with open('changed_paths_info.tsv', 'w') as f:
        # write information from all_info list into the file
        for tag in all_info:
            info = all_info[tag]
            f.write(
                '{}\t{}\t{}\t{}\t{}\t\n\n'.format(tag, str(info['num_changed_files']), str(info['error_found']),
                                                  str(info['url']), str(info['changed_paths']))
            )

    with open('artifact_info.json', 'w') as file:
        json.dump(all_info, file)

    print('total amount:', len(all_info))


if __name__ == '__main__':
    sys.exit(main())
