# Spatial API

## Server
To rebuld the server in a Docker container.

```bash
scripts/run_local.sh -s
```

## Database
To rebuld the database in a Docker container.

```bash
scripts/run_local.sh -d BEARER_TOKEN
```

On startup the database will process the file `db/initdb.d/initdb.sql` which
will define tables and stored procedures.

## Testing
To run the available test scripts against the server and database

```bash
scripts/run_local.sh -t
```

## Verification
You can use the [HuBMAP CCF Exploration])[https://portal.hubmapconsortium.org/ccf-eui] tool to do some cursory testing
of the items within a radius of a point MSAPI Endpoints.

Navigataion notes for a MAC Notebook:
+ Panning x/y: SHIFT + thumb on mouse pad + finger movement
+ Rotation about the Horizontal: thumb on mouse pad + finger movement up and down
+ Rotation about the Vertical: thumb on mouse pad + finger movement left and right
