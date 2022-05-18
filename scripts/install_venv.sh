#!/bin/sh

cd server

VENV=./venv

usage()
{
  echo "Usage: $0 [-R] [-h]"
  echo " -R Reinstall VENV at ${VENV}"
  echo " -h Help"
  exit 2
}

while getopts 'Rh' c; do
  echo "Processing $c : OPTIND is $OPTIND"
  case $c in
    R) REINSTALL=true ;;
    h|?) usage ;;
  esac
done

shift $((OPTIND-1))

which python3
status=$?
if [[ $status != 0 ]] ; then
    echo '*** Python3 must be installed!'
    exit
fi

if [ $REINSTALL ]; then
  echo "Removing Virtual Environment located at ${VENV}"
  rm -rf ${VENV}
fi

if [[ ! -d ${VENV} ]] ; then
    echo "*** Installing python3 venv to ${VENV}"
    python3 -m pip install --upgrade pip
    python3 -m venv ${VENV}
    source ${VENV}/bin/activate
    pip install -r requirements.txt
    echo "*** Done installing python3 venv"
fi

echo "*** Using python3 venv in ${VENV}"
source ${VENV}/bin/activate
