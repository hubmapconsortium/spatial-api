#!/bin/sh

# https://ccf-api--staging.herokuapp.com/#/operations/get-spatial-placement
# --url https://ccf-api--staging.herokuapp.com/v1/get-spatial-placement \
# -- url https://ccf-api.hubmapconsortium.org/v1/get-spatial-placement \

curl --verbose --request POST \
  --url https://ccf-api.hubmapconsortium.org/v1/get-spatial-placement \
  --header 'Content-Type: application/json' \
  --data '{
  "target_iri": "http://purl.org/ccf/latest/ccf.owl#VHMale",
  "rui_location": {
	"@context": "https://hubmapconsortium.github.io/hubmap-ontology/ccf-context.jsonld",
	"@id": "http://purl.org/ccf/0.5/c62cd431-dd48-4c1b-9c7b-ca4a683fe084",
	"@type": "SpatialEntity",
	"label": "SpatialEntity for Male, Age 21, BMI 21.8",
	"creator": "Jeff Spraggins",
	"creator_first_name": "Jeff",
	"creator_last_name": "Spraggins",
	"creation_date": "2/12/2020 9:48:13 AM",
	"ccf_annotations": [],
	"x_dimension": 23,
	"y_dimension": 18,
	"z_dimension": 5,
	"dimension_units": "millimeter",
	"placement": {
		"@context": "https://hubmapconsortium.github.io/hubmap-ontology/ccf-context.jsonld",
		"@id": "http://purl.org/ccf/0.5/c62cd431-dd48-4c1b-9c7b-ca4a683fe084_placement",
		"@type": "SpatialPlacement",
		"target": "http://purl.org/ccf/latest/ccf.owl#VHMRightKidney_Patch",
		"placement_date": "2/12/2020 9:48:13 AM",
		"x_scaling": 1,
		"y_scaling": 1,
		"z_scaling": 1,
		"scaling_units": "ratio",
		"x_rotation": 0,
		"y_rotation": 0,
		"z_rotation": 247.9199981689453,
		"rotation_order": "XYZ",
		"rotation_units": "degree",
		"x_translation": -2.729999542236328,
		"y_translation": 33.220001220703125,
		"z_translation": -8.940000534057617,
		"translation_units": "millimeter"
	}
 }
}'
echo
