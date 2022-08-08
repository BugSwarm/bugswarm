# Github Actions PairFinder

This is a version of PairFinder that mines Github Actions jobs instead of Travis jobs. It is designed to mimic the structure of the Travis pipeline, with several files being extremely similar if not outright identical to their Travis counterparts. This means that it should be possible to add the Github Actions pipeline to the main pipeline without too much hassle.

## Usage

```
$ python3 run.py <repo> <last-run-id> [-o/--out-file <out-file>]
```

- `repo`: The repo to mine.
- `last-run-id`: The ID of the last workflow run mined in a previous run. All mined workflow runs will have IDs greater than this value. In the real pipeline, this will be obtained from the database.
- `out-file`: The file to dump the JSON output into. Defaults to `out_data.json`.

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