# Artifact Structure

## Overview
BugSwarm artifacts consist of two discrete parts: the artifact metadata and the artifact Docker image.

## Metadata schema
Each artifact is associated with a subset of the following attributes. The attributes are described in more detail in the table that follows.
```bash
'_id':         ObjectId(string)             # Set by MongoDB
'base_branch': string                       # e.g. 'master'
'branch':      string                       # e.g. 'my-new-feature'
'failed_job': {                             # Job object
    'base_sha':                string       #   e.g. '1234abc'
    'build_id':                integer      #   e.g. 12345678
    'build_job':               string       #   e.g. '140.1'
    'committed_at':            timestamp    #   e.g. '2015-08-10T14:26:08Z'
    'failed_tests':            string       #   e.g. 'testHelloWorld#testPrintLn'
    'job_id':                  integer      #   e.g. 12345679
    'message':                 string       #   e.g. '- Updated to 4.4.0\n- Added pulse icon support'
    'mismatch_attrs':          [string]     #   e.g. ['num_tests_run', 'num_tests_failed', ...]
    'num_tests_failed':        integer      #   e.g. 3
    'num_tests_run':           integer      #   e.g. 16
    'reproducer_error_reason': string       #   e.g. 'this is the error reason'
    'trigger_sha':             string       #   e.g. '1234xyz'
},                                          #
'filtered_reason':     string               # e.g. 'no head sha'
'image_tag':           string               # e.g. '74924751'
'is_error_pass':       bool                 # e.g. True or False
'lang':                string               # e.g. 'Java'
'match':               integer              # e.g. 2
'merged_at':           timestamp            # e.g. '2015-08-18T12:30:27Z'
'passed_job': {                             # Job object
    'base_sha':                string       #   e.g. '5678def'
    'build_id':                integer      #   e.g. 98765432
    'build_job':               string       #   e.g. '141.1'
    'committed_at':            timestamp    #   e.g. '2015-08-10T16:21:24Z'
    'failed_tests':            string       #   e.g. ''
    'job_id':                  integer      #   e.g. 74943870
    'message':                 string       #   e.g. 'Replaced tab to white space.'
    'mismatch_attrs':          [string]     #   e.g. ['tr_log_status', ...]
    'num_tests_failed':        integer      #   e.g. 0
    'num_tests_run':           integer      #   e.g. 16
    'reproducer_error_reason': string       #   e.g. 'this is the error reason'
    'trigger_sha':             string       #   e.g. '7890uvw'
},                                          #
'pr_num':               integer             # e.g. 379
'repo':                 string              # e.g. 'gwtbootstrap3/gwtbootstrap3'
'reproduced':           bool                # e.g. True or False
'tag':                  string              # e.g. 'gwtbootstrap3-gwtbootstrap3-92837490'
'build_system':         string              # e.g. 'Maven'
'reproduce_attempts':   integer             # e.g. '5'
'reproduce_successes':  integer             # e.g. '5'
'stability':            string              # e.g. '5/5'
'test_framework':       string              # e.g. 'JUnit'
'classification': {                         #
    'code':       string                    # e.g. 'Yes'
    'build':      string                    # e.g  'No'
    'test':       string                    # e.g. 'Partial'
    'exceptions': [string]                  # e.g. ['NullPointerException', ...]
},
'cached':             bool                  # e.g. True or False
'status':             string                # e.g. 'active'
'added_version':      string                # e.g. '1.1.2'
'deprecated_version': string                # e.g. '1.2.0'
```
 
| Attribute                                      | Type        | Description                    |
| ---------------------------------------------- | ----------- | ------------------------------ |
| `base_branch`                                  | `string`    | The branch into which pull request changes are merged. Only valid on pairs from pull requests. |
| `branch`                                       | `string`    | The branch from which pull request changes are merged. Only valid on pairs from pull requests. |
| `filtered_reason`                              | `string`    | If the pair was marked as not suitable for reproducing by `pair-filter`, then this attribute contains a human-readable reason for `pair-filter`'s decision. |
| `image_tag`                                    | `string`    | The tag identifying the Docker image associated with this artifact. |
| `is_error_pass`                                | `bool`      | Whether the artifact contains an error-pass pair (rather than a fail-pass pair). |
| `lang`                                         | `string`    | The language of the build, as indicated by a project's travis.yml file. |
| `match`                                        | `integer`   | The match type for the pair. Only valid if `reproduced` is `true`. Otherwise, the default value is empty string ''. |
| `merged_at`                                    | `timestamp` | The time when the pull request associated with the pair was merged. Only valid on pairs from pull requests. |
| `pr_num`                                       | `integer`   | The number uniquely identifying the pull request within this project. Only valid on pairs from pull requests. The default value is `-1` if pairs are not from pull requests. |
| `repo`                                         | `string`    | The repository slug that identifies a project on GitHub. |
| `reproduced`                                   | `bool`      | Whether `reproducer` attempted to build the pair. This attribute will be `false` if a pair was marked as not suitable for reproducing by `pair-filter`. |
| `tag`                                          | `string`    | This attribute is the same as the `image_tag` attribute. |
| `[failed\|passed]_job.base_sha`                | `string`    | The SHA of the commit that was merged with `trigger_sha` to create the Travis virtual commit used for the Travis build. |
| `[failed\|passed]_job.build_id`                | `integer`   | The number uniquely identifying the build on Travis. |
| `[failed\|passed]_job.build_job`               | `string`    | The dot-separated pair of numbers uniquely identifying the job within this Travis project. |
| `[failed\|passed]_job.committed_at`            | `timestamp` | The timestamp associated with `base_sha` (i.e. when the virtual commit was created). |
| `[failed\|passed]_job.failed_tests`            | `string`    | A pound symbol-separated list of failed test names. This attribute is not reliable at this time. |
| `[failed\|passed]_job.job_id`                  | `integer`   | The number uniquely identifying the job on Travis. |
| `[failed\|passed]_job.message`                 | `string`    | The commit message associated with `trigger_sha`. |
| `[failed\|passed]_job.mismatch_attrs`          | `[string]`  | The attributes, if any, that did not match when extracted from the original build log and the reproduced build log. |
| `[failed\|passed]_job.num_tests_failed`        | `integer`   | The number of tests failed during the Travis build. |
| `[failed\|passed]_job.num_tests_run`           | `integer`   | The number of tests executed during the Travis build. |
| `[failed\|passed]_job.reproducer_error_reason` | `string`    | If `reproducer` encounters an error, this attribute contains a human-readable reason for the error. |
| `[failed\|passed]_job.trigger_sha`             | `string`    | The SHA of the commit that, after being pushed to GitHub, triggered the Travis build. |
| `test_framework`                               | `string`    | The test framework for both jobs. Empty string if the `analyzer` failed to find the framework. |
| `reproduce_attempts`                           | `integer`   | The number of times the reproducer ran. |
| `reproduce_successes`                          | `integer`   | The number of times the job was completed as expected. |
| `stability`                                    | `string`    | The proportion of times the job completed as expected. The format is `reproduce_successes`/`reproduce_attempts` |
| `reproducibility_status.time_stamp`            | `timestamp` | The date at which `reproducibility_status.status` was last calculated.
| `reproducibility_status.status`                | `string`    | The artifact's reproducibility: `Unreproducible`, `Flaky`, or `Reproducible`.
| `classification.code`                          | `string`    | The patch classification for code related files.
| `classification.build`                         | `string`    | The patch classification for build related files.
| `classification.test`                          | `string`    | The patch classification for test related files.
| `classification.exceptions`                    | `[string]`  | The list of exceptions thrown during the failed Travis CI Job.
| `cached`                                       | `bool`      | Whether the artifact has been cached. If true, the artifact is present in the `bugswarm/cached-images` Docker repository.
| `status`                                       | `string`    | The artifact's status in the dataset. One of `active` (an official artifact), `candidate` (not officially added to the dataset), or `deprecated` (removed from the dataset).
| `added_version`                                | `string`    | The version of the dataset that this artifact was officially added in. Null if `status` == `candidate`.
| `deprecated_version`                           | `string`    | The version of the dataset that this artifact was deprecated in, or null if the artifact has not been deprecated.

## Updating metadata schema
To add, remove, or change a field in the artifact schema, one must update code in multiple places:
1. Add or update the key in `_flatten_keys` in `reproducer/packager.py`.
1. Set the appropriate value for the key in `_structure_artifact_data` in `reproducer/packager.py`.
1. Add or update the key in `artifact_schema.py` in the `database` repository.
1. Add or update the key in the table above.
1. If changing or removing a key, update code that uses the old key.


## Artifact Docker image
Each artifact is associated with a Docker image, which is capable of building the environment needed to reproduce both jobs in a job pair.

### Important files in the Docker container
- Failing repository: `/home/travis/build/failed`
- Passing repository: `/home/travis/build/passed`
- Script to run failed build: `/usr/local/bin/run_failed.sh`
- Script to run passed build: `/usr/local/bin/run_passed.sh`

### Running artifacts using BugSwarm Client
To learn more, see the BugSwarm client repository [README](https://github.com/BugSwarm/client).

> Requirements: [Docker](https://www.docker.com) and Python 3.
> 
```
$ pip3 install bugswarm-client
```

```shell
$ bugswarm run --image-tag <image_tag>
```
> `<image_tag>` is the image tag for BugSwarm artifact.

For example, `$ bugswarm run --image-tag Abjad-abjad-316134246` pulls the job pair image from Docker Hub, spawns a Docker container, and starts a shell for that container.

- Run the build
  - Run the failed build
    ```
    $ bash /usr/local/bin/run_failed.sh
    ```
  - Run the passed build
    ```
    $ bash /usr/local/bin/run_passed.sh
    ```
