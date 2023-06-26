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
* `--disconnect-network-during-test`: When testing the newly cached artifacts, disconnect the docker container from the
  network using `--network none`.

### Java only options
* `--no-copy-*`: Do not copy specific directories (e.g. `~/.m2`, `~/.gradle`, `~/.ivy2`)
* `--no-remove-maven-repositories`: Do not remove `_remote.repositories` and `_maven.repositories`.
* `--ignore-cache-error`: Ignore error when running build script to download
  cached files.
* `--no-strict-offline-test`: Do not apply strict offline mode when testing.
* `--no-separate-passed-failed`: Do not separate passed and failed caches. May decrease artifact size, but may also
  break certain artifacts.

### Python only options
* `--parse-original-log`: Instead of using the output of pip freeze on the reproduced
  artifact and then downloading them in the same container, use the old method of parsing
  the orginal build logs to find a list of dependencies then download them to an intermediate container.
* `--parse-new-log`: Like parse-original-log but instead of parsing the original
  build log, reproduce the artifact and parse this new log.


## Algorithm
1. Download cached files in containers and copy them out as tar files
    * For Java artifacts, setup localRepositories and run the build script,
      then copy files in localRepositories out.
        * If the build script fails for either the failed job or the passed job,
          caching will fail.
    * For Python artifacts run the build script then use pip freeze to get a
      list of all installed packages and versions, also check all anaconda 
      environments, if any, for any additional packages. Next use pip to download
      all the packages on the list, and then copy the files out.
        * For Python artifacts using the `parse-original-log` or `parse-new-log` 
          options, parse the build log (either the original build log 
          downloaded from Travis-CI or a newly reproduced build log from running the
          build script, depending upon which option is used) to determine the list
          of packages to be downloaded, and then download the files using a Python
          container (e.g. `python:3.7-slim`).
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
* `{failed,passed}-dep-download.log`: Output of pip while downloading the dependencies for Python build systems.


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


## Suggested Workflow
When working with caching a lot of artifacts and pushing them to the production
registry, it is important to keep things organized.

As of Mar 24, 2021, we use `bugswarm/images` on DockerHub for non-cached images
and `bugswarm/cached-images` for cached images. We use a Google spreadsheet to
track the status of each image. We primarily use bugcatcher to test whether an
artifact is reproducible.

The following workflow is just a recommendation

1. Get a list of image tags to be cached from the Google spreadsheet. Make sure
   their status is not cached (goal2). Store them to a file (I usually use
   `name_mar24a`, where `name` represents my name, `mar24` is today's date,
   `a` is the index of this file within today)
2. Pick a task name for the run. I usually pick `name_mar24a1`, where `1` is the
   index of run done on `name_mar24a`.
3. Run the caching script and let it push to a temporary docker repo (in
   contrast to `bugswarm/cached-images`, which is the production repo). Consider
   creating a private repository like `bugswarm/tmp_name_mar24a1`. Note that if
   the repository does not exist, DockerHub will create a public one
   automatically.
	* It is possible (but not recommended) to use non-bugswarm users, like
	  `dockeruser/name_mar24a1`, where `dockeruser` is my user name on
	  DockerHub.
4. Wait for the script to complete. It is going to take a long time.
5. After the script completes, go to `output/name_mar24a1.csv` to see the status
   of each artifact.
6. For images that success:
	1. It is recommended to test them first using bugcatcher.
	2. After that, push them to the production repo using the
	   `move_docker_images.py` helper script (this script will avoid overwriting
	   an existing image by default, which is good).
	3. Test the images in `bugswarm/cached-images` using bugcatcher. Create 2
	   test suites: one with connected network and one with disconnected.
	4. After testing, update the images in the Google spreadsheet to goal1 /
	   done according to the test result.
	5. Ping the person responding for the next step in the pipeline
7. For images that fail:
	1. First try again with extra caching features (e.g.
	   `--separate-passed-failed` for Java and `--parse-{new/old}-log` for Python)
	2. If that still does not work, go to `~/bugswarm-sandbox/name_mar24a1` and
	   debug by looking through the logs.
	3. To debug deeper, use `--keep-tmp-images`, `--keep-containers`, and
	  `--keep-tars` to save temporary files and Docker images. Note that these
	  options will consume a lot of disk space, so don't use them on a large
	  number of images. Also make sure to clean up after debugging.


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

### Pip Freeze Method (default)
1. Edit build scripts so that if a python virtual environment needs to be downloaded, the file it downloaded will not be deleted.
1. Runs the failed and passed jobs using `run_failed.sh` and `run_passed.sh`.
1. Use grep to find which python virtualenv was used and activate it.
1. Use `pip freeze` to get list of all installed packages.
1. Look for additional pip packages by looping through all anaconda virtualenvs if any, activating them and getting a list of their pip dependencies with `pip freeze`.
1. Download all the dependencies using `pip download` (or `pip install --download` for older versions of pip) to a new folder. Put the folder into a tarball and copy it out of the container.
   1. If a virtualenv was downloaded (the download file is still around), then copy the tar file it came from into the folder also before copying it out.
1. Copy the dependencies into a fresh instance of the artifact(`failed/requirements/`, `passed/requirements/`).
1. Patch build script with `--no-index --find-link` to utilize the download dependencies.
   1. If a virtualenv is downloaded by build script then place the cached tar file in the `/home/travis/build` directory and comment out the line to download it from the build script.

#### Parsing Method (activated with `--parse-original-log` or `--parse-new-log`)
1. Parse the passed or failed job logs to get a list of dependencies and versions.
   1. `--parse-original-log` will download then parse the original Travis-CI logs.
   1. `--parse-new-log` will reproduce the artifact then parse the log of that run.
1. Based on python/pip version, we initiate a docker container with same `python version` to download packages via `pip download`.
1. Copy them into the artifact(`failed/requirements/`, `passed/requirements/`).
1. Patch build script with `--no-index --find-link` to utilize the download dependencies.


## Unit tests for log parser
```
cd tests
python3 -m test_python_log_parser
```
