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
    * The `sudo` command is installed on the system.
    * You have `sudo` privileges on the system.
    * The system uses `apt-get` to manage packages (or you may need to edit
      `provision.sh` to make it work correctly).

1. Install the prerequisites:
    * Install [Docker](https://docs.docker.com/install/) -  [Why Docker?](docs/Frequently-Answered-Questions.md#why-do-we-use-docker)

1. Clone the repository:
    ```
    $ git clone https://github.com/BugSwarm/bugswarm.git
    ```

1. Setup MongoDB:

    **Create your own Docker Image of the BugSwarm MongoDB:**

    BugSwarm provides a [Dockerfile](https://docs.docker.com/engine/reference/builder/) to build a 
    [Docker image](https://docs.docker.com/v17.09/engine/userguide/storagedriver/imagesandcontainers/) 
    of MongoDB to port with the pipeline. Follow the steps below:

    1. Change to the database directory:
        ```
        $ cd bugswarm/database
        ```
    1. [Build](https://docs.docker.com/engine/reference/commandline/build/) the Docker Image with the tag as `bugswarm-db`
    from the Dockerfile located similarly to the above directory:
        ```
        $ docker build . -t bugswarm-db
        ```
    1. Run & [port](https://docs.docker.com/config/containers/container-networking/) the Docker container containing MongoDB:
        ```
        $ docker run -itd -p 27017:27017 -p 5000:5000 bugswarm-db
        ```
        > Note: If multiple instances of MongoDB are running on the system, you must change the port accordingly.
        > Please see the [FAQ](docs/Frequently-Answered-Questions.md)
    1. Get back to parent folder:
        ```
        $ cd ../..
        ```
    1. Move to step 4.
1. Mongo should now be up and running, test the connection by opening a new Terminal and use:
    ```
    $ mongo
    ```
1. Step into initial BugSwarm directory and configure necessary credentials:
    1. Change directories to BugSwarm:
        ```
        $ cd bugswarm
        ```
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
$ ./run_mine_project.sh -r Flipkart/foxtrot
```
The example will mine job-pairs from the "Flipkart/foxtrot" project. This will run through the Miner component
of the BugSwarm pipeline. The output will push data to your MongoDB specified and outputs several .json files
after each sub-step.

## [Reproducer](/reproducer/README.md)
BugSwarm obtains the original build environment that was used by Travis CI, via a Docker image, and generate
scripts to build and run regression tests for each build. We match the reproduced build log, which is a
transcript of everything that happens at the command line during build and testing, with the historical
build log from Travis CI. We do this five times to account for reproducibility and flakiness.
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
$ ./run_reproduce_project.sh -r "Flipkart/foxtrot" -c ~/bugswarm/
```
The example will attempt to reproduce all job-pairs mined from the "Flipkart/foxtrot" project. We add the "-c"
argument to specify that "~/bugswarm/" directory contains the required BugSwarm components to run the pipeline
sucessfully. If successful, metadata will be pushed to our specified MongoDB and the Artifact is pushed to the
DockerHub repository we specified.

#### Reproducing a Pair
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
$ ./run_reproduce_pair.sh -r Flipkart/foxtrot -f 433449696 -p 433455764 -t 2
```
The example above will take the repo-slug "Flipkart/foxtrot" and both failed/passed job id to reproduce through
the Reproducer component of the pipeline. We use 2 threads to run the process. If successful, we push the Artifact to the DockerHub repository specified
in the "credentials.py" file and push metadata to the MongoDB.

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
$ python3 generate_pair_input.py --repo stormpath/stormpath-sdk-java --include-resettable --include-test-failures-only --include-archived-only --classified-code --classified-exception NullPointerException -o /home/user/results_output.txt
```
The example above will include job pairs that were previously attempted to reproduce from the Artifact database collection,
among those job pairs we include only those that have test failure according to the Analyzer, marked
as resettable, and finally we restrict the job pairs further to those that were classified with having 
the "NullPointerException".

## Questions:
Visit our FAQ docs [page](docs/Frequently-Answered-Questions.md)

