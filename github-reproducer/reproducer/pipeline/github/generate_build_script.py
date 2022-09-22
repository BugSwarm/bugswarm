import uuid
import shlex
from bugswarm.common import log
from .github_builder import GitHubBuilder


def generate(github_builder: GitHubBuilder, steps, output_path, setup=True):
    # path to the source code
    if setup:
        lines = [
            '#!/usr/bin/env bash',
            'export BUILD_PATH={}'.format(github_builder.build_path),
            '',
            'set -o allexport',
            'source /etc/environment',
            'set +o allexport',
            '',
            # So we can run this script anywhere.
            'cd ${BUILD_PATH}',
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
            'cp -a /home/github/{}/steps/. ${{BUILD_PATH}}/'.format(github_builder.job.job_id),
            '',
            'CURRENT_ENV=\'\'',
            'PREVIOUS_STEP_FAILED=false'
        ]
    else:
        lines = [
            '#!/usr/bin/env bash',
            '',
            'set -o allexport',
            'source /etc/environment',
            'set +o allexport',
            '',
            'cd ${BUILD_PATH}',
            'CURRENT_ENV=\'\'',
            'PREVIOUS_STEP_FAILED=false'
        ]

    for s in steps:
        # s is None or (Step number: str, Step name: str, Custom command: bool, Command to set up: str,
        # Command to run: str, Step environment variables: str, Step workflow data: dict)
        if s is not None:
            step_number, step_name, is_custom_command, setup_command, run_command, envs, working_dir, step = s
            log.debug('Generate build script for step {} (#{})'.format(step_name, step_number))

            # Handle super basic if condition (always() and failure())
            step_if_condition = step['if'] if 'if' in step else ''

            if 'always()' in step_if_condition:
                condition = 'true'
            elif 'failure()' in step_if_condition:
                condition = '$PREVIOUS_STEP_FAILED == true'
            else:
                condition = '$PREVIOUS_STEP_FAILED != true'

            lines.append('if [[ {} ]]; then'.format(condition))

            lines.append('echo {}'.format(shlex.quote("##[group]{}".format(step_name))))
            # TODO: Add group details.
            lines.append('echo "##[endgroup]"')

            # Setup environment variable
            if envs != '':
                lines.append('CURRENT_ENV={} '.format(shlex.quote(envs)))

            # TODO: Fix spacing
            lines += [
                '',
                # If we have envs.txt file
                'if [ -f /home/github/workflow/envs.txt ]; then',
                # Use bash to convert DELIMITER list to env list
                '   KEY=\'\'',
                '   VALUE=\'\'',
                '   DELIMITER=\'\'',
                # Define regex
                '   regex=\'(.*)<<(.*)\'',
                '   regex2=\'(.*)=(.*)\'',
                '   while read line ',
                '   do',
                # If the line is var_name<<DELIMITER
                '      if [[ $key = \'\' && $line =~ $regex ]]; then',
                # Save var_name to KEY
                '         KEY=${BASH_REMATCH[1]}',
                '         DELIMITER=${BASH_REMATCH[2]}',
                # If the line is DELIMITER
                '      elif [[ $line = $DELIMITER ]]; then',
                '         if [[ $VALUE != \'\' ]]; then',
                '            VALUE=$(printf \'%q \' "$VALUE")',
                # Add KEY VALUE pairs to CURRENT_ENV
                '            CURRENT_ENV="${CURRENT_ENV}${KEY}=${VALUE} "',
                '         fi',
                # Reset KEY and VALUE
                '         KEY=\'\'',
                '         VALUE=\'\'',
                '         DELIMITER=\'\'',
                '      elif [[ $KEY != \'\' ]]; then',
                # If VALUE is empty, set VALUE to current line
                # Otherwise, append line to VALUE.
                '         if [[ $VALUE = \'\' ]]; then',
                '            VALUE="${line}"',
                '         else',
                '            VALUE="${VALUE}',
                '${line}"',
                '         fi',
                '      elif [[ $line =~ $regex2 ]]; then',
                '         TEMP_KEY=${BASH_REMATCH[1]}',
                '         TEMP_VALUE=$(printf \'%q \' "${BASH_REMATCH[2]}")',
                '         CURRENT_ENV="${CURRENT_ENV}${TEMP_KEY}=${TEMP_VALUE} "',
                '      fi',
                '   done <<< "$(cat /home/github/workflow/envs.txt)"',
                '',
                'else',
                # We don't have envs.txt file, create one
                '  echo -n \'\' > /home/github/workflow/envs.txt',
                'fi',
                '',
                'if [ -f /home/github/workflow/paths.txt ]; then',
                # Convert lines in paths.txt into $PATH
                '   while read NEW_PATH ',
                '   do',
                '      PATH="$(eval echo "$NEW_PATH"):$PATH"',
                '   done <<< "$(cat /home/github/workflow/paths.txt)"',
                'else',
                # We don't have paths file, create one
                '  echo -n \'\' > /home/github/workflow/paths.txt',
                'fi',
                '',
                'if [ ! -f /home/github/workflow/event.json ]; then',
                '  echo -n \'{}\' > /home/github/workflow/event.json',
                'fi'
            ]

            if setup_command:
                lines.append(setup_command)

            continue_on_error = 'continue-on-error' in step and step['continue-on-error']
            lines += [
                'RUN_UUID={}'.format(str(uuid.uuid4())),
                # Put commands to ${RUN_UUID}.sh, and run it.
                # We need ${RUN_UUID}.sh, running `env .. command` doesn't work.
                'if [[ $CURRENT_ENV != \'\' ]]; then',
                '  echo "env ${CURRENT_ENV}' + run_command + '" > ${BUILD_PATH}/${RUN_UUID}.sh',
                'else',
                '  echo "${CURRENT_ENV}' + run_command + '" > ${BUILD_PATH}/${RUN_UUID}.sh',
                'fi',
                '',
                'chmod u+x ${BUILD_PATH}/${RUN_UUID}.sh',
                '',
                # Change directory to working-directory
                '' if not working_dir else 'pushd {} > /dev/null'.format(working_dir),
                'EXIT_CODE=0',
                'set -e',
                '${BUILD_PATH}/${RUN_UUID}.sh || EXIT_CODE=$?',
                'set +e',
                # Check previous command exit code
                '' if not working_dir else 'popd > /dev/null',
                '',
                'if [[ $EXIT_CODE != 0 ]]; then',
                '	echo "" && echo "##[error]Process completed with exit code $EXIT_CODE."',
                '	{}'.format('' if continue_on_error else 'PREVIOUS_STEP_FAILED=true'),
                'fi',
                ''
            ]

            lines.append('fi')

    lines += [
        '',
        'if [[ $PREVIOUS_STEP_FAILED == true ]]; then',
        '   exit 1',
        'fi'
    ]

    log.debug('Writing build script to {}'.format(output_path))
    content = ''.join(map(lambda l: l + '\n', lines))
    with open(output_path, 'w') as f:
        f.write(content)
