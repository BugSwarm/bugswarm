import argparse
import os
import re
import sys
import time

from bugswarm.common import log
from bugswarm.common.credentials import DOCKER_HUB_CACHED_REPO, DOCKER_HUB_REPO

from CacheMaven import PatchArtifactMavenTask
from CachePython import PatchArtifactPythonTask
from utils import PatchArtifactRunner, PatchArtifactTask, get_repr_metadata_dict


_COPY_DIR = 'from_host'


class DynamicPatchArtifactTask(PatchArtifactTask):
    def __init__(self, runner: PatchArtifactRunner, image_tag: str):
        super().__init__(runner, image_tag)
        self.runner = runner
        self.lang_override = runner.args.language

    def run(self):
        lang = self.lang_override or self.repr_metadata[self.image_tag]['language']
        task = self._get_task_for_language(lang)
        return task.run()

    def _get_task_for_language(self, lang):
        if lang == 'java':
            return PatchArtifactMavenTask(self.runner, self.image_tag)
        elif lang == 'python':
            return PatchArtifactPythonTask(self.runner, self.image_tag)
        else:
            raise ValueError('Unsupported language "{}" (supported: "java", "python")'.format(lang))


def main():
    log.config_logging('INFO')

    args = validate_input()
    print_args(args)

    output_file = os.path.join('output', args.task_name + '.csv')
    os.makedirs('output', exist_ok=True)

    repr_metadata_dict = {}
    if args.task_json:
        log.info('Getting pairs from ReproducedResultsAnalyzer JSON')
        repr_metadata_dict = get_repr_metadata_dict(args.task_json, repr_metadata_dict)

    t_start = time.time()
    runner = PatchArtifactRunner(
        DynamicPatchArtifactTask,
        args.image_tags_file,
        _COPY_DIR,
        output_file,
        repr_metadata_dict,
        args,
        args.workers)
    runner.run()
    t_end = time.time()
    log.info('Running patch took {}s'.format(t_end - t_start))


def print_args(args):
    log.info('Command line arguments:')
    for k, v in vars(args).items():
        log.info('    {}: {}'.format(k, v))


def validate_input():
    parser = argparse.ArgumentParser()

    parser.add_argument('image_tags_file',
                        help='Path to a file containing a newline-separated list of image tags to process.')
    parser.add_argument('task_name',
                        help='Name of current task. Results will be put in ./output/<task-name>.csv.')
    lang_group = parser.add_mutually_exclusive_group(required=True)
    lang_group.add_argument('--language', choices=('java', 'python'),
                            help='The language of the artifact(s) being cached. One of "java" or "python". Cannot be '
                            'used with --task-json.')
    lang_group.add_argument('--task-json', '--task_json', default='',
                            help='Location of task JSON from ReproducedResultsAnalyzer. Cannot be used with '
                            '--language.')

    parser.add_argument('--workers', type=int, default=4, help='Number of parallel tasks to run.')
    parser.add_argument('--no-push', action='store_true', help='Do not push the artifact to Docker Hub.')
    parser.add_argument('--cleanup-images', action='store_true', help='Clean up final images after pushing them.')
    parser.add_argument('--src-repo', default=DOCKER_HUB_REPO, help='Which repo to pull non-cached images from.')
    parser.add_argument('--dst-repo', default=DOCKER_HUB_CACHED_REPO, help='Which repo to push cached images to.')

    debugging_opts = parser.add_argument_group('Debugging options')
    debugging_opts.add_argument('--keep-tmp-images', action='store_true',
                                help='Keep temporary container images in the temporary repository.')
    debugging_opts.add_argument('--keep-containers', action='store_true',
                                help='Keep containers in order to debug.')
    debugging_opts.add_argument('--keep-tars', action='store_true',
                                help='Keep tar files in order to debug.')

    cache_opts = parser.add_argument_group('Caching options')
    cache_opts.add_argument('--disconnect-network-during-test', action='store_true',
                            help='When testing, disconnect the docker container from the network.')
    cache_opts.add_argument('--no-copy-actions-toolcache', action='store_true',
                            help='Do not copy /opt/hostedtoolcache/ directory.')
    cache_opts.add_argument('--no-cache-git', action='store_true',
                            help='Do not cache git clone and git submodule.')
    cache_opts.add_argument('--no-cache-wget', action='store_true',
                            help='Do not cache wget.')
    # TODO: This is not used by the Python cacher. Bug or feature?
    cache_opts.add_argument('--no-separate-passed-failed', action='store_false', dest='separate_passed_failed',
                            help='Do not separate passed and failed cached files (may decrease artifact size, but may '
                            'also cause errors).')

    java_opts = parser.add_argument_group('Java options')
    java_opts.add_argument('--no-copy-home-m2', action='store_true',
                           help='Do not copy /home/github/.m2/ directory.')
    java_opts.add_argument('--no-copy-home-gradle', action='store_true',
                           help='Do not copy /home/github/.gradle/ directory.')
    java_opts.add_argument('--no-copy-home-ivy2', action='store_true',
                           help='Do not copy /home/github/.ivy2/ directory.')
    java_opts.add_argument('--no-copy-proj-gradle', action='store_true',
                           help='Do not copy /home/github/build/*/*/*/.gradle/ directory.')
    java_opts.add_argument('--no-copy-proj-gradle-wrapper', action='store_true',
                           help='Do not copy /home/github/build/*/*/gradle/wrapper directory.')
    java_opts.add_argument('--no-copy-proj-maven', action='store_true',
                           help='Do not copy /home/github/build/*/*/.mvn directory.')
    java_opts.add_argument('--no-remove-maven-repositories', action='store_true',
                           help='Do not remove `_remote.repositories` and `_maven.repositories`.')
    java_opts.add_argument('--ignore-cache-error', action='store_true',
                           help='Ignore error when running build script to download cached files.')
    java_opts.add_argument('--no-strict-offline-test', action='store_true',
                           help='Do not apply strict offline mode when testing.')

    args = parser.parse_args()
    if not os.path.isfile(args.image_tags_file):
        parser.error('{} is not a file or does not exist. Exiting.'.format(args.image_tags_file))

    if args.task_json and not os.path.isfile(args.task_json):
        parser.error('{} is not a file or does not exist. Exiting.'.format(args.task_json))

    if not re.fullmatch(r'[\w-]+', args.task_name):
        parser.error('{} is not a valid task name. Exiting.'.format(args.task_name))

    return args


if __name__ == '__main__':
    sys.exit(main())
