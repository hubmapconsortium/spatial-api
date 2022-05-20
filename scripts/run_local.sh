#!/bin/bash

# To recreate the containers, load the data, and run the tests...
# $ ./scripts/run_local.sh -dlt

usage()
{
  echo "Usage: $0 [-d] [-r] [-h]"
  echo "Default action is to create and bring up the database and MSAPI containers"
  echo " -d Down and destroy containers before bringing them up"
  echo " -l Load data from Neo4J into database tables after a -d"
  echo " -t run the Tests after bringing up the containers"
  echo " -h Help"
  exit 2
}

unset VERBOSE
while getopts 'dlth' c; do
  case $c in
    d) DOWN=true ;;
    l) LOAD=true ;;
    t) TESTS=true ;;
    h|?) usage ;;
  esac
done

shift $((OPTIND-1))

which python3
status=$?
if [[ $status != 0 ]] ; then
    echo '*** Python3 must be installed!'
    echo '*** Try running scripts/install_venv.sh'
    exit
fi

if [ $DOWN ]; then
  echo ">>> Shut down and destroy containers before bringing them up..."
  echo
  docker-compose -f docker-compose.local.yml down --rmi all
fi

echo
echo ">>> Create and bring up the database and MSAPI containers..."
echo
docker network create shared-web
docker-compose -f docker-compose.local.yml up --build -d
sleep 5
docker-compose -f docker-compose.yml up --build -d

if [ $DOWN -a $LOAD ]; then
  echo
  echo ">>> Rebuilding database after destroying its container..."
  echo
  (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/spatial_manager.py)
fi

if [ $TESTS ]; then
  echo
  echo ">>> Run the Tests after bringing up the containers..."
  echo
  ./scripts/search_hubmap_id.sh
  ./scripts/spatial_search_hubmap_id.sh
  ./scripts/spatial_search_point.sh
fi

echo
echo "Done!"
