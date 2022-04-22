#!/bin/bash

docker network create shared-web
docker-compose -f docker-compose.local.yml ${@:-up -d}
sleep 5
docker-compose -f docker-compose.yml ${@:-up -d}

# Stop the container and then remove it....
# ./scripts/run_local.sh down