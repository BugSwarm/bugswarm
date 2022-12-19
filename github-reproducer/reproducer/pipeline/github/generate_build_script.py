import re
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
            # Required for the success()/failure()/cancelled() status functions to work
            'export _GITHUB_JOB_STATUS=success',
            '',
            # So we can run this script anywhere.
            'cd ${GITHUB_WORKSPACE}',
            '',
            # Analyzer needs this header to get OS.
            'echo "##[group]Operating System"',
            'echo "Ubuntu"',  # We only support Ubuntu runs-on
            'echo "{}"'.format('Unknown' if not github_builder.job.runs_on else github_builder.job.runs_on[7:]),
            'echo "LTS"',
            'echo "##[endgroup]"',
            '',
            # Predefined actions need this directory.
            'mkdir -p /home/github/workflow/',
            '',
            'cp /home/github/{}/event.json /home/github/workflow/event.json'.format(github_builder.job.job_id),
            'echo -n > /home/github/workflow/envs.txt',
            'echo -n > /home/github/workflow/paths.txt',
            '',
            'CURRENT_ENV=()',
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
            'CURRENT_ENV=()',
        ]

    lines += [
        'update_current_env() {',
        '  CURRENT_ENV=()',
        '  unset CURRENT_ENV_MAP',
        '  declare -gA CURRENT_ENV_MAP',
        '  if [ -f /home/github/workflow/envs.txt ]; then',
        # Use bash to convert DELIMITER list to env list
        '    local KEY=""',
        '    local VALUE=""',
        '    local DELIMITER=""',
        # Define regex
        '    local regex="(.*)<<(.*)"',
        '    local regex2="(.*)=(.*)"',
        '',
        '    while read line; do',

        # If the line is var_name<<DELIMITER
        '      if [[ "$KEY" = "" && "$line" =~ $regex ]]; then',
        # Save var_name to KEY
        '        KEY="${BASH_REMATCH[1]}"',
        '        DELIMITER="${BASH_REMATCH[2]}"',

        # If the line is DELIMITER
        '      elif [[ "$KEY" != "" && "$line" = "$DELIMITER" ]]; then',
        # Add KEY VALUE pairs to CURRENT_ENV
        '        CURRENT_ENV_MAP["$KEY"]="$VALUE"',
        # Reset KEY and VALUE
        '        KEY=""',
        '        VALUE=""',
        '        DELIMITER=""',

        '      elif [[ "$KEY" != "" ]]; then',
        # If VALUE is empty, set it to current line. Otherwise, append \n + line to VALUE
        '        if [[ $VALUE = "" ]]; then',
        '          VALUE="$line"',
        '        else',
        '          VALUE="$VALUE\n$line"',
        '        fi',

        # The line is "var_name=value"; set the corresponding variable
        '      elif [[ "$line" =~ $regex2 ]]; then',
        '        CURRENT_ENV_MAP["${BASH_REMATCH[1]}"]="${BASH_REMATCH[2]}"',
        '      fi',

        '    done < /home/github/workflow/envs.txt',
        '',

        # Set CURRENT_ENV from ENV array
        '    for key in "${!CURRENT_ENV_MAP[@]}"; do',
        '        val="${CURRENT_ENV_MAP["$key"]}"',
        '        CURRENT_ENV+=("${key}=${val}")',
        '    done',

        '  else',
        # We don't have envs.txt file, create one
        '    echo -n "" > /home/github/workflow/envs.txt',
        '  fi',
        '}',
    ]

    for s in steps:
        # s is None or a Step object
        if s is not None:
            log.debug('Generate build script for step {} (#{})'.format(s.name, s.number))

            # TODO: Fix spacing
            lines += [
                '',
                'update_current_env',
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
                'fi',
                ''
            ]

            filepath = '{}/{}'.format(github_builder.steps_dir, s.filename)

            # Need indirection so that environment variables are taken into account
            lines += [
                'STEP_CONDITION=' + resolve_exprs(s.envs, s.step_if),
                'if [[ "$STEP_CONDITION" = "true" ]]; then',
                '',
            ]

            lines.append('echo {}'.format('"##[group]"{}'.format(s.name)))
            # TODO: Add group details.
            lines.append('echo "##[endgroup]"')

            # Setup command for predefined action
            # See https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runspre
            if s.setup_cmd:
                lines += [
                    'echo ' + s.setup_cmd + ' > ' + filepath,
                    'chmod u+x ' + filepath,
                    run_with_envs(s.envs, s.exec_template.format(filepath))
                ]

            lines += [
                # Put commands into filepath, and run it.
                # We need a separate file to put commands in, running `env .. command` doesn't work.
                'echo ' + s.run_cmd + ' > ' + filepath,
                'chmod u+x ' + filepath,
                '',
                # Change directory to working-directory
                '' if not s.working_dir else 'pushd {} > /dev/null'.format(resolve_exprs(s.envs, s.working_dir)),
                'EXIT_CODE=0',
                run_with_envs(s.envs, s.exec_template.format(filepath)),
                'EXIT_CODE=$?',
                # Check previous command exit code
                '' if not s.working_dir else 'popd > /dev/null',
                '',

                # Handle exit code (the closing "fi" is added later)
                'if [[ $EXIT_CODE != 0 ]]; then',
                '  CONTINUE_ON_ERROR=' + resolve_exprs(s.envs, s.continue_on_error),
                '  if [[ "$CONTINUE_ON_ERROR" != "true" ]]; then ',
                '    export _GITHUB_JOB_STATUS=failure',
                '  fi',
                '  echo "" && echo "##[error]Process completed with exit code $EXIT_CODE."',
                ''
            ]

            if 'id' in s.step:
                step_id = str(s.step['id'])
                conclusion_var = '_CONTEXT_STEPS_{}_CONCLUSION'.format(re.sub(r'\W', '_', step_id.upper()))
                outcome_var = '_CONTEXT_STEPS_{}_OUTCOME'.format(re.sub(r'\W', '_', step_id.upper()))
                lines += [
                    '  ' + outcome_var + '=failure',
                    '  if [[ "$CONTINUE_ON_ERROR" != "true" ]]; then ',
                    '    ' + conclusion_var + '=failure',
                    '  else',
                    '    ' + conclusion_var + '=success',
                    '  fi',
                    'else',
                    '  ' + outcome_var + '=success',
                    '  ' + conclusion_var + '=success',
                ]

            lines += [
                'fi',  # if [[ $EXIT_CODE != 0 ]]
                'fi',  # if [[ "$STEP_CONDITION" = "true" ]]
            ]

    lines += [
        '',
        'if [[ $_GITHUB_JOB_STATUS != "success" ]]; then',
        '   exit 1',
        'fi'
    ]

    log.debug('Writing build script to {}'.format(output_path))
    content = ''.join(map(lambda l: l + '\n', lines))
    with open(output_path, 'w') as f:
        f.write(content)


def run_with_envs(envs, command):
    return 'env {}\\\n{}'.format(envs, command)


def resolve_exprs(envs, value):
    command = "echo {}".format(value)
    return '$({})'.format(run_with_envs(envs, command))
