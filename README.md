# BugSwarm Overview

BugSwarm is a framework that enables the creation of scalable, diverse, real-world, continuously
growing set of reproducible build failures and fixes from open-source projects.

The framework consists of three major components: [Miner](#miner), [Reproducer](#reproducer), and [Cacher](#cacher).

<!--![bugswarm-image-overview](https://user-images.githubusercontent.com/24599782/70661354-e9787580-1c18-11ea-855e-53e26426c261.png)
*Datasets play an important role in the advancement of software tools and facilitate their evaluation. BugSwarm is an infrastructure to automatically create a large dataset of real-world reproducible failures and fixes*-->

For more details:

* **Website**: <http://www.bugswarm.org>
* **DockerHub Repository for BugSwarm Dataset**: <https://hub.docker.com/r/bugswarm/images/tags>
* **ICSE-2019 Paper**: [BugSwarm: Mining and Continuously Growing a Dataset of Reproducible Failures and Fixes](https://web.cs.ucdavis.edu/~rubio/includes/icse19.pdf)
* **ICSE-Companion 2023 Paper**: [ActionsRemaker: Reproducing GitHub Actions](https://web.cs.ucdavis.edu/~rubio/includes/icse23-demo.pdf)

If you use our infrastructure or dataset, please cite our paper as follows:

```bibtex
@inproceedings{BugSwarm-ICSE19,
  author    = {David A. Tomassi and
               Naji Dmeiri and
               Yichen Wang and
               Antara Bhowmick and
               Yen{-}Chuan Liu and
               Premkumar T. Devanbu and
               Bogdan Vasilescu and
               Cindy Rubio{-}Gonz{\'{a}}lez},
  title     = {BugSwarm: mining and continuously growing a dataset of reproducible
               failures and fixes},
  booktitle = {{ICSE}},
  pages     = {339--349},
  publisher = {{IEEE} / {ACM}},
  year      = {2019}
}
```

Our second paper concerning the GitHub Actions segment of the pipeline can be cited as follows:

```bibtex
@inproceedings{ICSE:demo/actions-remaker,
  author    = {Zhu, Hao-Nan and
               Guan, Kevin Z. and
               Furth, Robert M. and
               Rubio-González, Cindy},
  title     = {{ActionsRemaker: Reproducing GitHub Actions}},
  booktitle = {{ICSE-Companion}}, 
  pages     = {11--15},
  publisher = {{IEEE}},
  year      = {2023},
  doi       = {{10.1109/ICSE-Companion58688.2023.00015}}
}
```

## Setting up BugSwarm

**You only have to follow the steps below if you want to produce your own artifacts.
If you only want to use BugSwarm artifact dataset, follow the [client](https://github.com/BugSwarm/client) instructions or our [tutorial](http://www.bugswarm.org/docs/tutorials/setting-up-an-experiment/) instead.**

1. System requirements:

    * A machine with x86-64 architecture. (BugSwarm does not support ARM architecture such as Apple silicon.)
    * A Unix-based operating system. (BugSwarm does not support Windows.)
    * The `sudo` command is installed on the system.
    * You have `sudo` privileges on the system.
    * The system uses `apt-get` to manage packages (or you may need to edit
      `provision.sh` to make it work correctly / use spawner (see below)).

1. Install the prerequisites:

    * Install [Docker](https://docs.docker.com/install/) -  [Why Docker?](docs/Frequently-Answered-Questions.md#why-do-we-use-docker)

1. Clone the repository:

    ```console
    git clone https://github.com/BugSwarm/bugswarm.git
    ```

1. Set up MongoDB:

    BugSwarm provides a [Docker image](https://docs.docker.com/v17.09/engine/userguide/storagedriver/imagesandcontainers/) of MongoDB to port with the pipeline. Alternatively, you can use [Dockerfile](https://docs.docker.com/engine/reference/builder/) to build your own image from scratch.

    1. Pull the provided Docker image from the BugSwarm Docker Hub repo:

        ```console
        docker pull bugswarm/containers:bugswarm-db
        docker tag bugswarm/containers:bugswarm-db bugswarm-db
        ```

    Build your own Docker image of the BugSwarm MongoDB from the source Dockerfile:

    1. Change to the database directory:

        ```console
        cd bugswarm/database
        ```

    1. [Build](https://docs.docker.com/engine/reference/commandline/build/) the Docker image with the tag as `bugswarm-db`
    from the Dockerfile:

        ```console
        docker build . -t bugswarm-db
        ```

    Now that the Docker image is ready:

    1. Run & [port](https://docs.docker.com/config/containers/container-networking/) the Docker container containing MongoDB:

        ```console
        docker run -itd -p 27017:27017 -p 5000:5000 bugswarm-db
        ```

        > Note: If multiple instances of MongoDB are running on the system, you must change the port accordingly.
        > Please see the [FAQ](docs/Frequently-Answered-Questions.md)
        >
        > In some operating systems, this command will expose ports so that everyone from the outside world will be able to connect.
        > To stop this, replace `-p 27017:27017 -p 5000:5000` with `-p 127.0.0.1:27017:27017 -p 127.0.0.1:5000:5000`

    1. Get back to parent folder:

        ```console
        cd ..
        ```

1. (Recommended) Set up and run spawner (to run BugSwarm in host, go to step 6):

    Spawner is a Docker image that contain all required packages in `provision.sh` and can spawn pipeline jobs. If using spawner, the host only needs to install Docker.

    To understand how spawner works, please see [spawner README](spawner/README.md).

    1. Pull the spawner container and update the tag:

       ```console
       docker pull bugswarm/containers:bugswarm-spawner
       docker image tag bugswarm/containers:bugswarm-spawner bugswarm-spawner
       ```

       Alternatively, build the spawner using Docker:

        ```console
        cd spawner
        docker build -t bugswarm-spawner .
        ```

    1. Run the container with `/var/run/docker.sock` mounted and network set to `host`.

        ```console
        docker run -v /var/run/docker.sock:/var/run/docker.sock \
            -v /var/lib/docker:/var/lib/docker --net=host -it bugswarm-spawner
        ```

    1. Add user to docker group and re-login.

        ```console
        DOCKER_GID=`stat -c %g /var/run/docker.sock`
        sudo groupadd -g $DOCKER_GID docker_host
        sudo usermod -aG $DOCKER_GID bugswarm
        sudo su bugswarm
        ```

    1. Pull the git repository

        ```console
        git pull
        ```

1. If you are using the spawner container, continue the following commands in the containers. If you are using the host, continue with the host.

1. Mongo should now be up and running. Test the connection by running the following commands and checking that the output matches:

    ```console
    $ curl localhost:27017  # MongoDB check -- you can also run `mongosh` if it's installed on the host
    It looks like you are trying to access MongoDB over HTTP on the native driver port.
    
    $ curl -H 'Authorization: token testDBPassword' localhost:5000/v1/artifacts  # Local API check
    {"_items": [], "_links": {"next": {"href": "artifacts?page=2", "title": "next page"}, "parent": {"href": "/", "title": "home"}, "self": {"href": "artifacts", "title": "artifacts"}}, "_meta": {"max_results": 250, "page": 1}}
    ```

1. Step into initial BugSwarm directory and configure necessary credentials:
    1. Make a copy of the credentials file:

        ```console
        cp bugswarm/common/credentials.sample.py bugswarm/common/credentials.py
        ```

    1. Fill in credentials in `bugswarm/common/credentials.py`:

        ```python
        DOCKER_HUB_REPO=<DOCKER_HUB_REPO>
        DOCKER_HUB_CACHED_REPO=<DOCKER_HUB_CACHED_REPO>
        DOCKER_HUB_USERNAME=<DOCKER_HUB_USERNAME>
        DOCKER_HUB_PASSWORD=<DOCKER_HUB_PASSWORD>
        GITHUB_TOKENS=<GITHUB_TOKENS>
        TRAVIS_TOKENS=<TRAVIS_CI_TOKEN>
        DATABASE_PIPELINE_TOKEN=<DATABASE_PIPELINE_TOKEN>  # ('testDBPassword' if using Docker image of Mongo)
        COMMON_HOSTNAME=<LOCAL-IPADDRESS>:5000
        ```

       > The following values are required for authentication, accessing components and APIs used within
       > the BugSwarm pipeline. Please see the [FAQ](docs/Frequently-Answered-Questions.md) for details regarding the credentials.

1. Run the provision script:

    ```console
    ./provision.sh
    ```

    This will provision the environment to use the BugSwarm pipeline.
    If you only want to produce GitHub Actions artifacts, you can use the `--github-actions-only` switch to skip installing the extra components needed to produce TravisCI artifacts.

    ```console
    ./provision.sh --github-actions-only
    ```

## Miner

BugSwarm mines builds from projects on GitHub that use the continuous integration (CI) services [Travis CI](https://travis-ci.org/) and [GitHub Actions](https://github.com/features/actions).
We mine fail-pass build pairs such that the first build of the pair fails and the second, which is next chronologically in Git history on each branch, passes.

The Miner component consists of the `PairFinder`, `PairFilter`, and `PairClassifier`.
`PairFinder` has a separate version for each CI service we support, while `PairFilter` and `PairClassifier` are CI-service-agnostic.

### Mine a Project

`run_mine_project.sh`: Mines job pairs from a project or projects.

This script finds fail-pass job pairs in the given projects, filters out unsuitable pairs, downloads each job's original log, and obtains classification statistics for each job/job pair.
It outputs a set of JSON files (one for each repository mined) in `pair-classifier/output`, and the original logs for each job in `pair-filter/original-logs`.
It also updates the `minedBuildPairs` database collection.

```shellsession
./run_mine_project.sh --ci <ci> (-r <repo-slug> | -f <repo-slug-file>) [OPTIONS]
```

Required Options:

* `--ci <CI>`: The CI service to mine. Must be either `travis` or `github`.
* `-r, --repo <REPO>`: The GitHub repository to mine.
    Cannot be used with `-f`.
* `-f, --repo-file <FILE>`: A file containing a newline-separated list of GitHub repositories to mine.
    Cannot be used with `-r`.

Additional Options:

* `-t, --threads <THREADS>`: The number of threads to use while mining.
    Only useful if mining more than one repository.
    Defaults to 1.
* `-c, --component-directory <DIR>`: The directory where the PairFinder, PairFilter, and PairClassifier are located.
    Defaults to the directory where the script is located.

*Example*:

```console
./run_mine_project.sh --ci github -r alibaba/spring-cloud-alibaba
```

The example will mine GitHub Actions job-pairs from the "alibaba/spring-cloud-alibaba" project.
This will run through the Miner component of the BugSwarm pipeline.
The output will push data to your MongoDB specified and outputs several `.json` files after each sub-step.
This process should take less than 10 minutes.

## [Reproducer](/github-reproducer/README.md)

BugSwarm obtains the original build environment that was used by Travis CI or GitHub Actions via a Docker image, and generates
scripts to run every command that was run in the original build.
We match the reproduced build log, which is a transcript of everything that happens at the command line during build and testing, with the historical build log from the target CI service.
We do this three times to account for reproducibility and flakiness.
Reproducible pairs are then pushed as an Artifact to `DOCKER_HUB_REPO` as specified in `credentials.py`, as a temporary repo.
Metadata is not pushed to the MongoDB until the [Cacher](#cacher) step, which pushes the Artifact with cached dependencies to the final repo.

### Reproduce a Project

`run_reproduce_project.sh`: Reproduces all job pairs mined from a project given its repo slug.

Required Options:

* `--ci <CI>`: The CI service of the pairs to reproduce.
    Must be either `travis` or `github`.
* `-r, --repo <REPO>`: The repository of the pairs to reproduce.

Additional Options:

* `-t, --threads <THREADS>`: The number of worker threads to reproduce with.
* `-c, --component-directory <DIR>`: The directory where the Reproducer is located.
    Defaults to the directory where the script is located.
* `-s, --skip-disk-check`: If set, do not verify whether there is adequate disk space (50 GiB by default) for reproducing before running.
    Possibly useful if you're low on disk space.

*Example*:

```text
./run_reproduce_project.sh --ci github -r alibaba/spring-cloud-alibaba -c ~/bugswarm -t 4
```

The example will attempt to reproduce all job-pairs mined from the "alibaba/spring-cloud-alibaba" project.
We add the "-c" argument to specify that "~/bugswarm" directory contains the required BugSwarm components to run the pipeline successfully.
We use 4 threads to run the process.

### Generate Pair Input

`generate_pair_input.py`: Generate job pairs from the given repo slug or file containing a list of repos. This allows
 the user to be selective in which job pairs they'd want to reproduce through the optional argument filters. The output
 will result as such: repo-slug, failing-job-id, and passing-job-id.

```text
Usage: python3 generate_pair_input.py (-r <repo-slug> | --repo-file <repo-file>) -o <output-path> [options]

Options:
     -r, --repo                         Repo slug for the mined project from which to choose pairs. Cannot be used with --repo-file.
         --repo-file                    Path to file containing a newline-separated list of repo slugs for the mined projects from which to choose pairs. Cannot be used with --repo.
     -o, --output-path                  Path to the file where chosen pairs will be written.
         --include-attempted            Include job pairs in the artifact database collection that we have already attempted to reproduce. Defaults to false.
         --include-archived-only        Include job pairs in the artifact database collection that are marked as archived by GitHub but not resettable. Defaults to false.
         --include-resettable           Include job pairs in the artifact database collection that are marked as resettable. Defaults to false.
         --include-test-failures-only   Include job pairs that have a test failure according to the Analyzer. Defaults to false.
         --include-different-base-image Include job pairs that passed and failed job have different base images. Defaults to false.
         --classified-build             Restrict job pairs that have been classified as build according to classifier Defaults to false.
         --classified-code              Restrict job pairs that have been classified as code according to classifier Defaults to false.
         --classified-test              Restrict job pairs that have been classified as test according to classifier Defaults to false.
         --exclusive-classify           Restrict to job pairs that have been exclusively classified as build/code/test, as specified by their respective options. Defaults to false.
         --classified-exception         Restrict job pairs that have been classified as contain certain exception
         --build-system                 Restricted to certain build system
         --os-version                   Restricted to certain OS version(e.g. 12.04, 14.04, 16.04)
         --diff-size                    Restricted to certain diff size MIN~MAX(e.g. 0~5)
```

*Example*:

```console
python3 generate_pair_input.py --repo alibaba/spring-cloud-alibaba --include-resettable --include-test-failures-only --include-archived-only --classified-exception IllegalAccessError -o ./results_output.txt
```

The example above will include job pairs that were previously attempted to reproduce from the Artifact database collection,
among those job pairs we include only those that have test failure according to the Analyzer, marked
as resettable, and finally we restrict the job pairs further to those that were classified with having
the "IllegalAccessError".

The output file of this script can then be used to define the repo slug, failed job ID, and passed job ID arguments of the below step, Reproduce a Pair.

### Reproduce a Pair or Pairs

`run_reproduce_pair.sh`: Reproduces a single job pair given the slug for the project from which the job pair was mined, the failed Job ID, and the passed job ID.

```console
./run_reproduce_pair.sh --ci <CI> (--pair-file <FILE> | -r <REPO> -f <FAILED_JOB_ID> -p <PASSED_JOB_ID>) [OPTIONS]
```

Required Options:

* `--ci <CI>`: The CI service the pair comes from.
    Must be either `travis` or `github`.
* `--pair-file <FILE>`: A CSV file containing fail-pass pairs, such as the ones generated by `generate_pair_input.py`.
  Cannot be used with `-r`, `-f`, or `-p`.
* `-r, --repo <REPO>`: The repository the job pair comes from.
* `-f, --failed-job-id <JOB_ID>`: The failed job ID of the pair to reproduce.
* `-p, --passed-job-id <JOB_ID>`: The passed job ID of the pair to reproduce.

Additional Options:

* `-t, --threads <THREADS>`: The number of worker threads to reproduce with.
* `-c, --component-directory <DIR>`: The directory where the Reproducer is located.
    Defaults to the directory where the script is located.
* `--reproducer-runs <RUNS>`: The number of times to run the reproducer.
    Use more to be more certain about whether a run is reprodcible.
    Defaults to 5.
* `-s, --skip-disk-check`: If set, do not verify whether there is adequate disk space (50 GiB by default) for reproducing before running.
    Possibly useful if you're low on disk space.
* `--skip-cacher`: Do not cache the job pairs after reproducing them.

*Example*:

```console
./run_reproduce_pair.sh --ci github -r alibaba/spring-cloud-alibaba -f 10571587467 -p 10579006004 --reproducer-runs 3
```

This example will attempt to reproduce the GitHub Actions job pair with failed job ID 10571587467 and passed job ID 10579006004 from the "alibaba/spring-cloud-alibaba" project.
We specify that the Reproducer should attempt to reproduce the job pair only 3 times, instead of the default 5 times.
We do not specify the number of threads, so the Reproducer defaults to 1 worker thread.

## [Cacher](/github-cacher/README.md)

Artifacts with cached dependencies are more stable over time, and are the form in which Artifacts should be added to a dataset.
Successfully cached Artifacts are then pushed to the final repo, specified as `DOCKER_HUB_CACHED_REPO` in `credentials.py`, with
crucial metadata pushed to the MongoDB.
If you reproduced job pairs using `run_reproduce_pair.sh`, then they have already been cached unless you provided the `--skip-cacher` parameter.

### Cache Reproduced Pairs or Project

`run_cacher.sh`: Cache job-pair artifacts from a previous reproducer run.

```console
./run_cacher.sh --ci <ci> -i <file> [OPTIONS]
```

Required Options:

* `--ci <CI>`: The CI service of the pairs to cache.
    Must be either `travis` or `github`.
* `-i, --input-json <FILE>`: A JSON file generated by the Reproducer.
  These files are named `<ci>-reproducer/output/result_json/<task-name>.json`, according the task name given to the reproducer run that generated them.
  If you used `run_reproduce_{pair,project}.sh`, then this file will be named one of the following:
  * `run_reproduce_project.sh`: `<owner>-<repo>.json`
  * `run_reproduce_pair.sh -r ... -f ... -p ...`: `<owner>-<repo>_<failed-job-id>.json`
  * `run_reproduce_pair.sh --pair-file ...`: `<pair-file-without-extension>.json`

Additional Options:

* `-t, --threads <THREADS>`: The number of concurrent threads to run.
    Defaults to 1 thread.
* `-c, --component-directory <DIR>`: The directory where the Reproducer is located.
    Defaults to the directory where the script is located.
* `--no-push`: Do not update the database or push the image to `DOCKER_HUB_CACHED_REPO`.
* `-a, --caching-args <ARGS>`: A string containing arguments to pass on to `CacheMaven.py`.
    See that script's [README](github-cacher/README.md) for a description of these arguments.

*Example*:

First, log in to a Docker registry with `docker login`. Then, run:

```console
./run_cacher.sh --ci github -i github-reproducer/output/result_json/spring-cloud-alibaba.json -c ~/bugswarm -a '--separate-passed-failed --no-strict-offline-test'
```

The example will attempt to cache all reproducible job-pairs from the "alibaba/spring-cloud-alibaba" project. We add the "-c"
argument to specify that "~/bugswarm/" directory contains the required BugSwarm components to run the pipeline
successfully. We will run the caching script with the `--separate-passed-failed` and `--no-strict-offline-test` flags.
If successful, metadata will be pushed to our specified MongoDB and the cached Artifact is pushed to the
DockerHub repository we specified by `DOCKER_HUB_CACHED_REPO`. This script tracks successfully cached Artifacts,
so that only the remaining uncached are attempted. This script is meant to be re-run as necessary with different
caching script flags to iteratively attempt to cache candidate reproducible Artifacts. Successfully cached artifacts
then have their metadata inserted into the Database and their failed and passed build logs uploaded to the database.

## Questions

Visit our FAQ docs [page](docs/Frequently-Answered-Questions.md)
