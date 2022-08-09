import os
import git
import yaml
import copy
from bugswarm.common.shell_wrapper import ShellWrapper
from bugswarm.common import log
from reproducer.model.job import Job
from reproducer.reproduce_exception import ReproduceError

IGNORE_ACTIONS = {'codecov/codecov-action', 'actions/checkout', 'actions/upload-artifact', 'actions/download-artifact',
                  'actions/cache', 'gradle/wrapper-validation-action'}


class GitHubBuilder:

    def __init__(self, job: Job, location: str, utils):
        self.job = job
        self.location = location
        self.utils = utils
        # TODO: set them to correct values
        self.JOB_NAME = 'build'
        self.WORKFLOW_NAME = 'CI'
        self.ENV = {}
        # predefined actions directory
        os.makedirs(os.path.join(location, 'actions'), exist_ok=True)

    def __str__(self):
        return 'GitHubBuilder({} @ {})'.format(self.job.job_id, self.location)

    def __repr__(self):
        return str(self)

    def build(self):
        log.debug('Building build script with {}'.format(self))

        # Create build script for GitHub job
        if 'steps' not in self.job.config or not isinstance(self.job.config['steps'], list):
            GitHubBuilder.raise_error(
                'Encountered an error while generating the build script: steps attribute is missing from config.', 1)

        steps = []  # (Step Number: str, Step Name: str, Step Commands: [str])
        for step_number, step in enumerate(self.job.config['steps']):
            if 'uses' in step:
                steps.append(self.predefined_action(step_number, step))
            elif 'run' in step:
                steps.append(self.custom_action(step_number, step))

        log.debug('Generating build script... ({} steps)'.format(len(steps)))
        self.generate_build_script(steps)

    # TODO: Create build script based on steps.
    def generate_build_script(self, steps):
        lines = [
            '#!/usr/bin/env bash',
            '',
            # So we can run this script anywhere.
            'cd /home/github/build/{}'.format(self.job.repo),
            '',
            # Analyzer needs this header to get OS.
            'echo "##[group]Operating System"',
            'cat /etc/lsb-release | grep -oP \'(?<=DISTRIB_ID=).*\'',
            'cat /etc/lsb-release | grep -oP \'(?<=DISTRIB_RELEASE=).*\'',
            'echo "LTS"',
            'echo "##[endgroup]"',
            '',
            # Predefined actions need this directory.
            'mkdir -p /home/github/workflow/',
            '',
            'CURRENT_ENV=\'\''
        ]

        for step in steps:
            # step is None or (Step Number: str, Step Name: str, Step Commands: [str])
            if step is not None:
                step_number, step_name, step_commands = step
                log.debug('Generate build script for step {} (#{})'.format(step_name, step_number))
                lines.append('echo "##[group]{}"'.format(step_name))

                # Setup environment variable
                try:
                    # TODO: Read from memory, not disk
                    with open(os.path.join(self.location, 'step_{}.env'.format(step_number)), 'r') as f:
                        prefix = f.read()
                        if prefix != '':
                            lines.append('CURRENT_ENV=\'{} \''.format(prefix.replace('\'', '\'"\'"\'')))
                except FileNotFoundError:
                    # No environment variables for this step.
                    log.debug('No environment variable for step {} (#{})'.format(step_name, step_number))
                    pass

                lines += [
                    '',
                    # If we have envs.txt file
                    'if [ -f /home/github/workflow/envs.txt ]; then',
                    # Use bash to convert _GitHubActionsFileCommandDelimeter_ list to env list
                    '   KEY=\'\'',
                    '   VALUE=\'\'',
                    # Define regex
                    '   regex=\'(.*)<<_GitHubActionsFileCommandDelimeter_\'',
                    '   while read line ',
                    '   do',
                    # If the line is var_name<<_GitHubActionsFileCommandDelimeter_
                    '      if [[ $key = \'\' && $line =~ $regex ]]; then',
                    # Save var_name to KEY
                    '         KEY=${BASH_REMATCH[1]}',
                    # If the line is _GitHubActionsFileCommandDelimeter_
                    '      elif [[ $line = \'_GitHubActionsFileCommandDelimeter_\' ]]; then',
                    # Add KEY VALUE pairs to CURRENT_ENV
                    # TODO: Check VALUE is not empty
                    '         CURRENT_ENV="${CURRENT_ENV}${KEY}=${VALUE} "',
                    # Reset KEY and VALUE
                    '         KEY=\'\'',
                    '         VALUE=\'\'',
                    '      else',
                    # If VALUE is empty, set VALUE to current line
                    # Otherwise, append line to VALUE.
                    # TODO: Check KEY is not empty
                    '         if [[ $VALUE = \'\' ]]; then',
                    '            VALUE="${VALUE}${line}"',
                    '         else',
                    '            VALUE="${VALUE}\\n${line}"',
                    '         fi',
                    '      fi',
                    '   done <<< "$(cat /home/github/workflow/envs.txt)"',
                    '',
                    'else',
                    # We don't have envs.txt file, create one
                    '  echo -n \'\' > /home/github/workflow/envs.txt',
                    'fi',
                    '',
                    # We don't have paths file, create one
                    'if [ ! -f /home/github/workflow/paths.txt ]; then',
                    '  echo -n \'\' > /home/github/workflow/paths.txt',
                    'fi',
                    '',
                    'if [ ! -f /home/github/workflow/event.json ]; then',
                    '  echo -n \'{}\' > /home/github/workflow/event.json',
                    'fi'
                ]

                for command in step_commands:
                    lines += [
                        # Put commands to bugswarm_cmd.sh, and run it.
                        # We need bugswarm_cmd.sh, running `env .. command` doesn't work.
                        'if [[ $CURRENT_ENV != \'\' ]]; then',
                        '  echo "env ${CURRENT_ENV}' + command + '" > bugswarm_cmd.sh',
                        'else',
                        '  echo "${CURRENT_ENV}' + command + '" > bugswarm_cmd.sh',
                        'fi',
                        '',
                        'chmod u+x bugswarm_cmd.sh',
                        './bugswarm_cmd.sh',
                        '',
                        # Check previous command exit code
                        #  TODO: Don't exit right away, check always() condition and continue-on-error for future steps.
                        'if [ $? -ne 0 ]; then',
                        '	echo "##[error]Process completed with exit code $?."',
                        '	exit 1',
                        'fi'
                    ]
                lines.append('echo "##[endgroup]"')
                lines.append('')

        log.debug('Writing build script to {}'.format(self.location, 'run.sh'))
        content = ''.join(map(lambda l: l + '\n', lines))
        with open(os.path.join(self.location, 'run.sh'), 'w') as f:
            f.write(content)

    def clone_action_repo_if_not_exists(self, action_name, repo, branch):
        log.debug('Download action to {} '.format(os.path.join(self.location, 'actions', action_name)))

        if not os.path.isdir(os.path.join(self.location, 'actions', action_name)):
            os.makedirs(os.path.join(self.location, 'actions', action_name), exist_ok=True)
            git.Repo.clone_from(
                self.utils.construct_github_repo_url(repo),
                os.path.join(self.location, 'actions', action_name),
                branch=branch
            )

    def predefined_action_env(self, step_number, action_repo):
        return {
            'CI': True,
            'GITHUB_ACTION': step_number,
            'GITHUB_ACTION_PATH': '',
            'GITHUB_ACTION_REPOSITORY': action_repo,
            'GITHUB_ACTIONS': True,
            'GITHUB_ACTOR': 'bugswarm/bugswarm',
            'GITHUB_API_URL': 'https://api.github.com',
            'GITHUB_BASE_REF': '',
            'GITHUB_ENV': '/home/github/workflow/envs.txt',
            'GITHUB_EVENT_NAME': 'push',
            'GITHUB_EVENT_PATH': '/home/github/workflow/event.json',
            'GITHUB_GRAPHQL_URL': 'https://api.github.com/graphql',
            'GITHUB_HEAD_REF': '',
            'GITHUB_JOB': self.JOB_NAME,
            'GITHUB_PATH': '/home/github/workflow/paths.txt',
            'GITHUB_REF': 'master',
            'GITHUB_REF_NAME': '',
            'GITHUB_REF_TYPE': '',
            'GITHUB_REPOSITORY': self.job.repo,
            'GITHUB_REPOSITORY_OWNER': self.job.repo.split('/')[0],
            'GITHUB_RETENTION_DAYS': 0,
            'GITHUB_RUN_ATTEMPT': 1,
            'GITHUB_RUN_ID': 1,
            'GITHUB_RUN_NUMBER': 1,
            'GITHUB_SERVER_URL': 'https://github.com',
            'GITHUB_SHA': self.job.sha,
            'GITHUB_STEP_SUMMARY': '',
            'GITHUB_WORKFLOW': self.WORKFLOW_NAME,
            'GITHUB_WORKSPACE': '/home/github/build',
            'RUNNER_ARCH': '',
            'RUNNER_NAME': '',
            'RUNNER_OS': 'Linux',
            'RUNNER_TEMP': '/tmp',
            'RUNNER_TOOL_CACHE': '/opt/hostedtoolcache'
        }

    def predefined_action(self, step_number, step):
        name = step['uses']
        action_repo, _, tag = name.partition('@')

        log.debug('Setting up build code for predefined_action {}(#{})'.format(name, step_number))

        if action_repo.lower() in IGNORE_ACTIONS:
            return

        # Download action source code
        self.clone_action_repo_if_not_exists(name.replace('/', '-'), action_repo, tag)

        github_envs = self.predefined_action_env(step_number, action_repo)
        log.debug('Got GitHub {} envs.'.format(len(github_envs)))

        envs = copy.deepcopy(self.ENV)
        cmd = ''
        is_setup = 'actions/setup-' in action_repo

        if 'with' in step:
            for key, value in step['with'].items():
                if is_setup and key == 'cache':
                    # TODO: Need to ignore cache key, find out why.
                    continue

                envs['INPUT_{}'.format(key.upper().replace(' ', '_'))] = str(value).replace('\n', '\\n')
        try:
            # TODO: Change action.yml based on 'uses'
            action_file = 'action.yml'
            with open(os.path.join(self.location, 'actions', name.replace('/', '-'), action_file), 'r') as f:
                action_file = yaml.safe_load(f)
                # TODO: Handle non-nodejs predefined workflow.
                cmd = 'node /home/github/actions/' + name.replace('/', '-') + '/' + action_file['runs']['main']

                if 'inputs' in action_file:
                    for key, value in action_file['inputs'].items():
                        if 'INPUT_{}'.format(key.upper().replace(' ', '_')) not in envs:
                            if 'default' in value:
                                # TODO: Evaluate expression
                                if '${{' in str(value['default']):
                                    # SKIP them for now.
                                    continue
                                envs['INPUT_{}'.format(key.upper().replace(' ', '_'))] = str(value['default']).replace(
                                    '\n', '\\n')
        except Exception as e:
            GitHubBuilder.raise_error(repr(e), 1)

        # TODO: Save to memory, not disk
        with open(os.path.join(self.location, 'step_{}.env'.format(step_number)), 'w') as f:
            for key, value in github_envs.items():
                if value != '':
                    f.write('{}="{}" '.format(key, value) if ' ' in str(value) else '{}={} '.format(key, value))

            for key, value in envs.items():
                if value != '':
                    f.write('{}="{}" '.format(key, value) if ' ' in str(value) else '{}={} '.format(key, value))

        return step_number, 'Run {}'.format(name), [cmd]

    def custom_action(self, step_number, step):
        commands = [line for line in step['run'].split('\n') if line]
        envs = copy.deepcopy(self.ENV)

        log.debug('Setting up build code for custom commands action #{}'.format(step_number))

        if 'env' in step:
            for key, value in step['env'].items():
                envs[key] = value

        if len(envs) > 0:
            with open(os.path.join(self.location, 'step_{}.env'.format(step_number)), 'w') as f:
                for key, value in envs.items():
                    if value != '':
                        f.write('{}="{}" '.format(key, value) if ' ' in str(value) else '{}={} '.format(key, value))

        return step_number, 'Run {}'.format(commands[0]), commands

    @staticmethod
    def raise_error(message, return_code):
        if return_code:
            raise ReproduceError(message)
