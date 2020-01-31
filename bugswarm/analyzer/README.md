# Analyzer

## Description
`analyzer` extracts information from Travis build logs.

The BugSwarm build log analyzer is derived from the [TravisTorrent build log analyzer](https://github.com/TestRoots/travistorrent-tools). Before extending the TravisTorrent analyzer, we ported it to Python.

The BugSwarm analyzer fixes some problems present in the TravisTorrent analyzer and also supports additional features. See the [wiki page](https://github.com/BugSwarm/analyzer/wiki/Differences-from-original-TravisTorrent-Build-Log-Analyzer) for more details.

## Motivation
We implemented a new build log analyzer because
- some features of the TravisTorrent analyzer were unreliable in some cases. For example, the TravisTorrent analyzer sometimes used the wrong build system-specific analyzer, failed to capture the number of tests, and failed to capture the names of failing tests correctly
- we wanted the flexibility to add features

## Python Log Analyzer
- Supports unittest, unittest2, nose, and pytest.
- Reports unittest2 and nose as unittest as their outputs are the same.
   
## Dependencies 
- Python 3
- To run the test suite, you will also need [nose](http://nose.readthedocs.io).

    `$ pip3 install nose`

## Run
### Analyzing a single log
```
$ python3 entry.py -l <path_to_log> -j <job_id> (-t <trigger_sha> --repo <repo_slug> |  -b <build_system>)
```
Add the `--print` option to print the attributes extracted from the log.

### Comparing reproduced logs with original Travis logs
```
$ python3 entry.py -r <path_to_single_reproduced_log> \
                   -o <path_to_orig_log> -j <job_id> \
                   (-t <trigger_sha> --repo <repo_slug> |  -b <build_system>)
                   (-t <trigger_sha> --repo <repo_slug> |  -b <build_system>)
```
> Log filenames should be the job ID of the Travis job.

## Running the tests
> Requires [nose](http://nose.readthedocs.io).
```
$ python3 tests.py
```
> Run this command from tests/analyzer so that test files are correctly imported.
