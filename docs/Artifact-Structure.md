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
'filtered_out_reason': string               # e.g. 'no head sha'
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
'pr_num':        integer                    # e.g. 379
'repo':          string                     # e.g. 'gwtbootstrap3/gwtbootstrap3'
'repo_builds':   integer                    # e.g. 342
'repo_commits':  integer                    # e.g. 853
'repo_members':  integer                    # e.g. 4
'repo_prs':      integer                    # e.g. 225
'repo_watchers': integer                    # e.g. 311
'reproduced':    bool                       # e.g. True or False
'stable':        bool                       # e.g. True or False
'tag':           string                     # e.g. '74924751'
`classification`: {                         #
    'code':       string                    # e.g. 'Yes'
    'build':      string                    # e.g  'No'
    'test':       string                    # e.g. 'Partial'
    'exceptions': [string]                  # e.g. ['NullPointerException', ...]
}                                           #
```
 
| Attribute                                      | Type        | Description                    |
| ---------------------------------------------- | ----------- | ------------------------------ |
| `base_branch`                                  | `string`    | The branch into which pull request changes are merged. Only valid on pairs from pull requests. |
| `branch`                                       | `string`    | The branch from which pull request changes are merged. Only valid on pairs from pull requests. |
| `filtered_out_reason`                          | `string`    | If the pair was marked as not suitable for reproducing by `pair-filter`, then this attribute contains a human-readable reason for `pair-filter`'s decision. |
| `image_tag`                                    | `string`    | The tag identifying the Docker image associated with this artifact. |
| `is_error_pass`                                | `bool`      | Whether the artifact contains an error-pass pair (rather than a fail-pass pair). |
| `lang`                                         | `string`    | The language of the build, as indicated by a project's travis.yml file. |
| `match`                                        | `integer`   | The match type for the pair. Only valid if `reproduced` is `true`. |
| `merged_at`                                    | `timestamp` | The time when the pull request associated with the pair was merged. Only valid on pairs from pull requests. |
| `pr_num`                                       | `integer`   | The number uniquely identifying the pull request within this project. Only valid on pairs from pull requests. |
| `repo`                                         | `string`    | The repository slug that identifies a project on GitHub. |
| `repo_builds`                                  | `integer`   | ??? |
| `repo_commits`                                 | `integer`   | ??? |
| `repo_members`                                 | `integer`   | ??? |
| `repo_prs`                                     | `integer`   | ??? |
| `repo_watchers`                                | `integer`   | ??? |
| `reproduced`                                   | `bool`      | Whether `reproducer` attempted to build the pair. This attribute will be `false` if a pair was marked as not suitable for reproducing by `pair-filter`. |
| `stable`                                       | `bool`      | ??? Only valid if `reproduced` is `true`. |
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
| `classification.code`                          | `string`    | The patch classification for code related files.
| `classification.build`                         | `string`    | The patch classification for build related files.
| `classification.test`                          | `string`    | The patch classification for test related files.
| `classification.exceptions`                    | `[string]`    | The list of exceptions thrown during the failed Travis CI Job.

## Updating metadata schema
To add, remove, or change a field in the artifact schema, one must update code in multiple places:
1. Add or update the key in `_flatten_keys` in `packager.py`.
1. Set the appropriate value for the key in `_structure_artifact_data` in `packager.py`.
1. Add or update the key in `artifact_schema.py` in the `database` repository.
1. Add or update the key in the table above.
1. If changing or removing a key, update code that uses the old key.

Also, consider whether the artifact browser on the website needs to be updated to reflect your change.

## Artifact Docker image
Each artifact is associated with a Docker image, which is capable of building the environment needed to reproduce both jobs in a job pair.

### Important files in the Docker container
- Failing repository: `/home/travis/build/failed`
- Passing repository: `/home/travis/build/passed`
- Script to run failed build: `/usr/local/bin/run_failed.sh`
- Script to run passed build: `/usr/local/bin/run_passed.sh`

### Running an artifact image with Docker
> Requirement: [Docker](https://www.docker.com)
```
$ docker run -it bugswarm/artifacts:<tag> /bin/bash
```
> `<tag>` is the failed job ID of the job pair.
For example, `$ docker run -it bugswarm/artifacts:53517141 /bin/bash` pulls the job pair image from Docker Hub, spawns a Docker container, and starts a shell for that container.
- Add tools to the container or modify the repository as needed for your experiment.
- Run the build
  - Run the failed build
    ```
    $ bash /usr/local/bin/run_failed.sh
    ```
  - Run the passed build
    ```
    $ bash /usr/local/bin/run_passed.sh
    ```
- If you prefer to run the build immediately, add an argument to the `docker run` command:
  ```
  $ docker run -it bugswarm/artifacts:<tag> <script_to_run_build>
  ```
  > `<script_to_run_build>` can be a custom script or one of the scripts described above.

  For example, to directly run the failed build of a job pair, run
  ```
  $ docker run -it bugswarm/artifacts:53517141 /usr/local/bin/run_failed.sh
  ```

## Running artifacts and viewing metadata via the BugSwarm Client
See the BugSwarm client repository [README](https://github.com/BugSwarm/client).
