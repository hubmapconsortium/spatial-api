from flask import Blueprint, request, abort, redirect, current_app, jsonify, make_response, session, g
import configparser
from spatialapi.manager.spatial_manager import SpatialManager
from spatialapi.utils import json_error
import logging

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

spatial_search_point_blueprint = Blueprint('spatial_search_point_blueprint', __name__)


@spatial_search_point_blueprint.route('/spatial-search/point', methods=['POST'])
def spatial_search_point():
    request_dict: dict = request.get_json()
    logger.info(f'spatial_search: POST /spatial-search/point {request_dict}')
    request_validation(request_dict)

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'spatial_search: Reading properties file: {app_properties}')
    config.read(app_properties)
    spatial_manager = SpatialManager(config)

    results = spatial_manager.find_relative_to_spatial_entry_iri_within_radius_from_point(
        request_dict['target'],
        request_dict['radius'],
        request_dict['x'], request_dict['y'], request_dict['z'])

    response = make_response(jsonify(hubmap_ids=results), 200)
    response.headers["Content-Type"] = "application/json"
    return response

def request_validation(request_dict: dict) -> None:
    numeric_instances_keys: tuple = ("radius", 'x', 'y', 'z')
    required_request_keys: tuple = numeric_instances_keys + ("target",)
    target_values: list = ['VHMale', 'VHFemale']
    if not all(key in request_dict for key in required_request_keys):
        abort(json_error(f'Request Body: must have the following required attributes {required_request_keys}', 400))
    if not all(isinstance(value, (int, float)) for value in [request_dict[k] for k in numeric_instances_keys]):
        abort(json_error(f'Request Body: these attributes must have numeric values (int or float): {numeric_instances_keys}', 400))
    if not request_dict['target'] in target_values:
        abort(json_error(f'Request Body: the attribute "target" must be one of: {", ".join(target_values)}', 400))
