#!/bin/bash

# To recreate the containers, and load the data...
# $ ./scripts/run_local.sh -s -d TOKEN

# $ docker exec -ti spatial-api /bin/sh

# To get the BEARER_TOKEN, login through the UI (https://ingest.hubmapconsortium.org/) to get the credentials...
# In Firefox open 'Tools > Browser Tools > Web Developer Tools'.
# Click on "Storage" then the dropdown for "Local Storage" and then the url,
# Applications use the "groups_token" from the returned information.
# UI times-out in 15 min so close the browser window, and the token will last for a day or so.

usage()
{
  echo
  echo "Usage: $0 [-d BEARER_TOKEN] [-s] [-D] [-t] [-h]"
  echo "Default action is to do nothing"
  echo "Optional parameters:"
  echo " -d BEARER_TOKEN - Rebuild DB"
  echo " -s              - Rebuild Server"
  echo " -D              - Shutdown and destroy both containers and then exit"
  echo " -t              - Run the Tests after bringing up the containers"
  echo " -h              - Help"
  exit 2
}

unset VERBOSE
while getopts 'd:sDth' c; do
  case $c in
    d) DB=true; BEARER_TOKEN=$OPTARG ;;
    s) SERVER=true ;;
    D) DOWN=true ;;
    t) TESTS=true ;;
    h|?) usage ;;
  esac
done

shift $(($OPTIND - 1))

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
  (cd server; python3 -m venv venv; pip install -r ../requirements.txt; )
fi
source ./server/$ACTIVATE

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

  # At this point the Database is up with all tables and constraints are created.
  # Some geometric test data loaded, but no data source data loaded (e.g., the DB is empty).
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

if [ $DB ]; then
  echo
  echo ">>> Rebuilding database (through server) after destroying its container and reloading the schema..."
  echo
  ./scripts/db_rebuild.sh -H http://localhost:5001 -D localhost:5432 -t $BEARER_TOKEN -r
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
