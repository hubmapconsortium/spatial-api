from flask import Blueprint, request, abort, Response
import configparser
from http import HTTPStatus
import logging
import string

from spatialapi.manager.cell_type_count_manager import CellTypeCountManager
from spatialapi.utils import json_error

logger = logging.getLogger(__name__)

sample_extract_cell_type_count_blueprint =\
    Blueprint('sample extract cell_type_count data', __name__)

sample_extracted_cell_count_blueprint =\
    Blueprint('finish updating the sample_uuid cell_type_count data with data from Ingest-Api', __name__)


@sample_extract_cell_type_count_blueprint.route(
    '/sample/begin-extract-cell-type-counts-for-all-samples-for-organ-code',
    methods=['PUT'])
def begin_extract_cell_type_counts_for_all_samples_for_organ_code():
    request_dict: dict = request.get_json()
    logger.info(f' PUT sample/begin-extract-cell-type-counts-for-all-samples-for-organ-code {request_dict}')
    if 'organ_code' not in request_dict:
        abort(json_error("Request Body: the attribute 'organ_code' must be included in request parameters",
                         HTTPStatus.BAD_REQUEST))

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'sample_update_uuid: Reading properties file: {app_properties}')
    config.read(app_properties)

    cell_type_count_manager: CellTypeCountManager = CellTypeCountManager(config)

    bearer: str = request.headers.get('Authorization', None)
    if bearer is None or len(bearer.split()) != 2:
        return Response("Authorization Bearer token not presented", HTTPStatus.UNAUTHORIZED)
    bearer_token = bearer.split()[1]
    logger.info(f"Bearer Token: {bearer_token}")

    cell_type_count_manager.begin_extract_cell_type_counts_for_all_samples_for_organ_code(bearer_token,
                                                                                          request_dict['organ_code'])
    return Response("Processing has been initiated", HTTPStatus.ACCEPTED)


# https://realpython.com/token-based-authentication-with-flask/
@sample_extract_cell_type_count_blueprint.route(
    '/sample/begin-extract-cell-type-counts-for/sample-uuid/<sample_uuid>',
    methods=['PUT'])
def begin_extract_all_cell_type_counts_for_sample_uuid(sample_uuid: str):
    logger.info(f' PUT /sample/begin-extract-cell-type-counts-for/sample-uuid/{sample_uuid}')
    parameter_validation(sample_uuid)

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'sample_update_uuid: Reading properties file: {app_properties}')
    config.read(app_properties)

    cell_type_count_manager = CellTypeCountManager(config)

    bearer: str = request.headers.get('Authorization', None)
    if bearer is None or len(bearer.split()) != 2:
        return Response("Authorization Bearer token not presented", HTTPStatus.UNAUTHORIZED)
    bearer_token = bearer.split()[1]
    logger.info(f"Bearer Token: {bearer_token}")
    
    # Tells Ingest-api to return the 'cell_type_counts' to the endpoint below...
    cell_type_count_manager.begin_extract_cell_type_counts_for_sample_uuid(bearer_token, sample_uuid)

    return Response("Processing has been initiated", HTTPStatus.ACCEPTED)


# Ingest-api will call this when it has computed the 'cell_type_counts' from the initiation above
@sample_extracted_cell_count_blueprint.route(
    '/sample/extracted-cell-type-counts-from-secondary-analysis-files',
    methods=['PUT'])
def sample_extracted_cell_type_counts_from_secondary_analysis_files():
    logger.info(f'finish_sample_update_uuid: PUT /sample/extracted-cell-count-from-secondary-analysis-files')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'sample_extracted_cell_count_from_secondary_analysis_files: Reading properties file: {app_properties}')
    config.read(app_properties)

    cell_type_count_manager = CellTypeCountManager(config)

    sample_uuid: str = request.json['sample_uuid']
    cell_type_counts: dict = request.json['cell_type_counts']

    cell_type_count_manager.sample_extracted_cell_type_counts_from_secondary_analysis_files(sample_uuid, cell_type_counts)

    return Response("Processing has been initiated", HTTPStatus.ACCEPTED)


def parameter_validation(uuid: str) -> None:
    if not all(c in string.hexdigits for c in uuid):
        abort(json_error(f"The 'sample-uuid' ({uuid}) must contain only hex digits", HTTPStatus.BAD_REQUEST))
    if len(uuid) != 32:
        abort(json_error(f"The 'sample-uuid' ({uuid}) must contain exactly 32 hex digits", HTTPStatus.BAD_REQUEST))
