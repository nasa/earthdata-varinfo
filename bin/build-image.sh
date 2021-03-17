#!/bin/bash

image="sds/varinfo"
tag=${1:-latest}

# Look for existing versions of the image and remove
#
old=$(docker images | grep "$image" | grep "$tag" | awk '{print $3}')
if [ ! -z "$old" ]; then
  docker rmi "$old"
fi

# Build the image
#
docker build -t ${image}:${tag} .
