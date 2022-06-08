#!/bin/bash

# To recreate the containers, load the data, and run the tests...
# $ ./scripts/run_local.sh -dlt

usage()
{
  echo "Usage: $0 [-d] [-s] [-t] [-h]"
  echo "Default action is to do nothing"
  echo " -d Rebuild DB"
  echo " -s Rebuild Server"
  echo " -t run the Tests after bringing up the containers"
  echo " -h Help"
  exit 2
}

unset VERBOSE
while getopts 'dsth' c; do
  case $c in
    d) DB=true ;;
    s) SERVER=true ;;
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

ACTIVATE='venv/bin/activate'
if [[ ! -r ./server/$ACTIVATE ]]; then
  echo '*** Building venv....'
  python3 -m pip install --upgrade pip
  (cd server; python3 -m venv venv; source $ACTIVATE; pip install -r ../requirements.txt; )
fi

if [ $DB ] || [ $SERVER ]; then
  docker network create shared-web
fi

if [ $DB ]; then
  echo ">>> Shut down and destroy DB container before bringing it up..."
  echo
  docker-compose -f docker-compose.local.yml down --rmi all
  docker-compose -f docker-compose.local.yml up --build -d

  echo
  echo ">>> Sleeping to give the DB a chance to start before rebuilding it..."
  sleep 5

  echo
  echo ">>> Rebuilding database after destroying its container..."
  echo
  (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/spatial_manager.py)

  (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/cell_annotation_manager.py --load)
  (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py --process_json)
fi

if [ $SERVER ]; then
  echo ">>> Shut down and destroy SERVER container before bringing it up..."
  echo
  docker-compose -f docker-compose.yml down --rmi all
  docker-compose -f docker-compose.yml up --build -d
fi

if [ $TESTS ]; then
  echo
  echo ">>> Run the Tests after bringing up the containers..."
  echo
  ./scripts/search_hubmap_id.sh
  ./scripts/spatial_search_hubmap_id.sh
  ./scripts/spatial_search_point.sh
fi

if [ ! $DB ] && [ ! $SERVER ] && [ ! $TESTS ] ; then
  echo "Nothing to do?!"
  echo
  usage
fi

echo
echo "Done!"
