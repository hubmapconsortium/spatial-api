#!/bin/bash
set -e
set -u

echo
echo ">>> Testing spatialapi endpoint search_hubmap_id..."
echo

curl -si 'localhost:5001/search/hubmap_id/HBM634.MMGK.572/radius/16/target/VHMale'

curl -si 'localhost:5001/search/hubmap_id/HBM634.MMGK.572/radius/0.01/target/VHFemale'

echo
echo ">>> These should fail validation..."
echo

curl -si 'localhost:5001/search/hubmap_id/HBM634.MMGK.572/radius/one/target/VHFemale'

curl -si 'localhost:5001/search/hubmap_id/HBM634.MMGK.572/radius/0.01/target/VHBird'
