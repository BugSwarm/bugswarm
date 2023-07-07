#!/usr/bin/env python

import os
import sys
import subprocess


cacher_directory = os.environ.get('BUGSWARM_CACHER_PATH', '/home/github/cacher')
curl_path = '/usr/bin/curl_original'


def run_command(command):
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    ok = process.returncode == 0
    return process, stdout, stderr, ok


if __name__ == '__main__':
    curl_command = ' '.join(sys.argv[1:])
    _, out, err, ok = run_command('{} {} 2>&1'.format(curl_path, curl_command))
    print(out)
