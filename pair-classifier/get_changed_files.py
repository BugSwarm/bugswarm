import time
import json
import sys
from builtins import Exception, len, str
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from threading import RLock

from bugswarm.common import log
from bs4 import BeautifulSoup
from proxy_requests import ProxyRequests

lock = RLock()
SUPPRESS_THREAD_EXCEPTIONS = False


# Returns the count and names of modified files
def get_changed_files(soup):
    links = soup.find_all("div", class_="details-collapse table-of-contents js-details-container Details")
    count = 0
    changed_files = []
    for link in links:
        for a in link.find_all('a', href=lambda href: href and '#diff' in href):

            if a.find('span') is None:
                changed_files.append(a.text)
                count += 1

    return count, changed_files


# Returns the number of modified files used against the threshold in testing
def get_num_changed_files(soup):
    links = soup.find_all("div", class_="toc-diff-stats")
    current_num = 0
    for link in links:
        # default: searching for button (small amt of changed files)
        searching = link.find('button')
        if searching is None:
            # if large amt of changed files, use 'strong' tag
            searching = link.find('strong')
        num_started = False
        # parses text to get integer type of number of changed files
        for letter in searching.text:
            if num_started is False and letter.isdigit():
                current_num = int(letter)
                num_started = True
            elif num_started is True and letter.isdigit():
                current_num = current_num * 10
                current_num = current_num + int(letter)
            elif num_started is True and letter == ' ':
                break
    return current_num


def get_github_url(failed_sha, passed_sha, repo):
    """
    Creates the github diff url for a given failed_sha, passed_sha, and repo
    """
    # Generates the 2-dot diff url for each artifact
    url = 'https://github.com/{}/compare/{}..{}'.format(repo, failed_sha, passed_sha)
    return url


def _thread_main(url):
    list_of_user_agents = ['Mozilla/5.0', 'AppleWebKit/537.36', 'Chrome/79.0.3945.88', 'Safari/537.36']
    stat_code = 0
    tag_info = {
        'url': url
    }

    try_count = 0
    # continue attempting up to 4 proxies
    for user_agent in list_of_user_agents:
        if stat_code != 200:
            try_count += 1

            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp,image/apng, */*;\
                q = 0.8",
                "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q = 0.9"
            }

            r = ProxyRequests(url)
            r.set_headers(headers)
            r.get_with_headers()
            source = r.get_raw()
            stat_code = r.get_status_code()

    if try_count == len(list_of_user_agents):
        tag_info['num_changed_files'] = -1
        tag_info['changed_paths'] = ['ERROR, CANNOT FULFILL REQUEST']
        tag_info['error_found'] = 'ERROR, TOO MANY PROXY ATTEMPTS'
        return tag_info

    # proxy successful, continue reading the page
    if stat_code == 200:
        soup = BeautifulSoup(source, 'lxml')
        # get changed files info
        read_count = get_num_changed_files(soup)
        tag_info['num_changed_files'] = read_count

        count, changed_files = get_changed_files(soup)
        if count == 0:
            tag_info['changed_paths'] = ['NONE FOUND']
        else:
            tag_info['changed_paths'] = changed_files

        if count != read_count:
            tag_info['error_found'] = 'ERROR, MISMATCH IN COUNT'
        else:
            tag_info['error_found'] = 'NONE'
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
        future_to_tag = {executor.submit(_thread_main,
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
    print("total time:", total_time)

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

    print("total amount:", len(all_info))


if __name__ == "__main__":
    sys.exit(main())
