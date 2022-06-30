#!/bin/sh

trap "exit" INT

# Load data into various tables...
CONFIG=resources/app.dev.properties
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/spatial_manager.py -C $CONFIG)
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/cell_annotation_manager.py -l -C $CONFIG)
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py -p -C $CONFIG)

echo "Tests..."
(cd server; export PYTHONPATH=.; python3 ./tests/geom.py -c -C $CONFIG)
#./scripts/search_hubmap_id.sh -H https://spatial-api.dev.hubmapconsortium.org
#./scripts/spatial_search_hubmap_id.sh -H https://spatial-api.dev.hubmapconsortium.org
#./scripts/spatial_search_point.sh -H https://spatial-api.dev.hubmapconsortium.org
