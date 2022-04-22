#!/bin/bash
set -e
set -u

POSTGRES_USER=spatial
POSTGRES_DB=spatial

echo "Running test queries..."
psql -v ON_ERROR_STOP=1 -h localhost -p 5432 -U $POSTGRES_USER -d $POSTGRES_DB -a -f ./db/run_test.sql
