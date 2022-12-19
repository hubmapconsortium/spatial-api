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
echo ">>> Testing spatialapi endpoint search_hubmap_point..."
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/point-search \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 270,
  "x": 10, "y": 10, "z": 10
  }'
echo

echo
echo ">>> These should fail validation..."
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/point-search \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHBird",
  "radius": 250,
  "x": 10, "y": 10, "z": 10
  }'
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/point-search \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": "twoHundredFifty",
  "x": 10, "y": 10, "z": 10
  }'
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/point-search \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 250,
  "x": "ten", "y": 10, "z": 10
  }'
echo
