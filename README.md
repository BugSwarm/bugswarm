# BugSwarm Overview
BugSwarm is a framework that enables the creation of scalable, diverse, real-world, continuously
growing set of reproducible build failures and fixes from open-source projects.

The framework consist of two major components: [Miner](#miner) and [Reproducer](#reproducer).

![bugswarm-image-overview](https://user-images.githubusercontent.com/24599782/70661354-e9787580-1c18-11ea-855e-53e26426c261.png)
*Datasets play an important role in the advancement of software tools and facilitate their evaluation. BugSwarm is an infrastructure to automatically create a large dataset of real-world reproducible failures and fixes*

For more details:
* **Website**: http://www.bugswarm.org
* **DockerHub Repository for BugSwarm Dataset**: https://hub.docker.com/r/bugswarm/images/tags
* **ICSE-2019 Paper**: [BugSwarm: Mining and Continuously Growing a Dataset of Reproducible Failures and Fixes](https://web.cs.ucdavis.edu/~rubio/includes/icse19.pdf)

If you use our infrastructure or dataset, please cite our paper as follows:
```
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
## Setting up BugSwarm
1. System requirements:
    * A Unix-based operating system. (BugSwarm does not support Windows.)
    * The `sudo` command is installed on the system.
    * You have `sudo` privileges on the system.
    * The system uses `apt-get` to manage packages (or you may need to edit
      `provision.sh` to make it work correctly / use spawner (see below)).

1. Install the prerequisites:
    * Install [Docker](https://docs.docker.com/install/) -  [Why Docker?](docs/Frequently-Answered-Questions.md#why-do-we-use-docker)

1. Clone the repository:
    ```
    $ git clone https://github.com/BugSwarm/bugswarm.git
    ```

1. Set up MongoDB:

    BugSwarm provides a [Docker image](https://docs.docker.com/v17.09/engine/userguide/storagedriver/imagesandcontainers/) of MongoDB to port with the pipeline. Alternatively, you can use [Dockerfile](https://docs.docker.com/engine/reference/builder/) to build your own image from scratch.
    1. Pull the provided Docker image from the BugSwarm Docker Hub repo:
        ```
        $ docker pull bugswarm/containers:bugswarm-db
        $ docker tag bugswarm/containers:bugswarm-db bugswarm-db
        ```
    Build your own Docker image of the BugSwarm MongoDB from the source Dockerfile:

    1. Change to the database directory:
        ```
        $ cd bugswarm/database
        ```
    1. [Build](https://docs.docker.com/engine/reference/commandline/build/) the Docker image with the tag as `bugswarm-db`
    from the Dockerfile:
        ```
        $ docker build . -t bugswarm-db
        ```
    Now that the Docker image is ready: 
    1. Run & [port](https://docs.docker.com/config/containers/container-networking/) the Docker container containing MongoDB:
        ```
        $ docker run -itd -p 27017:27017 -p 5000:5000 bugswarm-db
        ```
        > Note: If multiple instances of MongoDB are running on the system, you must change the port accordingly.
        > Please see the [FAQ](docs/Frequently-Answered-Questions.md)
    1. Get back to parent folder:
        ```
        $ cd ..
        ```

1. (Recommended) Set up and run spawner (to run BugSwarm in host, go to step 6):

    Spawner is a Docker image that contain all required packages in `provision.sh` and can spawn pipeline jobs. If using spawner, the host only needs to install Docker.

    To understand how spawner works, please see [spawner README](spawner/README.md).

    1. Pull the spawner container and update the tag:
       ```
       $ docker pull bugswarm/containers:bugswarm-spawner
       $ docker image tag bugswarm/containers:bugswarm-spawner bugswarm-spawner
       ```
       Alternatively, build the spawner using Docker:
        ```sh
        $ cd spawner
        $ docker build -t bugswarm-spawner .
        ```
    1. Run the container with `/var/run/docker.sock` mounted and network set to `host`.
        ```sh
        $ docker run -v /var/run/docker.sock:/var/run/docker.sock \
            -v /var/lib/docker:/var/lib/docker --net=host -it bugswarm-spawner
        ```
    1. Add user to docker group and re-login.
        ```sh
        $ DOCKER_GID=`stat -c %g /var/run/docker.sock`
        $ sudo groupadd -g $DOCKER_GID docker_host
        $ sudo usermod -aG $DOCKER_GID bugswarm
        $ sudo su bugswarm
        ```
    1. Pull the git repository
        ```sh
        $ git pull
        ```

1. If you are using the spawner container, continue the following commands in the containers. If you are using the host, continue with the host.

1. Mongo should now be up and running, test the connection by opening a new Terminal and use:
    ```
    $ mongo
    ```

1. Step into initial BugSwarm directory and configure necessary credentials:
    1. Make a copy of the credentials file:
        ```
        $ cp bugswarm/common/credentials.sample.py bugswarm/common/credentials.py
        ```
    1. Fill in credentials in `bugswarm/common/credentials.py`:
        ```
        DOCKER_HUB_REPO=<DOCKER_HUB_REPO>
        DOCKER_HUB_CACHED_REPO=<DOCKER_HUB_CACHED_REPO>
        DOCKER_HUB_USERNAME=<DOCKER_HUB_USERNAME>
        DOCKER_HUB_PASSWORD=<DOCKER_HUB_PASSWORD>
        GITHUB_TOKENS=<GITHUB_TOKENS>
        TRAVIS_TOKENS=<TRAVIS_CI_TOKEN>
        DATABASE_PIPELINE_TOKEN=<DATABASE_PIPELINE_TOKEN> ('testDBPassword' if using Docker image of Mongo)
        COMMON_HOSTNAME=<LOCAL-IPADDRESS>:5000
        ```
       > The following values are required for authentication, accessing components and APIs used within
       > the BugSwarm pipeline. Please see the [FAQ](docs/Frequently-Answered-Questions.md) for details regarding the credentials.

1. Run the provision script:
    ```
    $ ./provision.sh
    ```
   > The `provision.sh` will provision the environment to utilize the BugSwarm pipeline

## Miner
BugSwarm mines builds from projects on GitHub that use [Travis CI](https://travis-ci.org/), a continuous integration 
service. We mine fail-pass build pairs such that the first build of the pair fails and the second, which is
next chronologically in Git history on each branch, passes.

The Miner component consists of the `Pair-Miner` and `Pair-Filter`.

`run_mine_project.sh`: Mines job-pairs from a project given its repo-slug.

```
Usage: ./run_mine_project.sh -r <repo-slug> [OPTIONS]

    <repo-slug>         Repo slug of the project from which the job-pair was mined

    OPTIONS:
        -t, --threads                Maximum number of worker threads to spawn. Defaults to 1.
        -c, --component-directory    The directory containing all the required BugSwarm components.
```
_Example_:
```
$ ./run_mine_project.sh -r alibaba/canal
```
The example will mine job-pairs from the "alibaba/canal" project. This will run through the Miner component
of the BugSwarm pipeline. The output will push data to your MongoDB specified and outputs several `.json` files
after each sub-step.

## [Reproducer](/reproducer/README.md)
BugSwarm obtains the original build environment that was used by Travis CI, via a Docker image, and generate
scripts to build and run regression tests for each build. We match the reproduced build log, which is a
transcript of everything that happens at the command line during build and testing, with the historical
build log from Travis CI. We do this five times to account for reproducibility and flakiness. Reproducible pairs
are then pushed as an an Artifact to `DOCKER_HUB_REPO` in as specified in `credentials.py`, as a temporary repo. 
Metadata is not pushed to the MongoDB until after completing of the following caching step which pushes the Artifact
with cached dependencies to the final repo, described below.

#### Reproduce a Project
`run_reproduce_project.sh`: Reproduces all job-pairs mined from a project given its repo slug.
```
Usage: ./run_reproduce_project.sh -r <repo-slug> [OPTIONS]

    <repo-slug>         Repo slug of the project

    OPTIONS:
        -t, --threads                Maximum number of worker threads to spawn. Defaults to 1.
        -c, --component-directory    The directory containing all the required BugSwarm components.
        -s, --skip-check-disk        Skip checking for disk space (default requires 50 GiB free space).
                                     This can result in your disk filling up depending on how many/big projects are being reproduced.
```
_Example_:
```
$ ./run_reproduce_project.sh -r alibaba/canal -c ~/bugswarm
```
The example will attempt to reproduce all job-pairs mined from the "alibaba/canal" project. We add the "-c"
argument to specify that "~/bugswarm" directory contains the required BugSwarm components to run the pipeline
sucessfully.

#### Generate Pair Input

`generate_pair_input.py`: Generate job pairs from the given repo slug or file containing a list of repos. This allows
 the user to be selective in which job pairs they'd want to reproduce through the optional argument filters. The output 
 will result as such: repo-slug, failing-job-id, and passing-job-id.
```
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
_Example_:
```
$ python3 generate_pair_input.py --repo alibaba/canal --include-resettable --include-test-failures-only --include-archived-only --classified-code --classified-exception NullPointerException -o /home/user/results_output.txt
```
The example above will include job pairs that were previously attempted to reproduce from the Artifact database collection,
among those job pairs we include only those that have test failure according to the Analyzer, marked
as resettable, and finally we restrict the job pairs further to those that were classified with having 
the "NullPointerException".

The output of this script can then be used with the below step, Reproduce a Pair.

#### Reproduce a Pair
`run_reproduce_pair.sh`: Reproduces a single job-pair given the slug for the project from which the job-pair
 was mined, the failed Job ID, and the passed job ID.
```
Usage: ./run_reproduce_pair.sh -r <repo-slug> -f <failed-job-id> -p <passed-job-id> [OPTIONS]

    <repo-slug>         Repo slug of the project
    <failed-job-id>     The failed job ID
    <passed-job-id>     The passed job ID

    OPTIONS:
        -t, --threads                Maximum number of worker threads to spawn. Defaults to 1.
        -c, --component-directory    The directory containing all the required BugSwarm components.
        -s, --skip-check-disk        Skip checking for disk space (default requires 50 GiB free space).
                                     This can result in your disk filling up depending on how many/big projects are being reproduced.
```
_Example_:
```
$ ./run_reproduce_pair.sh -r alibaba/canal -f 256610197 -p 256621225 -t 2
```
The example above will take the repo-slug "alibaba/canal" and both failed/passed job id to reproduce through
the Reproducer component of the pipeline. We use 2 threads to run the process. If successful, we push the Artifact to the temporary 
DockerHub repository specified as `DOCKER_HUB_REPO` in the `credentials.py` file for attempted caching in the following step described below.

## [Cacher](/cache-dependency/README.md)
Artifacts with cached dependencies are more stable over time, and are the form in which Artifacts should be added to a dataset.
Successfully cached Artifacts are then pushed to the final repo, specified as `DOCKER_HUB_CACHED_REPO` in `credentials.py`, with
crucial metadata pushed to the MongoDB.

#### Cache Reproduced Project
`run_cache_project.sh`: Cache reproduced job-pair Artifacts from a project.
```
Usage: ./run_cache_project.sh -r <repo-slug> [OPTIONS]

    <repo-slug>         Repo slug of the project

    OPTIONS:
        -t, --threads                Maximum number of worker threads to spawn. Defaults to 1.
        -c, --component-directory    The directory containing all the required BugSwarm components.
        -ca, --caching-args          Optional flags to caching script, written as normal enclosed by
                                     single-quotes. See cache-dependency/README for details on flags.
```
_Example_:
```
$ ./run_cache_project.sh -r "alibaba/canal" -c ~/bugswarm -ca '--separate-passed-failed --no-strict-offline-test'
```
The example will attempt to cache all reproducible job-pairs from the "alibaba/canal" project. We add the "-c"
argument to specify that "~/bugswarm/" directory contains the required BugSwarm components to run the pipeline
sucessfully. We will run the caching script with the `--separate-passed-failed` and `--no-strict-offline-test` flags. 
If successful, metadata will be pushed to our specified MongoDB and the cached Artifact is pushed to the
DockerHub repository we specified by `DOCKER_HUB_CACHED_REPO`. This script tracks successfully cached Artifacts, 
so that only the remaining uncached are attempted. This script is meant to be re-run as necessary with different 
caching script flags to iteratively attempt caching candidate reproducible Artifacts. Successfully cached artifacts
then have their metadata inserted into the Database and their failed and passed build logs uploaded to the database.

#### Cache Reproduced Pair
`run_cache_pair.sh`: Caches a single reproduced Artifact given the slug for the project from which the job-pair
 was mined and the failed Job ID. The passed Job ID is not necessary any longer for this step.

```
Usage: ./run_cache_pair.sh -r <repo-slug> -f <failed-job-id> [OPTIONS]

    <repo-slug>         Repo slug of the project
    <failed-job-id>     The failed job ID

    OPTIONS:
        -c, --component-directory    The directory containing all the required BugSwarm components.
        -ca <caching-args>           Optional flags to caching script, written as normal enclosed by
                                     single-quotes. See cache-dependency/README for details on flags.
```
_Example_:
```
$ ./run_cache_pair.sh -r alibaba/canal -f 256610197 -ca '--keep-tmp-images --keep-containers'
```
The example above takes command line arguments repo-slug "alibaba/canal", the failed job id, and optional caching
script arguments `--keep-tmp-images` and `--keep-containers` to cache the reproduced jobpair which was pushed to a temporary 
repo by `run_reproduce_pair.sh` to the cached Artifact repo `DOCKERHUB_CACHED_REPO`.

## Questions:
Visit our FAQ docs [page](docs/Frequently-Answered-Questions.md)
