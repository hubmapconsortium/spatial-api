#!/bin/sh

DATABASE_HOST='hubmap-postgresql-dev.cylxi65xrqts.us-east-1.rds.amazonaws.com'
DATABASE_NAME='spatial_dev'
DATABASE_USER='fill this in'
DATABASE_PASSWORD='fill this in'

if [[ `which psql > /dev/null 2>&1; echo $?` -ne 0 ]] ; then
  brew install postgresql
fi

export PGPASSWORD=$DATABASE_PASSWORD

# This file is automatically loaded when the local container is created.
# In this case the instance already exists, and so we must load it.
INIT_DB_SCRIPT=db/initdb.d/initdb.sql
psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -f $INIT_DB_SCRIPT

# Load data into various tables...
CONFIG=resources/app.properties
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/spatial_manager.py -C $CONFIG)
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/cell_annotation_manager.py -l -C $CONFIG)
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py -p -C $CONFIG)
