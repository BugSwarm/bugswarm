# Analyzer

## Description
The BugSwarm build log analyzer is a Python-based tool that extracts information from build logs of Java and Python projects from both Travis CI and GitHub Actions. It was initially derived from the [TravisTorrent build log analyzer](https://github.com/TestRoots/travistorrent-tools) by porting it to Python. Since then, it has undergone significant refactoring, bug fixing, and feature additions.

## Java Log Analyzer
- Supports build log from Ant, Maven, and Gradle.
- Supports test frameworks JUnit and testng.

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
$ python3 entry.py -l <path_to_log> -j <job_id> (-t <trigger_sha> --repo <repo_slug> |  -b <build_system>) --mining <true/false>
```
Add the `--print` option to print the attributes extracted from the log.

Example: `$ python3 entry.py -l 23434234.log -j 23434234`

This example will run the Python analyzer on `23434234.log`. `23434234.log` is the path to the log you want to analyze and `23434234` is the job id of the log.

### Comparing reproduced logs with original logs
```
$ python3 entry.py -r <path_to_single_reproduced_log> \
                   -o <path_to_orig_log> -j <job_id> \
                   (-t <trigger_sha> --repo <repo_slug> |  -b <build_system>) \
                   --mining <true/false>
```
> Log filenames should be the job ID of the job.

Example: `$ python3 entry.py -r 45123523.log -o 45123523-orig.log -j 45123523`

This example will compare the reproduced log `45123523.log` with the original log `45123523-orig.log`. `45123523.log` is the path to the reproduced log, `45123523-orig.log` is the path to the original log, and `45123523` is the job id of the logs.

## Running the tests
> Requires [nose](http://nose.readthedocs.io).
```
$ python3 tests.py
```
> Run this command from tests/analyzer so that test files are correctly imported.
