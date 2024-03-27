"""
Defines 3 sets of actions that are treated specially by the GitHub Actions
Reproducer.

`UNSUPPORTED_ACTIONS`:
For actions that (1) don't work with the current version of the Reproducer (e.g.
require secrets or tokens) and (2) are likely to cause jobs to fail if they're
just skipped.
`generate_pair_input.py` by default will exclude job pairs if their failed step
uses one of these actions.

`SKIPPED_ACTIONS`:
For actions that don't work with the current version of the Reproducer but can
usually be safely skipped.
The Reproducer will skip steps that use these actions.

`SPECIAL_ACTIONS`:
The reproducer will not download the action from GitHub and will replace it with
a custom action from the reproducer/resources directory.
"""

UNSUPPORTED_ACTIONS = {
    'actions/download-artifact',
}


SKIPPED_ACTIONS = UNSUPPORTED_ACTIONS | {
    'codecov/codecov-action',
    'actions/upload-artifact',
    'actions/download-artifact',
    'actions/cache',
    'gradle/wrapper-validation-action',
    'styfle/cancel-workflow-action',
    'github/codeql-action',
    'peaceiris/actions-gh-pages',
    's0/git-publish-subdir-action',
    'madrapps/jacoco-report',
    'mikepenz/action-junit-report',
}


SPECIAL_ACTIONS = {'actions/checkout'}
