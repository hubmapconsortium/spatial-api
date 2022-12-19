#!/bin/bash
set -e
set -u

SCHEME_HOST_PORT=https://spatial-api.dev.hubmapconsortium.org
# SCHEME_HOST_PORT=http://localhost:5001
DATABASE_HOST_PORT=18.205.215.12:5432
BEARER_TOKEN=
INCREMENTAL_REINDEX=0
RECREATE_DATABASE_TABLES=0
VERBOSE=

usage()
{
  echo "Usage: $0 [-H SCHEME_HOST_PORT] [-D DATABASE_HOST_PORT] [-t BEARER_TOKEN] [-i] [-r] [-v] [-h]"
  echo " -H Scheme, host, and port of spatial-api server (${SCHEME_HOST_PORT})"
  echo " -D HOST:PORT Database Host and Port separated by a colon ':' (${DATABASE_HOST_PORT})"
  echo " -t BEARER_TOKEN (see text below)"
  echo " -i Incremental Reindex samples that are older than last processed"
  echo " -r Delete and then recreate Databases Tables from 'db/initdb.d/initdb.sql'"
  echo " -v Verbose"
  echo " -h Help"
  echo
  echo "To get the BEARER_TOKEN, login through the UI (https://ingest.hubmapconsortium.org/) to get the credentials"
  echo "In Firefox open 'Tools > Browser Tools > Web Developer Tools'."
  echo "Click on "Storage" then the dropdown for "Local Storage" and then the url,"
  echo "and use the "groups_token" from the returned information."
  exit 2
}

while getopts 'H:D:t:irvh' arg; do
  case $arg in
    H) SCHEME_HOST_PORT=$OPTARG ;;
    D) DATABASE_HOST_PORT=$OPTARG ;;
    t) BEARER_TOKEN=$OPTARG ;;
    i) INCREMENTAL_REINDEX=1 ;;
    r) RECREATE_DATABASE_TABLES=1 ;;
    v) VERBOSE='--verbose' ;;
    h|?) usage ;;
  esac
done

shift $((OPTIND-1))

echo
echo "spatial-api: Scheme, host, and port: ${SCHEME_HOST_PORT}"
echo "db: host, port: ${DATABASE_HOST_PORT}"
echo "Bearer Token: ${BEARER_TOKEN}"
echo "Incremental Reindex: ${INCREMENTAL_REINDEX}"
echo "Recreate database tables: ${RECREATE_DATABASE_TABLES}"
echo

IFS=':'; arr_db_host_port=($DATABASE_HOST_PORT); unset IFS;
if [[ ${#arr_db_host_port[@]} -ne 2 ]]; then
  echo
  echo "ERROR: -D HOST:PORT Both host and port must be specified separated by a ':'."
  echo
  usage
  exit 1
fi
db_host=${arr_db_host_port[0]}
db_port=${arr_db_host_port[1]}

if [[ $RECREATE_DATABASE_TABLES -eq 1 ]] && [[ $INCREMENTAL_REINDEX -eq 1 ]]; then
  echo
  echo "ERROR: You can only recreate the database tables if you are doing a full reindex and not an incremental one."
  echo
  usage
  exit 1
fi

if [[ $INCREMENTAL_REINDEX -eq 1 ]]; then
  echo
  echo ">>> Extract cell_type_counts for modified samples..."
  curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/samples/incremental-reindex" \
    -H "Authorization: Bearer $BEARER_TOKEN"
  echo
  echo "Done!"
  exit 0
fi

if [[ $RECREATE_DATABASE_TABLES -eq 1 ]]; then
  if [[ `which psql > /dev/null 2>&1; echo $?` -ne 0 ]] ; then
    echo "Installing postgresql using brew..."
    brew install postgresql
  fi
  echo
  echo ">>> Reloading database tables; dbhost: ${db_host}; db_port: ${db_port}"
  echo "Look in the resources/app.properties file for the [postgresql] Passowrd."
  psql -h ${db_host} -p ${db_port} -d spatial -U spatial -f db/initdb.d/initdb.sql
fi

echo
echo ">>> Rebuild Database..."
echo

# This must be done first because the organ-sample-data references it...
echo ">>> Rebuild annotation details ..."
curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/rebuild-annotation-details" \
 -H "Authorization: Bearer $BEARER_TOKEN"

echo
echo ">>> Reindexing all samples..."
curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/samples/reindex-all" \
 -H "Authorization: Bearer $BEARER_TOKEN"

echo "Done!"

#echo
#echo ">>> Extract cell_type_counts for samples of; organ_code: RK..."
#curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/samples/organs/RK/reindex" \
# -H "Authorization: Bearer $BEARER_TOKEN"
#
#echo
#echo ">>> Extract cell_type_counts for samples of; organ_code: LK..."
#curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/samples/organs/LK/reindex" \
# -H "Authorization: Bearer $BEARER_TOKEN"
#
#SAMPLE_ID=2b8f250ca625a3186cc6e2e8e40c3c58
#echo ">>> Extract cell_type_counts for sample_id: ${SAMPLE_ID}..."
#curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/samples/${SAMPLE_ID}/reindex" \
# -H "Authorization: Bearer $BEARER_TOKEN"

# At this point you can add any other organ_codes....
