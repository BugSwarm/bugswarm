FROM ubuntu:20.04

ARG PROVISION_ARGS

RUN apt-get update && apt-get install -y git sudo gnupg \
	vim nano tmux screen less python3 zip wget curl && \
	groupadd rvm && groupadd docker && \
	wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | \
	sudo apt-key add - && \
	echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu" \
		"focal/mongodb-org/6.0 multiverse" | \
		sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list && \
	sudo apt-get update && \
	sudo apt-get install mongodb-mongosh && \
	useradd bugswarm && sudo usermod -aG rvm,docker bugswarm && \
	chsh bugswarm -s /bin/bash && \
	echo bugswarm ALL=NOPASSWD:ALL | sudo tee -a /etc/sudoers && \
	mkdir /home/bugswarm && chown bugswarm /home/bugswarm && \
	ln -snf /usr/share/zoneinfo/America/Los_Angeles /etc/localtime && \
	echo America/Los_Angeles > /etc/timezone
USER bugswarm
RUN cd /home/bugswarm && \
	git config --global user.name "BugSwarm" && \
	git config --global user.email "contact.bugswarm@gmail.com" && \
	git clone https://github.com/BugSwarm/bugswarm
WORKDIR /home/bugswarm/bugswarm/
RUN ./provision.sh ${PROVISION_ARGS} && \
	echo "source /etc/profile.d/rvm.sh" >> /home/bugswarm/.bashrc && \
	echo "source ~/.bashrc" >> /home/bugswarm/.bash_profile

