import shlex

from bugswarm.common import log
from reproducer.model.step import Step

from .github_builder import GitHubBuilder


def generate(github_builder: GitHubBuilder, steps: 'list[Step]', output_path, setup=True):
    # path to the source code
    if setup:
        lines = [
            '#!/usr/bin/env bash',
            'export GITHUB_WORKSPACE={}'.format(github_builder.build_path),
            '',
            'set -o allexport',
            'source /etc/environment',
            'set +o allexport',
            '',
            # So we can run this script anywhere.
            'cd ${GITHUB_WORKSPACE}',
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
            'cp -a /home/github/{}/steps/. ${{GITHUB_WORKSPACE}}/'.format(github_builder.job.job_id),
            'cp /home/github/{}/event.json /home/github/workflow/event.json'.format(github_builder.job.job_id),
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
            'cd ${GITHUB_WORKSPACE}',
            'CURRENT_ENV=\'\'',
            'PREVIOUS_STEP_FAILED=false'
        ]

    for s in steps:
        # s is None or a Step object
        if s is not None:
            log.debug('Generate build script for step {} (#{})'.format(s.name, s.number))

            # Handle super basic if condition (always() and failure())
            step_if_condition = s.step['if'] if 'if' in s.step else ''

            if 'always()' in step_if_condition:
                condition = 'true'
            elif 'failure()' in step_if_condition:
                condition = '$PREVIOUS_STEP_FAILED == true'
            else:
                condition = '$PREVIOUS_STEP_FAILED != true'

            lines.append('if [[ {} ]]; then'.format(condition))

            lines.append('echo {}'.format(shlex.quote("##[group]{}".format(s.name))))
            # TODO: Add group details.
            lines.append('echo "##[endgroup]"')

            # TODO: Fix spacing
            lines += [
                'CURRENT_ENV=""',
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

            continue_on_error = 'continue-on-error' in s.step and s.step['continue-on-error']
            filepath = '${GITHUB_WORKSPACE}/' + s.filename

            # Setup command for predefined action
            # See https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runspre
            if s.setup_cmd:
                lines += [
                    'echo ' + s.setup_cmd + ' > ' + filepath,
                    'chmod u+x ' + filepath,
                    'env ' + s.envs + ' ${CURRENT_ENV} ' + s.exec_template.format(filepath)
                ]

            lines += [
                # Put commands into filepath, and run it.
                # We need a separate file to put commands in, running `env .. command` doesn't work.
                'echo ' + s.run_cmd + ' > ' + filepath,
                'chmod u+x ' + filepath,
                '',
                # Change directory to working-directory
                '' if not s.working_dir else 'pushd {} > /dev/null'.format(s.working_dir),
                'EXIT_CODE=0',
                'set -e',
                'env ' + s.envs + ' ${CURRENT_ENV} ' + s.exec_template.format(filepath) + ' || EXIT_CODE=$?',
                'set +e',
                # Check previous command exit code
                '' if not s.working_dir else 'popd > /dev/null',
                '',
                'if [[ $EXIT_CODE != 0 ]]; then',
                '  echo "" && echo "##[error]Process completed with exit code $EXIT_CODE."',
                '  {}'.format('' if continue_on_error else 'PREVIOUS_STEP_FAILED=true'),
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
