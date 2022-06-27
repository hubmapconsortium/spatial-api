#!/bin/sh

DATABASE_HOST='18.205.215.12'
DATABASE_PORT='5432'
DATABASE_NAME='spatial'
DATABASE_USER='spatial'
DATABASE_PASSWORD='test4now'

trap "exit" INT

if [[ `which psql > /dev/null 2>&1; echo $?` -ne 0 ]] ; then
  brew install postgresql
fi

export PGPASSWORD=$DATABASE_PASSWORD

echo "Dropping and Creating test database..."
psql -v ON_ERROR_STOP=1 -h $DATABASE_HOST -p $DATABASE_PORT -U $DATABASE_USER -a <<-EOSQL
  DROP DATABASE IF EXISTS ${DATABASE_NAME};
  CREATE DATABASE ${DATABASE_NAME};
EOSQL

# This file is automatically loaded when the local container is created.
# In this case the instance already exists, and so we must load it.
INIT_DB_SCRIPT=db/initdb.d/initdb.sql
#psql -v ON_ERROR_STOP=1 -h $DATABASE_HOST -p $DATABASE_PORT -U $DATABASE_USER -d $DATABASE_NAME -f $INIT_DB_SCRIPT

# Load data into various tables...
CONFIG=resources/app.dev.properties
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/spatial_manager.py -C $CONFIG)
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/cell_annotation_manager.py -l -C $CONFIG)
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py -p -C $CONFIG)
