from flask import Blueprint, make_response, request, abort
import configparser
import logging
from http import HTTPStatus

from spatialapi.manager.cell_annotation_manager import CellAnnotationManager
from spatialapi.manager.sample_load_manager import SampleLoadManager
from spatialapi.utils import json_error

logger = logging.getLogger(__name__)

db_rebuild_blueprint = Blueprint('endpoints for rebuilding the database', __name__)


@db_rebuild_blueprint.route('/db/rebuild/annotation-details', methods=['PUT'])
def db_rebuild_annotation_details():
    logger.info(f'db_rebuild_annotation_details: PUT /db/rebuild/annotation-details')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)

    cell_annotation_manager: CellAnnotationManager = CellAnnotationManager(config)

    cell_annotation_manager.load_annotation_details()

    return make_response("Done", 200)


# https://realpython.com/token-based-authentication-with-flask/
@db_rebuild_blueprint.route('/db/rebuild/organ-sample-data', methods=['PUT'])
def db_rebuild_organ_sample_data():
    request_dict: dict = request.get_json()
    logger.info(f'db_rebuild_organ_sample_data: PUT /db/rebuild/organ-sample-data {request_dict}')
    if 'organ_code' not in request_dict:
        abort(json_error("Request Body: the attribute 'organ_code' must be included in request parameters",
                         HTTPStatus.BAD_REQUEST))

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)

    sample_load_manager: SampleLoadManager = SampleLoadManager(config)

    sample_load_manager.insert_organ_data(request_dict['organ_code'])

    return make_response("Done", 200)
