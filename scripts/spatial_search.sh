#!/bin/bash
set -e
set -u

curl --verbose --request POST \
 --url http://localhost:5001/spatial-search \
 --header 'Content-Type: application/json' \
 --data '{
  "target": "VHMale",
  "radius": 250,
  "x": 10, "y": 10, "z": 10
  }'
echo
