FROM ubuntu:20.04
RUN apt-get update && apt-get install -y git sudo gnupg \
	vim nano tmux screen less python3 zip wget curl && \
	groupadd rvm && groupadd docker && \
	wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | \
	sudo apt-key add - && \
	echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu" \
		"focal/mongodb-org/4.4 multiverse" | \
		sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list && \
	sudo apt-get update && \
	sudo apt-get install mongodb-org-shell && \
	useradd bugswarm && sudo usermod -aG rvm,docker bugswarm && \
	chsh bugswarm -s /bin/bash && \
	echo bugswarm ALL=NOPASSWD:ALL | sudo tee -a /etc/sudoers && \
	mkdir /home/bugswarm && chown bugswarm /home/bugswarm && \
	ln -snf /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
	echo America/Los_Angeles > /etc/timezone
USER bugswarm
RUN cd /home/bugswarm; git clone https://github.com/BugSwarm/bugswarm
WORKDIR /home/bugswarm/bugswarm/
RUN sudo su bugswarm -c ./provision.sh && \
	echo "source /etc/profile.d/rvm.sh" >> /home/bugswarm/.bashrc && \
	echo "source ~/.bashrc" >> /home/bugswarm/.bash_profile

