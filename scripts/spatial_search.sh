#!/bin/bash
set -e
set -u

curl -si -H 'Content-Type: application/json' -d '{"target": "VHMale", "radius": '5.76456', "x":5.234, "y": 5, "z": 5}' -X POST 'http://localhost:5001/spatial-search'




