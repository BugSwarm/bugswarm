#!/bin/bash

docker stop $(sudo docker ps -a -q)
docker rm $(sudo docker ps -a -q)
docker rmi $(sudo docker images -q)

# Remove exited containers.
docker ps --filter status=dead --filter status=exited -aq | xargs -r docker rm -v
    
# Remove unused images.
docker images --no-trunc | grep '<none>' | awk '{ print $3 }' | xargs -r docker rmi

# Remove unused volumes.
find '/var/lib/docker/volumes/' -mindepth 1 -maxdepth 1 -type d | grep -vFf <(
  docker ps -aq | xargs docker inspect | jq -r '.[] | .Mounts | .[] | .Name | select(.)'
) | xargs -r rm -fr
