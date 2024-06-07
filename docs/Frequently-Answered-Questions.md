# Frequently Answered Questions

## What accounts do I need to sign up to generate the credentials?

* [GitHub](https://github.com/join) (even if mining Travis)
* [Travis CI](https://travis-ci.com/signup) (only if mining Travis)
* [Docker Hub](https://hub.docker.com/signup)

## What credentials do I input?

* `DOCKER_HUB_REPO` - The DockerHub repository that will hold Docker Images pushed by the BugSwarm
  Reproducer. For example `bugswarm/images`.
* `DOCKER_HUB_CACHED_REPO` - The DockerHub repository that will hold Docker Images pushed by the CacheDependencies step
  in the BugSwarm Reproducer. Leave this blank to skip caching dependencies. For example `bugswarm/cached-images`.
* `DOCKER_HUB_USERNAME` - This is the username credential being used by the DockerHub API to access the `DOCKER_HUB_REPO`. For example `bugswarm`.
* `DOCKER_HUB_PASSWORD` - This is the password credential being used by the DockerHub API to access the `DOCKER_HUB_REPO`. You can also use an [access token](https://docs.docker.com/docker-hub/access-tokens/) instead.
* `GITHUB_TOKENS` - A [GitHub Access Token](https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line)
  to perform Git Operations over HTTPS via the Git API. The token only needs "public access", so it does not need any additional scopes in the "Select scopes" page. (used for Mining projects)
* `TRAVIS_TOKENS` - A [Travis CI Access Token](https://developer.travis-ci.com/authentication) to send authenticated requests
  to Travis CI. (used for gathering builds)
* `DATABASE_PIPELINE_TOKEN` - The token of a user's account used to access MongoDB.
  ('testDBPassword' if using Docker image of Mongo)
* `COMMON_HOSTNAME`- This hostname is used to integrate the API usage with your local database. It should be `<LOCAL-IPADDRESS>:5000`, for example `127.0.0.1:5000`.

## How do I double check whether my tokens are valid?

### GitHub Tokens

* The GitHub tokens should look like this in `credentials.py`:

    ```py
    GITHUB_TOKENS = ['ghp_ABcdEfghijKLMNOPQrStUvwXyz0123456789']
    ```

* You can verify the token using the following curl command:

    ```sh
    curl -H 'Authorization: token ghp_ABcdEfghijKLMNOPQrStUvwXyz0123456789' https://api.github.com/repos/BugSwarm/bugswarm
    ```

* If you see `{"message": "Bad credentials ...`, then the token is not valid.
  ([Reference](https://developer.github.com/v3/auth/#via-oauth-and-personal-access-tokens))

### Docker Password / Tokens

* The Docker tokens should look like this in `credentials.py`:

    ```py
    DOCKER_HUB_REPO = 'YOUR_USER_NAME/REPO_1'
    DOCKER_HUB_CACHED_REPO = 'YOUR_USER_NAME/REPO_2'
    DOCKER_HUB_USERNAME = 'YOUR_USER_NAME'
    DOCKER_HUB_PASSWORD = '11223344-5566-7788-9900-aabbccddeeff'
    ```

* You can verify the token using the docker client:

    ```sh
    $ docker login
    # enter your username (YOUR_USER_NAME)
    # enter your password / token (11223344-5566-7788-9900-aabbccddeeff)
    $ docker pull ubuntu:20.04
    $ docker tag ubuntu:20.04 YOUR_USER_NAME/REPO_1:docker_test_image
    $ docker tag ubuntu:20.04 YOUR_USER_NAME/REPO_2:docker_test_image
    $ docker push YOUR_USER_NAME/REPO_1:docker_test_image
    $ echo $?
    $ docker push YOUR_USER_NAME/REPO_2:docker_test_image
    $ echo $?
    ```

* If one of the `echo $?` gives a non-zero value, then the password / token is not valid.

### Travis Token

* The Travis tokens should look like this in `credentials.py`:

    ```py
    TRAVIS_TOKENS = ['1234567890A-bCdEfGhIjK']
    ```

* You can verify the token using the following curl command:

    ```sh
    curl -H "Travis-API-Version: 3" -H "Authorization: token 1234567890A-bCdEfGhIjK" https://api.travis-ci.com/repos
    ```

* If you see `access denied`, then the token is not valid.
  ([Reference](https://developer.travis-ci.com/authentication))

## BugSwarm still using old credentials input?

In the case where you modify your credentials under the `common/credentials.py` file, but ran the `provision.sh`
script previously, the BugSwarm package will still retain the old values. You would need to uninstall the package and
run the `provision.sh` script once more.

## Have multiple instances of MongoDB Running?

If you have an existing MongoDB instance running on your machine, it's most likely utilizing the default port `27017`.
In the case where you would want to use our provided Dockerfile for the database you must change the port in a few spots.

For example, lets use port `27020` when running the Docker image of the database, the command would be:

```
docker run -it -p 27020:27017 -p 5000:5000 bugswarm-db (Note the change in the first -p argument)
```

So now when connecting to this instance of Mongo, the command would be:

```
mongosh --port 27020
```

In the case where the second `-p` argument for port `5000` is used, our BugSwarm pipeline API port, we can also map to a
different port as follows:

```
docker run -it -p 27017:27017 -p 5002:5000 bugswarm-db (Note the change in the second -p argument)
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

## How to change the database token?

1. Connect to the database

    ```sh
    mongosh
    ```

1. Execute the following commands in Mongo Shell

    ```
    > use bugswarm
    > db.accounts.find()
    > db.accounts.findAndModify({
    ... query: { email: "pipeline.bugswarm@gmail.com", token: "testDBPassword" },
    ... update: { $set: { token: "new-token" } }
    ... })
    > db.accounts.find()
    > exit
    ```

1. The new token will be `new-token`. Be sure to update `DATABASE_PIPELINE_TOKEN` in `common/credentials.py`.
