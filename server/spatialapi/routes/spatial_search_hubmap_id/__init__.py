from flask import Blueprint, request, abort, jsonify, make_response
import configparser
from http import HTTPStatus
import logging

from spatialapi.manager.spatial_manager import SpatialManager
from spatialapi.utils import json_error

logger = logging.getLogger(__name__)

spatial_search_hubmap_id_blueprint = Blueprint('spatial_search_hubmap_id_blueprint', __name__)


@spatial_search_hubmap_id_blueprint.route('/spatial-search/hubmap_id', methods=['POST'])
def spatial_search_hubmap_id():
    request_dict: dict = request.get_json()
    logger.info(f'spatial_search: POST /spatial-search/hubmap_id {request_dict}')
    request_validation(request_dict)

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'spatial_search: Reading properties file: {app_properties}')
    config.read(app_properties)
    spatial_manager = SpatialManager(config)

    cell_type_name: str = None
    if 'cell_type' in request_dict:
        cell_type_name = request_dict['cell_type']

    results = spatial_manager.find_relative_to_spatial_entry_iri_within_radius_from_hubmap_id(
        request_dict['target'],
        request_dict['radius'],
        request_dict['hubmap_id'],
        cell_type_name
    )

    response = make_response(jsonify(hubmap_ids=results), HTTPStatus.OK)
    response.headers["Content-Type"] = "application/json"
    return response

def request_validation(request_dict: dict) -> None:
    int_instances_keys: tuple = ("radius", )
    required_request_keys: tuple = int_instances_keys + ("target", "hubmap_id")
    optional_request_keys: tuple = ("cell_type", )
    all_request_keys: tuple = required_request_keys + optional_request_keys
    for k in request_dict.keys():
        if k not in all_request_keys:
            abort(json_error(f"Request Body: can only have the following attributes {all_request_keys}",
                             HTTPStatus.BAD_REQUEST))
    if not all(key in request_dict for key in required_request_keys):
        abort(json_error(f"Request Body: must have the following required attributes {required_request_keys}", HTTPStatus.BAD_REQUEST))
    if not all(isinstance(value, (int, float)) for value in [request_dict[k] for k in int_instances_keys]):
        abort(json_error(f"Request Body: the following attributes {int_instances_keys} must have numeric values", HTTPStatus.BAD_REQUEST))
    target_values: list = ['VHMale', 'VHFemale']
    if not request_dict['target'] in target_values:
        abort(json_error(f"Request Body: the attribute 'target' must be one of: {', '.join(target_values)}", HTTPStatus.BAD_REQUEST))
