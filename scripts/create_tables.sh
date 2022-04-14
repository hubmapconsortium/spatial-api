#!/bin/bash
set -e
set -u

POSTGRES_USER=spatial
POSTGRES_DB=spatial

# $ createdb -h localhost -p 5433 -U user user

#echo "Dropping and Creating test database..."
#psql -v ON_ERROR_STOP=1 -h localhost -p 5433 -U $POSTGRES_USER -a <<-EOSQL
#  DROP DATABASE IF EXISTS ${POSTGRES_DB};
#  CREATE DATABASE ${POSTGRES_DB};
#EOSQL

echo "Creating tables in database..."
psql -v ON_ERROR_STOP=1 -h localhost -p 5433 -U $POSTGRES_USER -d $POSTGRES_DB -a -f ./db/create_tables.sql
