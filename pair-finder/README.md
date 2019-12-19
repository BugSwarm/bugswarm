# Pair Finder
`PairFinder` is a component in the [BugSwarm](https://bugswarm.github.io) pipeline that identifies fail-pass and error-pass build pairs by leveraging the [GitHub API](https://developer.github.com/v3) and the [Travis API](https://github.com/travis-ci/travis.rb) to reconstruct and then inspect project build history.

## Usage
```
$ python3 pair_finder.py OPTIONS

    -r, --repo          Repo slug. Cannot be used with --repo-file.
    --repo-file         Path to file containing a newline-separated list of repo slugs. Cannot be used with --repo.
    -t, --threads       Maximum number of worker threads. Defaults to 1.
    --log               Log level. Use CRITICAL (lowest), ERROR, WARNING, INFO (default), or DEBUG (highest).
    --keep-clone        Prevent the default cleanup of the cloned repo after running.
    -h, --help          Display help
```

_Examples:_
##### Find pairs for a single repository
```
$ python3 pair_finder.py -r numpy/numpy
```

##### Find pairs for multiple repositories
First, create a newline-separated list of repository slugs.
Assume the file is named `repos.txt` and is located in `/home`.

The file should look like this:
```
numpy/numpy
HubSpot/Singularity
square/okhttp
google/guice
...
```
Then pass the path to your file with the `--repo-file` argument.
```
$ python3 pair_finder.py --repo-file /home/repos.txt
```

## Output
### JSON Files
`PairFinder` creates a JSON file for each repository on which it is invoked.

The output JSON files are located in the `output` directory and contain:
- an array of pairs that `PairFinder` identified (see the `pairs` key)
- statistics about the identified pairs (see the `stats` key)
- metadata about the `PairFinder` job (see the `duration` and `generated_at` keys)
- the intermediate output of each step in the pair finding pipeline (see the `intermediates` key)

The structure of an output file looks like this:

```
{
  "generated_at": "",
  "duration": "",
  "pairs": [
    {
      "pr_num": "",
      "repo": "",
      "failed_build": {
        ...
      },
      "passed_build": {
        ...
      }
    },
    ...
  ],
  "stats": {
    ...
  },
  "intermediates": {
    ...
  }
}
```

### Log Files
`PairFinder` also creates a log file for each repository on which it is invoked.

The log files are located in the `intermediates/logs` directory. If an older log for a repository exists, `PairFinder`
replaces it during the next run.
