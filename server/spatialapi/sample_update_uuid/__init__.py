from flask import Blueprint, redirect, abort, current_app, jsonify, make_response, session, g
import configparser
from spatialapi.manager.spatial_manager import SpatialManager
from typing import List
from spatialapi.utils import json_error
from http import HTTPStatus
import logging
import string

logger = logging.getLogger(__name__)

sample_update_uuid_blueprint = Blueprint('update the given sample_uuid data in the PostgreSQL database from a Neo4J query', __name__)


@sample_update_uuid_blueprint.route('/sample/update/uuid/<uuid>', methods=['PUT'])
def sample_update_uuid(uuid):
    logger.info(f'sample_update_uuid: GET /sample/update/uuid/{uuid}')
    parameter_validation(uuid)

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'sample_update_uuid: Reading properties file: {app_properties}')
    config.read(app_properties)
    spatial_manager = SpatialManager(config)

    spatial_manager.upsert_sample_uuid_data(uuid)
    return make_response("Success", HTTPStatus.OK)

def parameter_validation(uuid: str) -> None:
    if not all(c in string.hexdigits for c in uuid):
        abort(json_error(f"The sample 'uuid' ({uuid}) must contain only hex digits", HTTPStatus.BAD_REQUEST))
    if len(uuid) != 32:
        abort(json_error(f"The sample 'uuid' ({uuid}) must contain exactly 32 hex digits", HTTPStatus.BAD_REQUEST))
