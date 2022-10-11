from flask import Blueprint, abort, jsonify, make_response
import configparser
from typing import List
from spatialapi.utils import json_error
from http import HTTPStatus
import logging

from spatialapi.manager.spatial_manager import SpatialManager

logger = logging.getLogger(__name__)

search_hubmap_id_to_radius_blueprint = Blueprint('search_hubmap_id_to_radius_blueprint', __name__)


@search_hubmap_id_to_radius_blueprint.route('/search/hubmap_id/<id>/radius/<r>/target/<t>', methods=['GET'])
def search_hubmap_id_to_radius(id, r, t):
    logger.info(f'search_hubmap_id_to_radius: GET /search/hubmap_id/{id}/radius/{r}/target/{t}')
    parameter_validation(r, t)

    #replace by the correct way to check token validity.
    # authenticated = session.get('is_authenticated')
    # if not authenticated:
    #     #return redirect(url_for('login.login'))
    #     redirect_url = current_app.config['FLASK_APP_BASE_URI'].rstrip('/') + '/login'
    #     return redirect(redirect_url)
    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'search_hubmap_id_to_radius: Reading properties file: {app_properties}')
    config.read(app_properties)
    spatial_manager = SpatialManager(config)

    results: List[str] = spatial_manager.find_within_radius_at_sample_hubmap_id_and_target(r, id, t)
    logger.info(f'search_hubmap_id_to_radius; find_within_radius_at_hubmap_id({id},{r}, {t}): {results}')
    response = make_response(jsonify(hubmap_ids=results), 200)
    response.headers["Content-Type"] = "application/json"
    return response

def parameter_validation(radius, target: str) -> None:
    target_values: list = ['VHMale', 'VHFemale']
    if not target in target_values:
        abort(json_error(f"The 'target' must be one of: {', '.join(target_values)}", HTTPStatus.BAD_REQUEST))
    try:
        float(radius)
    except ValueError:
        abort(json_error(f"The 'radius' must have a numeric value of either 'int' or 'float'", HTTPStatus.BAD_REQUEST))
