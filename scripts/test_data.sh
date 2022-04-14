#!/bin/bash
set -e
set -u

POSTGRES_USER=spatial
POSTGRES_DB=spatial

echo "Loading geom_test and running test query..."
psql -v ON_ERROR_STOP=1 -h localhost -p 5433 -U $POSTGRES_USER -d $POSTGRES_DB -a -f ./db/load_test_data.sql
