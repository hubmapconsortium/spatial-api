#!/bin/bash
set -e
set -u

curl -si -H 'Content-Type: application/json' -d '{"target": "VHMale", "radius": 10, "x":5, "y": 5, "z":5}' -X POST 'http://localhost:5001/spatial-search'




