from flask import Blueprint, make_response, request, abort
import configparser
import logging

from spatialapi.manager.cell_annotation_manager import CellAnnotationManager

logger = logging.getLogger(__name__)

db_rebuild_annotation_details_blueprint = Blueprint('endpoints for rebuilding the database', __name__)


@db_rebuild_annotation_details_blueprint.route('/db/rebuild/annotation-details', methods=['PUT'])
def db_rebuild_annotation_details():
    logger.info(f'db_rebuild_annotation_details: PUT /db/rebuild/annotation-details')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)

    cell_annotation_manager: CellAnnotationManager = CellAnnotationManager(config)

    cell_annotation_manager.load_annotation_details()

    return make_response("Done", 200)
