# The BugSwarm Client

![The BugSwarm Mascot](https://cloud.githubusercontent.com/assets/8139148/24324903/1101b9a2-114c-11e7-9340-316022ef57d5.png)

The official command line client for the [BugSwarm](http://bugswarm.org) artifact dataset

## Installation
> Requires Python 3.
```
$ pip3 install bugswarm-client
```

## Usage
Download a Docker image and enter the Docker container associated with an artifact.
```shell
$ bugswarm run --image-tag <image_tag>
```
> Depending on how Docker is configured on your machine, you may need to enter an administrator password.

Download a Docker image and enter the Docker container with a shared folder between the container and the host machine.

```shell
$ bugswarm run --image-tag <image_tag> --use-sandbox
```

Show metadata for an artifact.

```shell
$ bugswarm show --image-tag <image_tag> --token <token>
```

Show usage text for the entire tool or for a specific sub-command.

```shell
$ bugswarm --help
$ bugswarm <sub-command> --help
```

Show the version.

```shell
$ bugswarm --version
```

Please note that artifacts are first attempted to be pulled from `bugswarm/cached-images`, and if not found then they are attempted to be pulled from `bugswarm/images`.

## Example

```shell
$ bugswarm run --image-tag square-okio-140452393
$ bugswarm show --image-tag square-okio-140452393 [--token <token>]
```

> You can use BugSwarm Client without a token. However, unauthenticated requests are subject to rate limits (6 requests/minute). [You can request a token here.](http://www.bugswarm.org/contact/)

## Development
Execute the following commands to install the tool.
1. Clone this repository.
    ```
    $ git clone https://github.com/BugSwarm/bugswarm.git
    ```
1. `cd` into the root directory of this repository.
    ```
    $ cd bugswarm
    ```
1. Use client setup file
    ```
    $ mv setup.client.py setup.py
    ```
1. Install the tool.
    ```
    $ pip3 install --upgrade --force-reinstall .
    ```
