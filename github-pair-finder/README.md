# Github Actions PairFinder

This is a version of PairFinder that mines Github Actions jobs instead of Travis jobs. It is designed to mimic the structure of the Travis pipeline, with several files being extremely similar if not outright identical to their Travis counterparts. This means that it should be possible to add the Github Actions pipeline to the main pipeline without too much hassle.

## Usage

```
$ python3 pair_finder.py (-r REPO | --repo-file REPO_FILE) [args...]
```

- `-r / --repo <repo>`: The repo to mine. Cannot be used with `--repo-file`.
- `--repo-file <path>`: Path to a file containing a newline-separated list of repos to mine. Cannot be used with `--repo`.

### Optional arguments
- `-t / --threads <n>`: Maximum number of worker threads. Only useful if mining more than one repo. Defaults to 1.
- `--log <level>`: Log level. One of `CRITICAL` (least verbose), `ERROR`, `WARNING`, `INFO` (default), or `DEBUG` (most verbose).
- `--last-run-override <n>`: Override the run ID of the last run that was mined for a repo. The miner will mine all runs from all given repos with an ID greater than N. Use with caution, especially with `--repo-file` &mdash; this will mess up the database metrics.
- `--keep-clone`: Prevent the cloned repo in `intermediates/repos/<repo-name>` from being cleaned up at the end of the run.
- `--fast`: Skip mining repos that already have an output file.
- `--no-cutoff-date`: Disable the 400-day mining limit, so workflow runs older than 400 days can be mined. Note that if a repo has already been mined, only runs newer than the last run of that repo at the time will be mined unless `--last-run-override` is provided.

### Run Tests

Make sure you're in the pair-finder directory, and then run

```
$ python3 -m unittest
```

## Pipeline Outline

Note that not all steps in the Travis pipeline have Github equivalents. Specifically, the Travis pipeline has several steps dealing with how Travis handles PR builds, none of which are applicable to Github Actions.

| Step                 | Travis Pipeline Equivalent | Description                                                                                                                                                                                                                                                                          |
| -------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Preflight | Preflight | Clones the repo and gets the list of all commit SHAs in that repo (later used by CheckBuildIsResettable).
| GetJobsFromGitHubAPI | GetJobsFromTravisAPI       | Fetches information about every job run in a repo from Github's API. All jobs will be from workflow runs with IDs > `last-run-id`.                                                                                                                                                   |
| GroupJobs            | GroupJobsByBranch          | Groups jobs by both their workflow ID and the branch they were run on. (The Travis pipeline only groups jobs by their branch.) Otherwise mostly the same as the Travis version.                                                                                                      |
| ExtractAllBuildPairs | ExtractAllBuildPairs       | Finds fail/pass and error/pass build pairs in each branch-workflow combination. Copied directly from the Travis pipeline.                                                                                                                                                            |
| ConstructJobConfig   | ---                        | Adds `config` parameters to each job by parsing their workflow YML files and determining what matrix values were used for that job. No equivalent in the Travis pipeline, since the Travis API exposes a `config` parameter for us already.                                          |
| AlignJobPairs        | AlignJobPairs              | Searches for fail/pass job pairs with the same `config` within each build pair. Almost identical to its Travis counterpart -- they have all but 1 line in common.                                                                                                                    |
| CheckBuildIsResettable | --- | Checks that each build pair's commit can be reset to, either by checking out the commit SHA or by downloading the repo at that commit from GitHub. |
| GetBuildSystemInfo | GetBuildSystemInfo | Figures out which build system each build in a pair is using. |
| CleanPairs           | CleanPairs                 | Last-second sanity checks on the job pairs. Almost identical to its Travis counterpart, with only one difference -- the Travis version finds the latest commit in the repo by cloning the repo and running `git rev-parse HEAD`, while this version makes a single API call instead. |
| Postflight | Postflight | Deletes the repo clone that was created in Preflight.