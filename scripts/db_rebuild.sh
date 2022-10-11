#!/bin/bash
set -e
set -u

#SCHEME_HOST_PORT=https://spatial-api.dev.hubmapconsortium.org
SCHEME_HOST_PORT=http://localhost:5001
BEARER_TOKEN=
VERBOSE=

usage()
{
  echo "Usage: $0 [-H SCHEME_HOST_PORT] [-t BEARER_TOKEN] [-v] [-h]"
  echo " -H Scheme, host, and port (default $SCHEME_HOST_PORT)"
  echo " -t BEARER_TOKEN (no default)"
  echo " -v Verbose"
  echo " -h Help"
  exit 2
}

while getopts 'H:t:vh' arg; do
  case $arg in
    H) SCHEME_HOST_PORT=$OPTARG ;;
    t) BEARER_TOKEN=$OPTARG ;;
    v) VERBOSE='--verbose' ;;
    h|?) usage ;;
  esac
done

shift $((OPTIND-1))

echo
echo "Scheme, host, and port: ${SCHEME_HOST_PORT}"
echo "Bearer Token: ${BEARER_TOKEN}"

echo
echo ">>> Rebuild Database..."
echo

# This must be done first because the organ-sample-data references it...
echo ">>> Rebuild annotation-details ..."
curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/db/rebuild/annotation-details" \
 -H "Authorization: Bearer $BEARER_TOKEN"

echo
echo ">>> Rebuild organ-sample-data; organ_code: RK..."
curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/db/rebuild/organ-sample-data" \
 -H "Authorization: Bearer $BEARER_TOKEN" \
 -H "Content-Type: application/json" \
 -d "{\"organ_code\": \"RK\"}"

echo
echo ">>> Extract cell_type_counts for samples of; organ_code: RK..."
curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/sample/begin-extract-cell-type-counts-for-all-samples-for-organ_code" \
 -H "Authorization: Bearer $BEARER_TOKEN" \
 -H "Content-Type: application/json" \
 -d "{\"organ_code\": \"RK\"}"

echo
echo ">>> Rebuild organ-sample-data; organ_code: LK..."
curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/db/rebuild/organ-sample-data" \
 -H "Authorization: Bearer $BEARER_TOKEN" \
 -H "Content-Type: application/json" \
 -d "{\"organ_code\": \"LK\"}"

echo
echo ">>> Extract cell_type_counts for samples of; organ_code: RK..."
curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/sample/begin-extract-cell-type-counts-for-all-samples-for-organ_code" \
 -H "Authorization: Bearer $BEARER_TOKEN" \
 -H "Content-Type: application/json" \
 -d "{\"organ_code\": \"RK\"}"

# At this point you can add any other organ_codes....
