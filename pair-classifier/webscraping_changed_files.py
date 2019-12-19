import bs4 as bs

import time
import concurrent
import concurrent.futures

import json

from threading import RLock

from proxy_requests import ProxyRequests


lock = RLock()


def get_changed_files(soup):
    links = soup.find_all("div", class_="details-collapse table-of-contents js-details-container Details")
    count = 0
    changed_files = []
    for link in links:
        for a in link.find_all('a', href=lambda href: href and '#diff' in href):

            span = a.find('span')
            if span is None:
                changed_files.append(a.text)
                count = count + 1

    return count, changed_files


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


def thread_get_info(url):
    stat_code = 0
    this_tag_info = {}
    this_tag_info['url'] = url

    try_count = 0
    # continue collecting proxies for up to 10 tries
    while stat_code != 200:
        try_count += 1
        if try_count > 10:
            this_tag_info['num_changed_files'] = -1
            this_tag_info['changed_paths'] = ['NONE FOUND']
            this_tag_info['error_found'] = 'ERROR, TOO MANY PROXY ATTEMPTS'
            return this_tag_info

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html, application/xhtml+xml, application/xml; q = 0.9, image/webp,image/apng, */*;\
            q = 0.8, application/signed-exchange; v = b3",
            "Accept-Encoding": "gzip, deflate, br", "Accept-Language": "en-US,en; q = 0.9"}

        r = ProxyRequests(url)
        r.set_headers(headers)
        r.get_with_headers()
        source = r.get_raw()
        stat_code = r.get_status_code()

    # proxy successful, continue reading the page
    if stat_code == 200:
        soup = bs.BeautifulSoup(source, 'lxml')

        # get changed files info
        read_count = get_num_changed_files(soup)
        this_tag_info['num_changed_files'] = read_count

        count, changed_files = get_changed_files(soup)
        if count == 0:
            this_tag_info['changed_paths'] = ['NONE FOUND']
        else:
            this_tag_info['changed_paths'] = changed_files

        if count != read_count:
            this_tag_info['error_found'] = 'ERROR, MISMATCH IN COUNT'
        else:
            this_tag_info['error_found'] = 'OK'

    return this_tag_info


def main():
    all_info = {}
    url_list = {}

    # file with image tags and their urls, separated by tabs
    with open("url_list.tsv", "r") as f_tags:
        for line in f_tags:
            line_info = line.split('\t')

            this_img_tag = line_info[0]
            this_repo = line_info[1]
            this_failed_sha = line_info[2]
            this_passed_sha = line_info[3]

            this_url = get_github_url(this_failed_sha, this_passed_sha, this_repo)

            url_list[this_img_tag] = this_url

        t_start = time.time()

        # format: {'image_tag': {'url': url, 'num_files': num_files, 'changed_paths': changed_paths}, ...}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            for this_tag in url_list.keys():
                future = executor.submit(thread_get_info, url_list[this_tag])
                the_info = future.result()

                with lock:
                    # critical section
                    if this_tag not in all_info:
                        all_info[this_tag] = the_info
                    # end critical section

        t_stop = time.time()
        total_time = t_stop - t_start
        print("total time:", total_time)

    with open("changed_paths_info.tsv", "w") as f:
        # write information from all_info list into the file
        for the_tag in all_info:
            the_info = all_info[the_tag]
            f.write(
                the_tag + '\t' + (str)(the_info['num_changed_files']) + '\t' + (str)(the_info['error_found']) + '\t' +
                (str)(the_info['url']) + '\t' + (str)(the_info['changed_paths']) + '\t' + '\n\n'
            )

    with open('artifact_info.json', 'w') as file:
        json.dump(all_info, file)

    print("total amount:", len(all_info))


if __name__ == "__main__":
    main()
