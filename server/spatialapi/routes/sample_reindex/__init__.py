from flask import Blueprint, request, make_response
import configparser
from http import HTTPStatus
from typing import List
import logging

from spatialapi.manager.cell_type_count_manager import CellTypeCountManager
from spatialapi.manager.sample_load_manager import SampleLoadManager
from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.utils import json_error, sample_uuid_validation

logger = logging.getLogger(__name__)

sample_reindex_blueprint = Blueprint('sample_reindex_blueprint', __name__)


def sample_rec_reindex(rec, config, bearer_token) -> None:
    try:
        sample_load_manager: SampleLoadManager = SampleLoadManager(config)
        cell_type_count_manager: CellTypeCountManager = CellTypeCountManager(config)

        # This will delete any existing sample data and also load the spatial information...
        sample_load_manager.insert_sample_data(rec)

        # Tells Ingest-api to begin processing cell_type_count data...
        sample_uuid: str = rec['sample']['uuid']
        cell_type_count_manager.begin_extract_cell_type_counts_for_sample_uuid(bearer_token, sample_uuid)
    finally:
        sample_load_manager.close()
        cell_type_count_manager.close()

@sample_reindex_blueprint.route('/samples/sample_uuid/<sample_uuid>/reindex', methods=['PUT'])
def sample_sample_uuid_reindex(sample_uuid):
    logger.info(f'sample_reindex: PUT /samples/sample_uuid/{sample_uuid}/reindex')
    sample_uuid_validation(sample_uuid)

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)

    bearer: str = request.headers.get('Authorization', None)
    if bearer is None or len(bearer.split()) != 2:
        return make_response("Authorization Bearer token not presented", HTTPStatus.UNAUTHORIZED)
    bearer_token = bearer.split()[1]
    logger.info(f"Bearer Token: {bearer_token}")

    try:
        neo4j_manager = Neo4jManager(config)

        rec: List[dict] = neo4j_manager.query_sample_uuid(sample_uuid)
        if len(rec) != 1:
            return make_response(f'Neo4j returned multiple records for sample_uuid: {sample_uuid}',
                                  HTTPStatus.FAILED_DEPENDENCY)

        sample_rec_reindex(rec[0], config, bearer_token)
    finally:
        neo4j_manager.close()

    # Because it will take time for the cell_type_counts to be processed...
    return make_response('Processing begun', HTTPStatus.ACCEPTED)


@sample_reindex_blueprint.route('/samples/organ_code/<organ_code>/reindex', methods=['PUT'])
def sample_organ_code_reindex(organ_code):
    logger.info(f'sample_reindex: PUT /samples//organ_code{organ_code}/reindex')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)

    bearer: str = request.headers.get('Authorization', None)
    if bearer is None or len(bearer.split()) != 2:
        return make_response("Authorization Bearer token not presented", HTTPStatus.UNAUTHORIZED)
    bearer_token = bearer.split()[1]
    logger.info(f"Bearer Token: {bearer_token}")

    try:
        neo4j_manager = Neo4jManager(config)

        logger.info(f"Inserting data for organ: {organ_code}")
        recs: List[dict] = neo4j_manager.query_organ(organ_code)
        logger.debug(f"Records found for organ: {len(recs)}")
        for rec in recs:
            sample_rec_reindex(rec, config, bearer_token)
    finally:
        neo4j_manager.close()

    # Because it will take time for the cell_type_counts to be processed...
    return make_response('Processing begun', HTTPStatus.ACCEPTED)
