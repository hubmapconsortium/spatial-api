#!/bin/bash

read -p "Are you REALLY sure that you want to DELETE EVERYTHING in the current DEV database and then rebuild it [Y/n]? " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborting..."
  exit 1
fi

SCHEME_HOST_PORT_DEV=https://spatial-api.dev.hubmapconsortium.org

DB_HOST_PORT=18.205.215.12:5432
DB_USER=spatialdb_dev_user
DB_NAME=spatial-api_dev

# IMPORTANT NOTES:
# 1) The TOKEN, must be a "data-admin" token since the endpoints being hit in db_rebuild.sh require that.
# 2) the DB_USER "must be owner" of the tables created in db/init.db/initdb.sql
#
# To run type the following line filling in the data-admin token...
# export TOKEN=""; ./scripts/dev_db_rebuild.sh
# You will be prompted for the database password...

./scripts/db_rebuild.sh -H $SCHEME_HOST_PORT_DEV -D $DB_HOST_PORT -U $DB_USER -d $DB_NAME -t $TOKEN -r

echo "Done!"
