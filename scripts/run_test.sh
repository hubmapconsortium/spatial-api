#!/bin/bash
set -e
set -u

HOST=localhost
PORT=5432
POSTGRES_USER=spatial
POSTGRES_DB=spatial

usage()
{
  echo "Usage: $0 [-H host] [-P port] [-U user] [-D db] [-h]"
  echo " -H Host (default $HOST)"
  echo " -P Port (default $PORT)"
  echo " -U POSTGRES_USER (default $POSTGRES_USER)"
  echo " -D POSTGRES_DB (default $POSTGRES_DB)"
  echo " -h Help"
  exit 2
}

while getopts 'H:P:U:D:h' arg; do
  case $arg in
    H) HOST=$OPTARG ;;
    P) PORT=$OPTARG ;;
    U) POSTGRES_USER=$OPTARG ;;
    D) POSTGRES_DB=$OPTARG ;;
    h|?) usage ;;
  esac
done

shift $((OPTIND-1))

echo "Running test queries..."
psql -v ON_ERROR_STOP=1 -h $HOST -p $PORT -U $POSTGRES_USER -d $POSTGRES_DB -a -f ./db/run_test.sql
