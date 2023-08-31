#!/usr/bin/env python3

import re
import os
import sys
import uuid
import json
import logging
import argparse
import subprocess


git_path = '/usr/bin/git_original'
logging_level = logging.INFO


class ArgumentParser(argparse.ArgumentParser):
    def print_usage(self, file=None):
        pass

    def print_help(self, file=None):
        pass

    def error(self, message):
        pass


def main(args, unknown, command):
    # Need to remove --quiet for git clone and git submodule caching
    git_command = [x for x in command if x not in ('-q', '--quiet')]
    logger.info('> Running git command: {}'.format(git_command))
    logger.debug('Current directory is: {}'.format(os.getcwd()))

    if check_for_cache(args, git_command):
        logger.info('Cache hit')
        return

    # Not from cache, warn or stop depends on BUGSWARM_GIT_CACHER
    cacher_status = envs.get('BUGSWARM_GIT_CACHER', '')
    if args.get('type') in {'clone', 'pull', 'fetch'} or \
            (args.get('type') == 'submodule' and args.get('submodule_type') == 'update'):
        if cacher_status in {'warn', 'error'}:
            logger.warning('{}: Cache miss'.format(git_command))
        if cacher_status == 'error':
            sys.exit(1)

        # Run the actual git command
        try:
            _, out, _, return_code = run_command([git_path, *git_command], separate_stderr=False, echo=True)
            logger.info('Return code: {}'.format(return_code))

            if return_code != 0:
                sys.exit(return_code)

            # Parse git command's output for caching
            if cache_command(args, unknown, command, str(out)):
                logger.info('Cached!')
        except Exception as e:
            logger.error(repr(e))
    else:
        command = [git_path, *git_command]
        logger.debug('Running command using subprocess.run: {}'.format(command))
        sys.exit(subprocess.run(command).returncode)


def check_for_cache(args, git_command):
    current_cache_result = get_cache_result()  # Read git.json

    for cache_dir_id, value in current_cache_result.items():
        # Same git command
        if value['git_command'] == git_command:
            if args.get('C') == value['cwd'] or args.get('directory') == value['cwd'] or \
                    os.getcwd() == value['cwd'] or value['is_relative'] is False:
                # In the same directory
                # Not in the same directory, but destination path is absolute
                # In different directory, but -C is set
                for src, dest in value['copy'].items():
                    # Copy directories to dest (original destination)
                    src = src.replace('/home/github/cacher', cacher_directory)
                    copy(src, dest)
                return True

            dir = args.get('C') or os.getcwd()
            if not dir.startswith('/'):
                dir = os.path.join(os.getcwd(), dir)
            if args.get('directory'):
                dir = os.path.join(dir, args.get('directory'))
            if dir.endswith('/'):
                dir = dir[:-1]
            _, origin, _, _ = run_command([git_path, '-C', dir, 'ls-remote', '--get-url'])
            if value['origin'] == origin:
                # Same command, same repo, different directory
                for src, dest in value['copy'].items():
                    # Copy directories to dir (based on -C or current working directory)
                    src = src.replace('/home/github/cacher', cacher_directory)
                    copy(src, dir, exact_dest=False)
                return True

        # Check everything excepts C and directory
        # Only work for git clone for now.
        if args.get('type') != 'clone':
            continue

        if all([True if k in {'directory', 'C'} else value['args'].get(k) == v for k, v in args.items()]):
            # dir is the base path. Based on -C or current working directory.
            dir = args.get('C') or os.getcwd()
            if not dir.startswith('/'):
                dir = os.path.join(os.getcwd(), dir)
            if dir.endswith('/'):
                dir = dir[:-1]

            for src, _ in value['copy'].items():
                src = src.replace('/home/github/cacher', cacher_directory)
                if args.get('directory'):
                    directory = args.get('directory')
                else:
                    _, ref_urls, _, _ = run_command([git_path, '-C', src, 'ls-remote', '--get-url'])
                    ref_urls = ref_urls.splitlines()
                    _, out, _, return_code = run_command(['basename', '-s', '.git', *ref_urls])
                    if return_code != 0:
                        continue
                    else:
                        directory = out

                dest = os.path.join(dir, directory)
                copy(src, dest)
            return True


def cache_command(args, unknown, command, output):
    if 'type' not in args:
        return False

    if args['type'] == 'clone':
        return cache_clone(args, unknown, command, output)
    elif args['type'] in {'fetch', 'pull'}:
        return cache_fetch_pull(args, unknown, command, output)
    elif args['type'] == 'submodule':
        return cache_submodule(args, unknown, command, output)


def cache_clone(args, unknown, command, output):
    dir = args.get('C') or os.getcwd()  # Don't need args.get('directory') here
    if dir.endswith('/'):
        dir = dir[:-1]

    regex = r"Cloning into (bare repository )?'(([^/ ]*)(/[^/ ]*)*/?)'\.\.\."
    location = ''
    for line in output.split('\n'):
        match = re.match(regex, line)
        if match:
            location = match.group(2)
            break

    if not location:
        logger.error('Cannot find destination, use DEBUG to check git output!')
        return False

    is_relative = False
    if not location.startswith('/'):
        is_relative = True
        # Relative path: dir is the base path. Based on -C or current working directory.
        location = os.path.join(dir, location)

    cache_dir_id = str(uuid.uuid4())
    cache_dir_path = os.path.join(cacher_directory, 'git_cache', cache_dir_id)
    cache_dir_dest = os.path.join(cache_dir_path, location.rpartition('/')[2])

    # Copy directory from location to cache_dir_dest
    # Next time user runs the command, we need to copy cache_dir_dest to location
    copy(location, cache_dir_dest)
    update_cache_result(cache_dir_id, args, unknown, command, {cache_dir_dest: location}, is_relative)
    return True


def cache_fetch_pull(args, unknown, command, output):
    dir = args.get('C') or os.getcwd()
    if dir.endswith('/'):
        dir = dir[:-1]

    location = os.path.join(dir, '.git')
    if os.path.exists(location):
        # Save .git directory, if we run git fetch/pull again, we will copy it back
        cache_dir_id = str(uuid.uuid4())
        cache_dir_path = os.path.join(cacher_directory, 'git_cache', cache_dir_id)
        cache_dir_dest = os.path.join(cache_dir_path, '.git')
        copy(location, cache_dir_dest)

        _, origin, _, _ = run_command([git_path, '-C', dir, 'ls-remote', '--get-url'])
        update_cache_result(cache_dir_id, args, unknown, command, {cache_dir_dest: location}, None, origin=origin)


def cache_submodule(args, unknown, command, output):
    dir = args.get('C') or os.getcwd()
    if dir.endswith('/'):
        dir = dir[:-1]

    _, origin, _, _ = run_command([git_path, '-C', dir, 'ls-remote', '--get-url'])

    regex = r"Cloning into (bare repository )?'(([^/ ]*)(/[^/ ]*)*/?)'\.\.\."
    locations = []
    for line in output.split('\n'):
        match = re.match(regex, line)
        if match:
            location = match.group(2)
            if not location.startswith('/'):
                # Relative path
                location = os.path.join(dir, location)
            logger.debug('Submodule location: ' + location)
            locations.append(location)

    cache_dir_id = str(uuid.uuid4())
    cache_dir_path = os.path.join(cacher_directory, 'git_cache', cache_dir_id)

    if not locations:
        # No submodule, still cache the command, so if we run git submodule update again we will restore nothing
        logger.debug('No submodule')
        update_cache_result(cache_dir_id, args, unknown, command, {}, None, origin=origin)
        return False

    cache_dir_dests = map(lambda location: os.path.join(cache_dir_path, location.rpartition('/')[2]), locations)
    repo_pairs = list(zip(cache_dir_dests, locations))

    # Copy directory from location to cache_dir_dest
    # Next time user runs the command, we need to copy cache_dir_dest to location
    for cache_dir_dest, location in repo_pairs:
        copy(location, cache_dir_dest)

    update_cache_result(cache_dir_id, args, unknown, command, dict(repo_pairs), None, origin=origin)
    return True


def update_cache_result(cache_dir_id, args, unknown, command, source_dict, is_relative, origin=None):
    current_cache_result = get_cache_result()
    current_cache_result[cache_dir_id] = {
        'git_command': [x for x in command if x not in ('-q', '--quiet')],
        'copy': source_dict,
        'is_relative': is_relative,
        'cwd': os.getcwd(),
        'args': args,
        'unknown': unknown,
        'origin': origin
    }
    with open(os.path.join(cacher_directory, 'git.json'), 'w') as f:
        return json.dump(current_cache_result, f)


def get_cache_result():
    try:
        with open(os.path.join(cacher_directory, 'git.json'), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def copy(src, dest, exact_dest=True):
    # Copy directory from src to dest using sudo
    # Use -a to keep the same owner
    os.makedirs(dest, exist_ok=True)
    flags = '-Ta' if exact_dest else '-a'
    run_command(['sudo', 'cp', flags, src, dest])


def parse_argv(argv):
    parser = ArgumentParser(add_help=False)
    subparser = parser.add_subparsers(dest='type')
    clone = subparser.add_parser('clone')
    submodule = subparser.add_parser('submodule')
    submodule_subparser = submodule.add_subparsers(dest='submodule_type')
    submodule_update = submodule_subparser.add_parser('update')
    subparser.add_parser('fetch')
    subparser.add_parser('pull')

    parser.add_argument('-C', default=None, required=False)
    parser.add_argument('-c', '--config', default=None)
    parser.add_argument('--config-env', default=None)
    parser.add_argument('--work-tree', default=None)
    parser.add_argument('--namespace', default=None)

    clone.add_argument('--template', default=None)
    clone.add_argument('-o', '--origin', default=None)
    clone.add_argument('-b', '--branch', default=None)
    clone.add_argument('-u', '--upload-pack', default=None)
    clone.add_argument('--reference', default=None)
    clone.add_argument('--reference-if-able', default=None)
    clone.add_argument('--depth', default=None)
    clone.add_argument('--shallow-since', default=None)
    clone.add_argument('--shallow-exclude', default=None)
    clone.add_argument('-c', '--config', default=None)
    clone.add_argument('--server-option', default=None)
    clone.add_argument('-j', '--jobs', default=None)
    clone.add_argument('--filter', default=None)
    clone.add_argument('--bundle-uri', default=None)
    clone.add_argument('repository')
    clone.add_argument('directory', default='', nargs='?')

    submodule_update.add_argument('--reference', default=None)
    submodule_update.add_argument('--depth', default=None)
    submodule_update.add_argument('-j', '--jobs', default=None)
    submodule_update.add_argument('--filter', default=None)
    submodule_update.add_argument('path', default='', nargs='?')

    try:
        args, unknown = parser.parse_known_args(argv)
        args = vars(args)
    except TypeError:
        args, unknown = {}, []
    except SystemExit:
        return {}, [], argv
    return args, unknown, argv


def run_command(command, separate_stderr=True, echo=False):
    logger.debug('Running command {}'.format(command))

    stderr_dest = subprocess.PIPE if separate_stderr else subprocess.STDOUT
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_dest)
    stdout, stderr = process.communicate()

    stdout = stdout or b''
    stderr = stderr or b''

    if echo:
        sys.stdout.buffer.write(stdout)
        sys.stderr.buffer.write(stderr)

    stdout = stdout.decode('utf-8').strip()
    stderr = stderr.decode('utf-8').strip()
    return_code = process.returncode
    return process, stdout, stderr, return_code


def setup_logger():
    if not os.path.exists(os.path.join(cacher_directory, 'git_cache')):
        os.makedirs(os.path.join(cacher_directory, 'git_cache'))

    logging.basicConfig(
        filename=os.path.join(cacher_directory, 'git-output.log'),
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
                    key, _, val = line.partition('=')
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
