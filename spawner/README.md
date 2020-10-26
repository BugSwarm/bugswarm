## BugSwarm Spawner
A docker image that contain all required packages in `provision.sh` and can spawn pipeline jobs.

### Building the Spawner
1. Build the spawner using docker
	```sh
	$ cd spawner
	$ docker build -t bugswarm-spawner .
	```

### Starting the Spawner Container
There are two ways to run the spawner.

#### Run Docker Inside Docker
1. Run the container with `--privileged` mode.
	```sh
	$ docker run --privileged -it bugswarm-spawner
	```
1. Start docker daemon and build and run the database container.
	```sh
	$ sudo dockerd &
	$ cd database
	$ docker build -t bugswarm-db .
	$ cd ..
	$ docker run -tid -p 27017:27017 -p 5000:5000 bugswarm-db
	```
	(not tested)

#### Run Docker on Host
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
1. Make sure `bugswarm-db` is built and set up on the host.

### Setting up environment
1. Inside the container, pull the git repository
	```sh
	$ git pull
	```
1. Add the credentials file
	```sh
	$ cat > bugswarm/common/credentials.py
	```
1. Re-run `./provision.sh`
	```sh
	$ ./provision.sh
	```
1. Continue with any other commands (e.g. `./run_reproduce_project.sh`)

