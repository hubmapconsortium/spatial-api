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
echo ">>> Testing spatialapi endpoint search_hubmap_id on $SCHEME_HOST_PORT..."
echo

curl $VERBOSE -si "${SCHEME_HOST_PORT}/search/hubmap-id/HBM634.MMGK.572/radius/17/target/VHMale"

curl $VERBOSE -si "${SCHEME_HOST_PORT}/search/hubmap-id/HBM634.MMGK.572/radius/0.01/target/VHFemale"

echo
echo ">>> These should fail validation..."
echo

curl $VERBOSE -si "${SCHEME_HOST_PORT}/search/hubmap-id/HBM634.MMGK.572/radius/one/target/VHFemale"

curl $VERBOSE -si "${SCHEME_HOST_PORT}/search/hubmap-id/HBM634.MMGK.572/radius/0.01/target/VHBird"
