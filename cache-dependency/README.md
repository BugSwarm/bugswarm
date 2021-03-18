# Cache Dependency

## Overview
![The Overview](./resources/figures/process.png)
CacheDependency is a automated tool for caching BugSwarm artifacts' dependencies.
In following this README, we will run the tool to generate results and then evaluate those results.

## Requirements:
1. Docker Client
1. BugSwarm credential configured
1. Disk Space > 30 GB
1. Python >= 3.6


## Usage
**First `docker login` to the desired repository**

```
python3 CacheMaven.py <image-tag-file> <task-name> [arguments]
python3 CachePython.py <image-tag-file> <task-name> [arguments]
```

* `image-tag-file`: Path to a file containing a newline-separated list of image tags to process.
* `task-name`: A unique name assigned to this invokation of the caching script. The name should match regular expression `[a-zA-Z0-9\-\_]+`.
    * Results will be put in `output/<task-name>.csv`.
    * Temporary files will be put in `~/bugswarm-sandbox/<task-name>/<image-tag>/` (a.k.a. work directory)
    * Docker containers' names will start with `<task-name>-`.
    * Temporary container images will be placed into the `<task-name>` repository.
* `--workers`: Set number of worker threads in the script.
* `--no-push`: Do not push to destination repository at the end.
* `--src-repo`: Source repository (e.g. `bugswarm/images`)
* `--dst-repo`: Destination repository (e.g. `bugswarm/cached-images`)
* `--keep-tmp-images`: Do not remove temporary container images in the temporary repository `<task-name>`.
* `--keep-containers`: Do not remove intermediate containers during the build script for debugging (will consume a lot of disk space).
* `--keep-tars`: Do not remove tar files in the work directory.

### Java only options
* `--no-copy-*`: Do not copy specific directories (e.g. `~/.m2`, `~/.gradle`, `~/.ivy2`)
* `--no-remove-maven-repositories`: Do not remove `_remote.repositories` and `_maven.repositories`.
* `--ignore-cache-error`: Ignore error when running build script to download
  cached files.
* `--no-strict-offline-test`: Do not apply strict offline mode when testing.
* `--separate-passed-failed`: Separate passed and failed cached files. Will fix
  some Java artifacts, but will increase artifact size.

### Python only options
* `--parse-new-log`: Instead of parsing the original build log, reproduce the
  artifact and parse this new log.


## Algorithm
1. Download cached files
    * For Java artifacts, setup localRepositories and run the build script,
      then copy files in localRepositories out as tar files.
        * If the build script fails for either the failed job or the passed job,
          caching will fail.
    * For Python artifacts, parse the build log (downloaded from Travis
      CI) to determine the list of packages to be downloaded, and then download
      the files using a Python container (e.g. `python:3.7-slim`).
    	* By default the original build log is parsed.
    	* The user can choose to reproduce the artifact and parse this new log
    	  using `--parse-new-log`.
2. Create a new container from `src-repo`
    * Setup build system configurations (e.g. offline mode, local repository)
    * Put downloaded files into it.
    * Commit it to an image, in a temporary repository `<task-name>`.
3. Test the temporary image (similar to what bugcatcher does)
    * For Java, testing is more strict, in the sense that all Gradle and Maven
      commands will be forced to run in offline mode (by modifying the binary).
4. If testing passes, copy the image from the temporary repository to `dst-repo`
    * If `--no-push` is not set, push the image to `dst-repo`.


## Output
Output files are placed in the `output` directory.

Each line in the output file follows this format:
```
image-tag, "succeed" or error message, original-size, increased-size
```

1. `image-tag`: The name of the image tag attempted to be cached.
2. `succeed`: If caching is succeeded; an error message otherwise.
3. `original-size`: The size of the original Docker image. If dependencies could not be cached, `-`.
4. `increased-size`: How much the artifact's Docker image increased in size after its dependencies were cached.
   If dependencies could not be cached, `-`.


## Workspace directory
Temporary files will be stored in `~/bugswram-sandbox/<task-name>/<image-tag>/`
* `log.txt`: Log for only this image-tag (should be looked at first for debugging).
* `orig-{failed,passed}-<travis-job-id>.log`: Original log downloaded.
* `cache-{failed,passed}.log`: For Java, log in caching stage (step 1 in the algorithm).
* `test-{failed,passed}.log`: Log in testing stage (step 3 in the algorithm).
* `*.log.cmp`: Result of running `compare_single_log()` on `*.log` with the original log.
* `home-m2-{failed,passed}.log` etc.: Cached files for Java build systems.
    * A complete list is at `CACHE_DIRECTORIES` in `CacheMaven.py`
* `requirements-{failed,passed}-*.tar`: Cached files for Python build systems.


## Example
### Java
Create a file `image-tag-java` which contains `Adobe-Consulting-Services-acs-aem-commons-427338776`
Then run: 
```
python3 CacheMaven.py image-tag-java java-test --dst-repo temp-dst-repo
```

You should be able to see the result in `output/java-test.csv`.

You should be able to see intermediate files in `~/bugswarm-sandbox/java-test/Adobe-Consulting-Services-acs-aem-commons-427338776/`

You should be able to see `java-test:Adobe-Consulting-Services-acs-aem-commons-427338776` and `temp-dst-repo:Adobe-Consulting-Services-acs-aem-commons-427338776` created

### Python
Create a file `image-tag-python` which contains `Abjad-abjad-289716771`
Then run: 
```
python3 CachePython.py image-tag-python python-test --dst-repo temp-dst-repo
```

You should be able to see the result in `output/python-test.csv`

You should be able to see intermediate files in `~/bugswarm-sandbox/python-test/Abjad-abjad-289716771/`

You should be able to see `python-test:Abjad-abjad-289716771` and `temp-dst-repo:Abjad-abjad-289716771` created


## Caching Details

### Maven build

#### Old script (before Mar 1, 2021)
1. Patched the configuration file to specify the maven cache path for passed and failed job.
1. Runs the failed and passed jobs using `run_failed.sh` and `run_passed.sh`, caching the dependencies in the process.
1. Add offline flag in the build script to utilize the local dependencies

#### New Script (after Mar 1, 2021)
1. Maven cache path for passed and failed job are all falling back to the default.
1. Runs the failed and passed jobs using `run_failed.sh` and `run_passed.sh`, caching the dependencies in the process.
1. When packing cached artifact, add offline flag in the build script to utilize the local dependencies.
   When testing cached artifact, add offline flag in Maven and Gradle binary.

### Python
1. Parse the original logs to get a list of dependencies and versions.
1. Based on python/pip version, we initiate a docker container with same `python version` to download packages via `pip download`.
1. Copy them into the artifact(`failed/requirements/`, `passed/requirements/`).
1. Patch build script with `--no-index --find-link` to utilize the download dependencies.


## Unit tests for log parser
```
cd tests
python3 -m test_python_log_parser
```
