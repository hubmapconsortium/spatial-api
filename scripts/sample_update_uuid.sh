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
echo ">>> Testing sample_update_uuid on $SCHEME_HOST_PORT..."
echo

# found...
curl $VERBOSE --request PUT -si "${SCHEME_HOST_PORT}/sample/update/uuid/91832ec2f9dad1468f4f3bf18ee1f310"

# not found....
curl $VERBOSE --request PUT -si "${SCHEME_HOST_PORT}/sample/update/uuid/01832ec2f9dad1468f4f3bf18ee1f310"

echo
echo ">>> These should fail validation..."
echo

curl $VERBOSE --request PUT -si "${SCHEME_HOST_PORT}/sample/update/uuid/Q1832ec2f9dad1468f4f3bf18ee1f310"

curl $VERBOSE --request PUT -si "${SCHEME_HOST_PORT}/sample/update/uuid/91832ec2f9dad1468f4f3bf18ee1f3100"
