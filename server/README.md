# Spatial API

## Server
To rebuld the server in a Docker container.

```bash
scripts/run_local.sh -s
```

## Database
To rebuld the database in a Docker container.

On startup it will process the file `db/initdb.d/initdb.sql` which
will define tables and stored procedures.

```bash
scripts/run_local.sh -d
```

###Build
To build the json, copy it to the PSC and build.
```bash
cd server
export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py --build_json
export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py --run_psc
```

## Testing

You can use the [HuBMAP CCF Exploration])[https://portal.hubmapconsortium.org/ccf-eui] tool to do some cursory testing
of the items within a radius of a point MSAPI Endpoints.

Navigataion notes for a MAC Notebook:
+ Panning x/y: SHIFT + thumb on mouse pad + finger movement
+ Rotation about the Horizontal: thumb on mouse pad + finger movement up and down
+ Rotation about the Vertical: thumb on mouse pad + finger movement left and right
