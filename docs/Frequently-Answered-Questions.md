# Frequently Answered Questions

## What credentials do I input?
* `DOCKER_HUB_REPO` - The DockerHub repository that will hold Docker Images pushed by the BugSwarm
  Reproducer. For example `bugswarm/images`.
* `DOCKER_HUB_CACHED_REPO` - The DockerHub repository that will hold Docker Images pushed by the CacheDependencies step
  in the BugSwarm Reproducer. Leave this blank to skip caching dependencies. For example `bugswarm/cached-images`.
* `DOCKER_HUB_USERNAME` - This is the username credential being used by the DockerHub API to access the `DOCKER_HUB_REPO`. For example `bugswarm`.
* `DOCKER_HUB_PASSWORD` - This is the password credential being used by the DockerHub API to access the `DOCKER_HUB_REPO`. You can also use an [access token](https://docs.docker.com/docker-hub/access-tokens/) instead.
* `GITHUB_TOKENS` - A [GitHub Access Token](https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line)
  to perform Git Operations over HTTPS via the Git API. (used for Mining projects)
* `TRAVIS_TOKENS` - A [Travis CI Access Token](https://developer.travis-ci.com/authentication) to send authenticated requests
  to Travis CI. (used for gathering builds)
* `DATABASE_PIPELINE_TOKEN` - The token of a user's account used to access MongoDB.
  ('testDBPassword' if using Docker image of Mongo)
* `COMMON_HOSTNAME`- This hostname is used to integrate the API usage with your local database. It should be `<LOCAL-IPADDRESS>:5000`, for example `127.0.0.1:5000`.

## BugSwarm still using old credentials input?

In the case where you modify your credentials under the `common/credentials.py` file, but ran the `provision.sh`
script previously, the BugSwarm package will still retain the old values. You would need to uninstall the package and
run the `provision.sh` script once more.
  
## Have multiple instances of MongoDB Running?

If you have an existing MongoDB instance running on your machine, it's most likely utilizing the default port `27017`.
In the case where you would want to use our provided Dockerfile for the database you must change the port in a few spots.

For example, lets use port `27020` when running the Docker image of the database, the command would be:
```
$ docker run -it -p 27020:27017 -p 5000:5000 bugswarm-db (Note the change in the first -p argument)
```
So now when connecting to this instance of Mongo, the command would be:
```
$ mongo --port 27020
```
In the case where the second `-p` argument for port `5000` is used, our BugSwarm pipeline API port, we can also map to a
different port as follows:
```
$ docker run -it -p 27017:27017 -p 5002:5000 bugswarm-db (Note the change in the second -p argument)
```
This port will now be set under the `common/credentials.py` file as:
```
COMMON_HOSTNAME=<LOCAL-IPADDRESS>:5002
```
If you have followed these steps, resume at #4 of [Setting up BugSwarm](/README.md#setting-up-bugswarm)

## Why do we use Docker?

Docker is lightweight in comparison to Virtual Machines (VMs). The virtualization environment is interchangeable with
VMs. In principle, Travis CI creates and retains a base Docker image which is the exact build environment. 
 
## Why do we use MongoDB?

MongoDB is an object-oriented, scalable and dynamic NoSQL database. The data is stored as JSON or BSON documents
inside a collection. The use of high performance, availability, and scaling provides easy integration thus 
satisfying the BugSwarm needs.
