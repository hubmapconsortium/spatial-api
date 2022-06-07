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
  "radius": 300,
  "hubmap_id": "HBM795.TSPP.994"
  }'
echo

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search/hubmap_id \
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

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search/hubmap_id \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHBird",
  "radius": 250,
  "hubmap_id": "HBM795.TSPP.994"
  }'
echo

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search/hubmap_id \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": "twoHunderdFifty",
  "hubmap_id": "HBM795.TSPP.994"
  }'
echo

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search/hubmap_id \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 300,
  "hubmap_id": "HBM795.TSPP.994",
  "xyzzy": "bad key"
  }'
echo
