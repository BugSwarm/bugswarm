FROM ubuntu:20.04
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

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
	  	apt-transport-https -y \
		gnupg \
		wget

RUN wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add

RUN \   
	echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list && \
	apt-get update && \
	apt-get install \
		-y mongodb-org mongodb-org-server mongodb-mongosh mongodb-org-mongos mongodb-org-tools

RUN \
	apt-get update && \
	apt-get install \
		build-essential python3.8 python3.8-dev python3-pip python3.8-venv -y

RUN \ 
	update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1 && \
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
	python3.8 -m pip install pip --upgrade && \
	python3.8 -m pip install wheel

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
