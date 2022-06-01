# Spatial API

## Build Env

````bash
python3 -m pip install --upgrade pip
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
````

## Data

###Build
Build json, copy it to the PSC and build.
```bash
cd server
export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py --build_json
export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py --run_psc
```

### Load
First, remove the database container and rebuild it. On startup it will process the file `db/initdb.d/initdb.sql` which
will define tables and stored procedures. Then, load the tables with the following.
```bash
docker stop $(docker ps -q --filter ancestor=spatial-api_db )
docker rmi spatial-api_db
scripts/run_local.sh
cd server
pip install -r ../requirements.txt
export PYTHONPATH=.; python3 ./spatialapi/manager/cell_annotation_manager.py --load
export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py --process_json
```

## Testing

You can use the [HuBMAP CCF Exploration])[https://portal.hubmapconsortium.org/ccf-eui] tool to do some cursory testing
of the items within a radius of a point MSAPI Endpoints.

Navigataion notes for a MAC Notebook:
+ Panning x/y: SHIFT + thumb on mouse pad + finger movement
+ Rotation about the Horizontal: thumb on mouse pad + finger movement up and down
+ Rotation about the Vertical: thumb on mouse pad + finger movement left and right
