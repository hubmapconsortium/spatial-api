#!/bin/bash
set -e
set -u

SCHEME_HOST_PORT=http://0.0.0.0:8484
BEARER_TOKEN=
DATASET_UUID=
SAMPLE_UUID=
VERBOSE=

usage()
{
  echo "Usage: $0 [-H SCHEME_HOST_PORT] [-t BEARER_TOKEN] [-d DATASET_UUID] [-s SAMPLE_UUID] [-v] [-h]"
  echo " -H Scheme, host, and port (default $SCHEME_HOST_PORT)"
  echo " -t BEARER_TOKEN (no default)"
  echo " -d DATASET_UUID (no default)"
  echo " -s SAMPLE_UUID (no default)"
  echo " -v Verbose"
  echo " -h Help"
  exit 2
}
# NOTE: To retrieve the token for the build_json_token:
# In Firefox open 'Tools > Browser Tools > Web Developer Tools'.
# Login through the UI(https://portal.hubmapconsortium.org/).
# In the Web Developer Tools, click on 'Network', and then one of the search endpoints.
# Copy the 'Request Header', 'Authoriation : Bearer' token.
#
# $ ./scripts/ingest_api_manager.sh -d 4a4c98d9dd27afd652cdab74f9952bf1 -t TOKEN
# $ ./scripts/ingest_api_manager.sh -H https://ingest-api.dev.hubmapconsortium.org -d 4a4c98d9dd27afd652cdab74f9952bf1 -t TOKEN
#
# NOTE: See sample_extract_cell_count.sh for a list of local sample and dataset uuids.

while getopts H:t:d:s:vh arg; do
  case $arg in
    H) SCHEME_HOST_PORT=$OPTARG ;;
    t) BEARER_TOKEN=$OPTARG ;;
    d) DATASET_UUID=$OPTARG ;;
    s) SAMPLE_UUID=$OPTARG ;;
    v) VERBOSE='--verbose' ;;
    h/?) usage ;;
  esac
done

shift $((OPTIND-1))

echo
echo "Scheme, host, and port: ${SCHEME_HOST_PORT}"
echo "Bearer Token: ${BEARER_TOKEN}"
echo "Dataset UUID: ${DATASET_UUID}"
echo "Sample UUID: ${SAMPLE_UUID}"

echo
curl $VERBOSE -X GET -si "${SCHEME_HOST_PORT}/datasets/${DATASET_UUID}/file-system-abs-path" \
 -H "Authorization: Bearer $BEARER_TOKEN"

echo
curl $VERBOSE -X POST -si "${SCHEME_HOST_PORT}/dataset/extract-cell-count-from-secondary-analysis-files" \
 -H "Authorization: Bearer $BEARER_TOKEN" \
 -H "Content-Type: application/json" \
 -d "{\"ds_uuids\": [ \"${DATASET_UUID}\" ] }"

# The SAMPLE_UUID is only needed below so that when the thread has finished it can tell
# the code in spatial-api what sample id the computation was done for.
echo
curl $VERBOSE -X POST -si "${SCHEME_HOST_PORT}/dataset/begin-extract-cell-count-from-secondary-analysis-files-async" \
 -H "Authorization: Bearer $BEARER_TOKEN" \
 -H "Content-Type: application/json" \
 -d "{\"ds_uuids\": [ \"${DATASET_UUID}\" ], \"sample_uuid\": \"${SAMPLE_UUID}\"}"
