#!/usr/bin/env python

import os
import sys
import subprocess
import argparse
import re
import shutil
import json
import time
import uuid
import shlex
import logging

wget_path = '/usr/bin/wget_original'
logging_level = logging.INFO


class ArgumentParser(argparse.ArgumentParser):
    def print_usage(self, file=None):
        pass

    def print_help(self, file=None):
        pass

    def error(self, message):
        pass


def main(args, unknown, command):
    wget_command = shlex.join(command)

    if check_cache(wget_command, args):
        logger.info('Cache hit')
        return
    # If file has not been cached, then run wget utility without any options
    logger.info('{}: Cache miss'.format(wget_command))

    if args.get('output_document') == '-':
        # Output to stdout
        _, out, err, return_code = run_command('{} {} 2>&1'.format(wget_path, wget_command))

        file_name = str(uuid.uuid4())
        with open(os.path.join(cacher_directory, 'wget_cache', file_name), 'w') as f:
            f.write(out)

        print(out)
    else:
        mod_wget_command = shlex.join(filter(lambda x: x not in {'-q', '--quiet', '-nv', '--no-verbose'}, command))
        _, out, err, return_code = run_command('{} {} 2>&1'.format(wget_path, mod_wget_command))

        # Get file_name from console output of wget command
        file_name = get_file_name(args, out)
        if (not file_name):
            logger.error("Unable to get file name from wget output. Skipping cache")
        # Copy the file in the local directory to the cacher directory and update cache
        shutil.copy(file_name, os.path.join(cacher_directory, 'wget_cache'))

    update_cache_result(wget_command, file_name, 0)
    sys.exit(return_code)


def check_cache(command, args):
    '''Function to check if the file exists in the cache
    and update file path as per flags -O or -P'''
    result = False
    current_cache_result = get_cache_result()
    if current_cache_result:
        value = current_cache_result.get(command)
        if value:
            file_name = value['file_name']
            if args.get('output_document') == '-':
                with open(os.path.join(cacher_directory, 'wget_cache', file_name), 'r') as f:
                    print(f.read())
                result = True
            else:
                if (args['directory_prefix']):
                    dest_dir = args['directory_prefix']
                    logger.info(dest_dir)
                    # check if the directory already exists
                    os.makedirs(dest_dir, exist_ok=True)
                try:
                    src_file = file_name.split('/')[-1]
                    shutil.copy(os.path.join(cacher_directory, 'wget_cache', src_file), file_name)
                    file_timestamp = os.path.getmtime(os.path.join(cacher_directory, 'wget_cache', src_file))
                    current_time = time.time()
                    logger.info("Cached file timestamp:{0}".format(file_timestamp))
                    logger.info("Current time:{0}".format(current_time))
                    result = True
                except Exception as error:
                    logger.exception(error)
            update_cache_result(command, file_name, 1)
    return result


def update_cache_result(command, file_name, flag):
    current_cache_result = get_cache_result()
    if (flag):
        current_cache_result[command]['count'] += 1
    else:
        current_cache_result[command] = {
            'file_name': file_name,
            'count': 0,
        }
    with open(os.path.join(cacher_directory, 'wget.json'), 'w') as f:
        return json.dump(current_cache_result, f)


def get_cache_result():
    try:
        with open(os.path.join(cacher_directory, 'wget.json'), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def parse_argv(argv):
    parser = ArgumentParser(add_help=False)
    parser.add_argument('-O', '--output-document', default=None)
    parser.add_argument('-P', '--directory-prefix', default=None)
    parser.add_argument('url')

    args = parser.parse_args()
    try:
        # Known Args as defined in parser.add_argument()
        args, unknown = parser.parse_known_args(argv)
        args = vars(args)
        return args, unknown, argv
    except SystemExit:
        return {}, [], argv


def get_file_name(args, out):
    '''Takes command as input and returns the filename'''
    file_name = ''
    match = None
    pattern = r"Saving to: ‘(.*?)’"
    match = re.search(pattern, out)
    if match:
        file_name = match.group(1)
    return file_name


def run_command(command):
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=True)
    stdout, stderr = process.communicate()
    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    return_code = process.returncode
    return process, stdout, stderr, return_code


def setup_logger():
    if not os.path.exists(os.path.join(cacher_directory, 'wget_cache')):
        os.makedirs(os.path.join(cacher_directory, 'wget_cache'))

    logging.basicConfig(
        filename=os.path.join(cacher_directory,
                              'wget-output.log'),
        format='%(message)s',
        filemode='a',
        level=logging_level
    )
    return logging.getLogger()


def read_env():
    envs = {}
    try:
        with open('/etc/reproducer-environment', 'r') as f:
            for line in f.readlines():
                line = line.strip()
                if line:
                    key, _, val = line.partition("=")
                    if key and val:
                        envs[key] = val
    except FileNotFoundError:
        pass
    return envs


if __name__ == '__main__':
    global envs, cacher_directory, logger
    envs = read_env()
    cacher_directory = envs.get('BUGSWARM_CACHER_PATH', '/home/github/cacher')
    logger = setup_logger()

    args, unknown, command = parse_argv(sys.argv[1:])
    main(args, unknown, command)
