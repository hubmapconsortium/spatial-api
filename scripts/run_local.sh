#!/bin/bash

# To recreate the containers, load the data, and run the tests...
# $ ./scripts/run_local.sh -dlt

usage()
{
  echo "Usage: $0 [-d] [-s] [-D] [-t] [-h]"
  echo "Default action is to do nothing"
  echo " -d Rebuild DB"
  echo " -s Rebuild Server"
  echo " -D Shutdown and destroy both containers and then exit"
  echo " -t run the Tests after bringing up the containers"
  echo " -h Help"
  exit 2
}

unset VERBOSE
while getopts 'dsDth' c; do
  case $c in
    d) DB=true ;;
    s) SERVER=true ;;
    D) DOWN=true ;;
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
    exit 1
fi

ACTIVATE='venv/bin/activate'
if [[ ! -r ./server/$ACTIVATE ]]; then
  echo '*** Building venv....'
  python3 -m pip install --upgrade pip
  (cd server; python3 -m venv venv; source $ACTIVATE; pip install -r ../requirements.txt; )
fi

if [ $DOWN ]; then
  echo ">>> Shut down and destroy DB and SERVER containers..."
  echo
  docker-compose -f docker-compose.db.local.yml down --rmi all
  docker-compose -f docker-compose.api.local.yml down --rmi all
  exit 0
fi

if [ $DB ] || [ $SERVER ]; then
  docker network create shared-web
fi

if [ $DB ]; then
  echo ">>> Shut down and destroy DB container before bringing it up..."
  echo
  docker-compose -f docker-compose.db.local.yml down --rmi all
  docker-compose -f docker-compose.db.local.yml up --build -d

  echo
  echo ">>> Sleeping to give the DB a chance to start before rebuilding it..."
  sleep 5

  DATA_OUT_JSON=scripts/psc/data_out.json
  if [[ ! -f $DATA_OUT_JSON ]]; then
    echo "ERROR: You need to build and copy the $DATA_OUT_JSON file from the PSC machine."
    exit 1
  fi

  echo
  echo ">>> Rebuilding database after destroying its container..."
  echo
  (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/spatial_manager.py)

  (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/cell_annotation_manager.py --load)
  (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py --process_json)
fi

if [ $SERVER ]; then
  SERVER_LOG=server/log
  mkdir -p $SERVER_LOG

  APP_LOCAL_PROPERTIES=server/resources/app.local.properties
  if [[ ! -f $APP_LOCAL_PROPERTIES ]]; then
    echo "ERROR: You need to create a $APP_LOCAL_PROPERTIES file."
    exit 1
  fi

  echo ">>> Shut down and destroy SERVER container before bringing it up..."
  echo
  docker-compose -f docker-compose.api.local.yml down --rmi all
  cp /dev/null ${SERVER_LOG}/uwsgi-spatial-api.log
  docker-compose -f docker-compose.api.local.yml up --build -d
fi

if [ $TESTS ]; then
  echo
  echo ">>> Run the Tests after bringing up the containers..."
  echo
  (cd server; export PYTHONPATH=.; python3 ./tests/geom.py -c)
  ./scripts/search_hubmap_id.sh
  ./scripts/spatial_search_hubmap_id.sh
  ./scripts/spatial_search_point.sh
fi

if [ ! $DB ] && [ ! $SERVER ] && [ ! $DOWN ] && [ ! $TESTS ] ; then
  echo "Nothing to do?!"
  echo
  usage
fi

echo
echo "Done!"
