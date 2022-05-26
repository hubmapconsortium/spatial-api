#!/bin/sh

VENV=./venv

rm -rf ${VENV}
python3 -m venv ${VENV}
source ${VENV}/bin/activate
pip install -r requirements.txt

echo "*** Using python3 venv in ${VENV}"
