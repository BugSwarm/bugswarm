FROM ubuntu:20.04

ENV TZ=America/Los_Angeles
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US

COPY . /root/bugswarm/database

WORKDIR /root/bugswarm/database
RUN ./provision_container.sh

CMD ./mongo_entrypoint.sh && tail -f /dev/null
