#!/bin/bash
set -e
set -u

echo
echo ">>> Testing spatialapi endpoint search_hubmap_point..."
echo

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search/point \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 250,
  "x": 10, "y": 10, "z": 10
  }'
echo

echo
echo ">>> These should fail validation..."
echo

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search/point \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHBird",
  "radius": 250,
  "x": 10, "y": 10, "z": 10
  }'
echo

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search/point \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": "twoHundredFifty",
  "x": 10, "y": 10, "z": 10
  }'
echo

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search/point \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 250,
  "x": "ten", "y": 10, "z": 10
  }'
echo

