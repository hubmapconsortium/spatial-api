from flask import Blueprint, request, abort, redirect, current_app, jsonify, make_response, session, g
import configparser
from spatialapi.manager.spatial_manager import SpatialManager
from spatialapi.utils import json_error
import logging

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

spatial_search_blueprint = Blueprint('spatial_search_blueprint', __name__)


@spatial_search_blueprint.route('/spatial-search', methods=['POST'])
def spatial_search():
    request_dict: dict = request.get_json()
    logger.info(f'spatial_search: POST /spatial-search {request_dict}')
    required_request_keys: tuple = ("target", "radius", 'x', 'y', 'z')
    if not all(key in request_dict for key in required_request_keys):
        abort(json_error(f'Request Body must have the following required attributes {required_request_keys}', 400))

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'spatial_search: Reading properties file: {app_properties}')
    config.read(app_properties)
    spatial_manager = SpatialManager(config)
    
    results = {}
    response = make_response(jsonify(hubmap_ids=results), 200)
    response.headers["Content-Type"] = "application/json"
    return response
