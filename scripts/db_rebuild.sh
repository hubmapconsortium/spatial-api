#!/bin/bash
set -e
set -u

SCHEME_HOST_PORT=https://spatial-api.dev.hubmapconsortium.org
# SCHEME_HOST_PORT=http://localhost:5001
BEARER_TOKEN=
INCREMENTAL_REINDEX=0
VERBOSE=

# To reload the database tables on dev...
# $ psql -h 18.205.215.12 -p 5432 -d spatial -U spatial -f db/initdb.d/initdb.sql

usage()
{
  echo "Usage: $0 [-H SCHEME_HOST_PORT] [-t BEARER_TOKEN] [-v] [-h]"
  echo " -H Scheme, host, and port (default $SCHEME_HOST_PORT)"
  echo " -t BEARER_TOKEN (no default)"
  echo " -i Incremental Reindex samples"
  echo " -v Verbose"
  echo " -h Help"
  exit 2
}

while getopts 'H:t:vih' arg; do
  case $arg in
    H) SCHEME_HOST_PORT=$OPTARG ;;
    t) BEARER_TOKEN=$OPTARG ;;
    i) INCREMENTAL_REINDEX=1 ;;
    v) VERBOSE='--verbose' ;;
    h|?) usage ;;
  esac
done

shift $((OPTIND-1))

echo
echo "Scheme, host, and port: ${SCHEME_HOST_PORT}"
echo "Bearer Token: ${BEARER_TOKEN}"
echo "Incremental Reindex: ${INCREMENTAL_REINDEX}"

if [[ INCREMENTAL_REINDEX -eq 1 ]]; then
  echo
  echo ">>> Extract cell_type_counts for modified samples..."
  curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/samples/incremental-reindex" \
    -H "Authorization: Bearer $BEARER_TOKEN"
  echo
  echo "Done!"
  exit 0
fi

echo
echo ">>> Rebuild Database..."
echo

# This must be done first because the organ-sample-data references it...
echo ">>> Rebuild annotation details ..."
curl $VERBOSE -X PUT -si "${SCHEME_HOST_PORT}/rebuild-annotation-details" \
 -H "Authorization: Bearer $BEARER_TOKEN"

echo
echo ">>> Extract cell_type_counts for all samples..."
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
