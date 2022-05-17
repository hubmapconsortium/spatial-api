from flask import Blueprint, request, abort, redirect, current_app, jsonify, make_response, session, g
import configparser
from spatialapi.manager.spatial_manager import SpatialManager
from spatialapi.utils import json_error
import logging

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
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

    results = spatial_manager.find_relative_to_spatial_entry_iri_within_radius_from_hubmap_id(
        request_dict['target'],
        request_dict['radius'],
        request_dict['hubmap_id']
    )

    response = make_response(jsonify(hubmap_ids=results), 200)
    response.headers["Content-Type"] = "application/json"
    return response

def request_validation(request_dict: dict) -> None:
    int_instances_keys: tuple = ("radius", )
    required_request_keys: tuple = int_instances_keys + ("target", "hubmap_id", )
    target_values: list = ['VHMale', 'VHFemale']
    if not all(key in request_dict for key in required_request_keys):
        abort(json_error(f'Request Body: must have the following required attributes {required_request_keys}', 400))
    if not all(isinstance(value, (int, float)) for value in [request_dict[k] for k in int_instances_keys]):
        abort(json_error(f'Request Body: the following attributes {int_instances_keys} must have numeric values', 400))
    if not request_dict['target'] in target_values:
        abort(json_error(f'Request Body: the attribute "target" must be one of: {", ".join(target_values)}', 400))
