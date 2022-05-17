#!/bin/bash
set -e
set -u

echo
echo ">>> Testing spatialapi endpoint spatial_search_hubmap_id..."
echo

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search/hubmap_id \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 250,
  "hubmap_id": "HBM986.FGJM.339"
  }'
echo
