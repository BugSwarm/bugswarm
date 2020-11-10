FROM ubuntu:20.04
RUN apt-get update && apt-get install git sudo -y \
	vim nano tmux screen less python3 zip wget curl && \
	groupadd rvm && groupadd docker && \
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

