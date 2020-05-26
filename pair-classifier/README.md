# Pair Classifier
`pair-classifier` classifies and labels Travis CI job pairs in different categories so that we can be selective during the
reproducing stage.

`pair-classifier` populate the classification attributes of each job pair with [build classification](#classifier), [test classification](#classifier), [code classification](#classifier) and [list of exceptions](#classifier).

Later in the pipeline for Reproducer, `generate_pair_input.py` can be used to select job pairs with certain classification. 

## Usage
```
$ Usage: python3 pair-classifier.py (-r <repo-slug> | --repo-file <repo-file>) [OPTION]

    -r, --repo          Repo slug. Cannot be used with --repo-file.
    --repo-file         Path to file containing a newline-separated list of repo slugs. Cannot be used with --repo.

    OPTION:
        --log-path      Path to the directory where original logs were stored. If not provided, classifier
                        will try to download the logs.
        --pipeline      Flag set to true for when script is ran with run_mine_project.sh for processing.
```
_Example:_
```
$ python3 pair-classifier.py -r Flipkart/foxtrot
```

## Classifier
`pair-classifier` currently adds the following classification information to job pairs in the `minedBuildPairs` collection 
in the Database:
1. `build classification`: classifier determines the build classification based on the `percentage` from the formula: 
    <pre>
    percentage = Number of <b>build</b> files changed / number of total files changed</pre>
    The classifier will assign `Yes` to `build classification` if `percentage == 1`, `No` to `build classification`
if `percentage == 0`, `Partial` to `build classification` if `0 < percentage < 1` 
1. `test classification`: Similar to `build classification`, but the formula is:
    <pre>
    percentage = Number of <b>test</b> files changed / number of total files changed</pre>
1. `code classification` Similar to `build classification`, but the formula is:
    <pre>
    percentage = Number of <b>code</b> files changed / number of total files changed</pre>
1. `list of exceptions` list of exceptions that are thrown at run time that involve both integrated tests and 
compilation errors within the failed job log.

## Output
`pair-classifier` updates the `mineBuildPairs` collection in the Database with the classification information.
An example entry would be like:
```
{
    "repo" : "checkstyle/checkstyle",
    "failed_build" : {
        "build_id" : 270800483,
        ...
        "jobs" : [
            {
                "build_job" : "12377.9",
                "job_id" : 270800497,
                "config" : {
                    ...
                },
                "language" : "java"
            }
        ]
    },
    "passed_build" : {
        "build_id" : 270994341,
        ...
        "jobs" : [
            {
                "build_job" : "12390.9",
                "job_id" : 270994350,
                "config" : {
                    ...
                },
                "language" : "java"
            }
        ]
    },
    "jobpairs" : [
        {
            "classification" : {
                "code" : "Partial",
                "test" : "Partial",
                "build" : "Partial",
                "exceptions" : [
                    "ComparisonFailure",
                ],
            },
            "passed_job" : {
                ...
                "job_id" : 270994350
            },
            "filtered_reason" : null,
            "failed_job" : {
                ...
                "job_id" : 270800497
            }
        },
        ...
    ],
}
```
