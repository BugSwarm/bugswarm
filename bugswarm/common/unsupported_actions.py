"""
Unsupported actions:
Reproducer will skip the step if the action's name is in list.
generate_pair_input by default will also exclude job pairs if their failed step name is in this.

Special actions:
Reproducer will not download the action from GitHub and will replace it with the custom action from
the reproducer/resources directory.
"""

UNSUPPORTED_ACTIONS = {
    'codecov/codecov-action',
    'actions/upload-artifact',
    'actions/download-artifact',
    'actions/cache',
    'gradle/wrapper-validation-action',
    'styfle/cancel-workflow-action',
    'github/codeql-action'
}
SPECIAL_ACTIONS = {'actions/checkout'}
