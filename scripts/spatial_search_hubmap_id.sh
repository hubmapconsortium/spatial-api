#!/bin/bash
set -e
set -u

SCHEME_HOST_PORT=http://localhost:5001
VERBOSE=

usage()
{
  echo "Usage: $0 [-H] [-v] [-h]"
  echo " -H Scheme, host, and port (default $SCHEME_HOST_PORT)"
  echo " -v Verbose"
  echo " -h Help"
  exit 2
}

while getopts 'H:vh' arg; do
  case $arg in
    H) SCHEME_HOST_PORT=$OPTARG ;;
    v) VERBOSE='--verbose' ;;
    h|?) usage ;;
  esac
done

echo "Scheme, host, and port: ${SCHEME_HOST_PORT}"

shift $((OPTIND-1))

echo
echo ">>> Testing spatialapi endpoint spatial_search_hubmap_id..."
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/spatial-search/hubmap_id \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 300,
  "hubmap_id": "HBM795.TSPP.994"
  }'
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/spatial-search/hubmap_id \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 300,
  "hubmap_id": "HBM795.TSPP.994",
  "cell_type": "Connecting Tubule"
  }'
echo

echo
echo ">>> These should fail validation..."
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/spatial-search/hubmap_id \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHBird",
  "radius": 250,
  "hubmap_id": "HBM795.TSPP.994"
  }'
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/spatial-search/hubmap_id \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": "twoHunderdFifty",
  "hubmap_id": "HBM795.TSPP.994"
  }'
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/spatial-search/hubmap_id \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 300,
  "hubmap_id": "HBM795.TSPP.994",
  "xyzzy": "bad key"
  }'
echo
