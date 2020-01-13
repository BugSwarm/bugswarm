FROM ubuntu:16.04
RUN \
	apt-get update && \
  	apt-get install \
  		apt-utils \
    	apt-transport-https \
	    ca-certificates \
	    curl \
	    gnupg-agent \
	    software-properties-common \
		sudo \
	  	git-core \	  	
	  	vim \
	  	locales locales-all \
	  	lsb-release \
	  	ufw -y \
	  	apt-transport-https -y

RUN \ 	
	apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 9DA31620334BD75D9DCB49F368818C72E52529D4 && \
	echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/4.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-4.0.list && \
  	apt-get update && \
  	apt-get install \
  		mongodb-org=4.0.5 mongodb-org-server=4.0.5 mongodb-org-shell=4.0.5 mongodb-org-mongos=4.0.5 mongodb-org-tools=4.0.5 -y

RUN \
	add-apt-repository ppa:deadsnakes/ppa && \
	apt-get update && \
	apt-get install \
		build-essential python3.6 python3.6-dev python3-pip python3.6-venv -y

RUN \ 
	update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 1 && \
	cd ~/ && \
	git clone https://github.com/BugSwarm/bugswarm.git

RUN \
    cd ~/bugswarm && \
    find * -maxdepth 0 -name '*database*' -prune -o -exec rm -rf '{}' ';' && \
	cd ~/bugswarm/database && \
	pip3 install --upgrade --force-reinstall -r requirements.txt

RUN \
	mkdir -p /data/db && \
	chmod 000 ~/bugswarm/database/database/config.py

RUN \
	python3.6 -m pip install pip --upgrade && \
	python3.6 -m pip install wheel

COPY \
	./mongo_entrypoint.sh /root/bugswarm/database

COPY \
	./dump /root/bugswarm/database/dump

RUN \
	chmod 755 /root/bugswarm/database/mongo_entrypoint.sh

ENV LC_ALL en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8

CMD /root/bugswarm/database/mongo_entrypoint.sh && tail -f /dev/null