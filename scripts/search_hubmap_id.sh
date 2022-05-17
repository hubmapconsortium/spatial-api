#!/bin/bash
set -e
set -u

echo
echo ">>> Testing spatialapi endpoint search_hubmap_id..."
echo

curl -si 'localhost:5001/search/hubmap_id/HBM634.MMGK.572/radius/16.2'

curl -si 'localhost:5001/search/hubmap_id/HBM634.MMGK.572/radius/0.01'
