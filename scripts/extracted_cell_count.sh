#!/bin/bash
set -e
set -u

SCHEME_HOST_PORT=http://spatial-api.dev.hubmapconsortium.org
BEARER_TOKEN=
SAMPLE_UUID=
VERBOSE=

usage()
{
  echo "Usage: $0 [-H SCHEME_HOST_PORT] [-s SAMPLE_UUID] [-t BEARER_TOKEN] [-v] [-h]"
  echo " -H Scheme, host, and port (default $SCHEME_HOST_PORT)"
  echo " -t BEARER_TOKEN (no default)"
  echo " -s SAMPLE_UUID (no default)"
  echo " -v Verbose"
  echo " -h Help"
  exit 2
}

while getopts 'H:t:s:vh' arg; do
  case $arg in
    H) SCHEME_HOST_PORT=$OPTARG ;;
    t) BEARER_TOKEN=$OPTARG ;;
    s) SAMPLE_UUID=$OPTARG ;;
    v) VERBOSE='--verbose' ;;
    h|?) usage ;;
  esac
done

shift $((OPTIND-1))

echo "Scheme, host, and port: ${SCHEME_HOST_PORT}"
echo "Bearer Token: ${BEARER_TOKEN}"
echo "Sample UUID: ${SAMPLE_UUID}"

echo
echo ">>> Testing spatialapi endpoint that is called from the Thread in ingestapi..."
echo

curl $VERBOSE --request POST \
 --url ${SCHEME_HOST_PORT}/sample/extracted-cell-count-from-secondary-analysis-files \
 --header 'Authorization': "Bearer ${BEARER_TOKEN}" \
 --header 'X-Hubmap-Application': 'ingest-api' \
 --header 'Accept': 'application/json' \
 --header 'Content-Type: application/json' \
 --data '{
    "sample_uuid: "${SAMPLE_UUID}",
    "cell_type_counts": "HBM795.TSPP.994"
  }'
echo
