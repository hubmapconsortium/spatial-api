from flask import Blueprint, request, abort, jsonify, make_response
import configparser
from http import HTTPStatus
import logging

from spatialapi.manager.spatial_manager import SpatialManager
from spatialapi.utils import json_error

logger = logging.getLogger(__name__)

point_search_blueprint = Blueprint('point_search_blueprint', __name__)


@point_search_blueprint.route('/point-search', methods=['POST'])
def point_search():
    request_dict: dict = request.get_json()
    logger.info(f'point_search: POST /point-search {request_dict}')
    request_validation(request_dict)

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'point_search: Reading properties file: {app_properties}')
    config.read(app_properties)
    spatial_manager = SpatialManager(config)

    results = spatial_manager.find_relative_to_spatial_entry_iri_within_radius_from_point(
        request_dict['target'],
        request_dict['radius'],
        request_dict['x'], request_dict['y'], request_dict['z'])

    response = make_response(jsonify(hubmap_ids=results), HTTPStatus.OK)
    response.headers["Content-Type"] = "application/json"
    return response


def request_validation(request_dict: dict) -> None:
    numeric_instances_keys: tuple = ('radius', 'x', 'y', 'z')
    required_request_keys: tuple = numeric_instances_keys + ('target',)
    target_values: list = ['VHMale', 'VHFemale']
    if not all(key in request_dict for key in required_request_keys):
        abort(json_error(f"Request Body: must have the following required attributes {required_request_keys}", HTTPStatus.BAD_REQUEST))
    if not all(isinstance(value, (int, float)) for value in [request_dict[k] for k in numeric_instances_keys]):
        abort(json_error(f"Request Body: these attributes must have numeric values (int or float): {numeric_instances_keys}", HTTPStatus.BAD_REQUEST))
    if not request_dict['target'] in target_values:
        abort(json_error(f"Request Body: the attribute 'target' must be one of: {', '.join(target_values)}", HTTPStatus.BAD_REQUEST))
