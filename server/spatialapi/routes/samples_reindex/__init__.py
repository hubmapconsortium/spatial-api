from flask import Blueprint, request, make_response
import configparser
from http import HTTPStatus
from typing import List
import threading
import logging

from hubmap_commons.hm_auth import AuthHelper

from spatialapi.manager.cell_type_count_manager import CellTypeCountManager
from spatialapi.manager.sample_load_manager import SampleLoadManager
from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.utils import json_error, sample_uuid_validation

logger = logging.getLogger(__name__)

samples_reindex_blueprint = Blueprint('samples_reindex_blueprint', __name__)


def sample_rec_reindex(rec, config, bearer_token: str) -> None:
    sample_load_manager: SampleLoadManager = None
    cell_type_count_manager: CellTypeCountManager = None
    try:
        sample_load_manager = SampleLoadManager(config)
        cell_type_count_manager = CellTypeCountManager(config)

        # This will delete any existing sample data and also load the spatial information...
        sample_load_manager.insert_sample_data(rec)

        # Tells Ingest-api to begin processing cell_type_count data...
        sample_uuid: str = rec['sample']['uuid']
        cell_type_count_manager.begin_extract_cell_type_counts_for_sample_uuid(bearer_token, sample_uuid)
    except Exception as e:
        logger.error(f'sample_rec_reindex Exception: {e}')
    finally:
        if sample_load_manager is not None:
            sample_load_manager.close()
        if cell_type_count_manager is not None:
            cell_type_count_manager.close()


def process_recs_thread(recs, config) -> None:
    logger.info('Thread processing samples BEGIN')
    auth_helper_instance = AuthHelper.instance()
    # Because the Bearer token from the front end request may possibly timeout.
    bearer_token: str = auth_helper_instance.getProcessSecret()
    for rec in recs:
        sample_uuid: str = rec['sample']['uuid']
        logger.info(f"process_recs for Sample_uuid: {sample_uuid}")
        sample_rec_reindex(rec, config, bearer_token)
    logger.info('Thread processing samples END')


def start_process_recs_thread(recs, config) -> None:
    # https://stackoverflow.com/questions/63500768/how-to-work-with-background-threads-in-flask
    # https://smirnov-am.github.io/background-jobs-with-flask/
    thread = threading.Thread(target=process_recs_thread,
                              args=[recs, config],
                              name='process sample recs')
    # Setting thread.daemon = True will allow the main program to exit.
    # Apps normally wait till all child threads are finished before completing.
    thread.daemon = True
    thread.start()
    logger.info(f"Daemon thread '{thread.name}' is started.")


@samples_reindex_blueprint.route('/samples/<sample_uuid>/reindex', methods=['PUT'])
def samples_reindex(sample_uuid):
    """ This doesn't need to be threaded because it is just doing one sample.
    """
    logger.info(f'samples_reindex: PUT /samples/{sample_uuid}/reindex')
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


@samples_reindex_blueprint.route('/samples/organs/<organ_code>/reindex', methods=['PUT'])
def samples_organs_reindex(organ_code):
    logger.info(f'samples_organs_reindex: PUT /samples/organs/{organ_code}/reindex')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)

    # bearer: str = request.headers.get('Authorization', None)
    # if bearer is None or len(bearer.split()) != 2:
    #     return make_response("Authorization Bearer token not presented", HTTPStatus.UNAUTHORIZED)
    # bearer_token = bearer.split()[1]
    # logger.info(f"Bearer Token: {bearer_token}")

    try:
        neo4j_manager = Neo4jManager(config)
        recs: List[dict] = neo4j_manager.query_organ(organ_code)
        logger.debug(f"Records found: {len(recs)}")

        start_process_recs_thread(recs, config)
    finally:
        neo4j_manager.close()

    # Because it will take time for the cell_type_counts to be processed...
    return make_response('Processing begun', HTTPStatus.ACCEPTED)


@samples_reindex_blueprint.route('/samples/reindex-all', methods=['PUT'])
def samples_reindex_all():
    logger.info(f'samples_reindex_all: PUT /samples/reindex-all')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)

    # bearer: str = request.headers.get('Authorization', None)
    # if bearer is None or len(bearer.split()) != 2:
    #     return make_response("Authorization Bearer token not presented", HTTPStatus.UNAUTHORIZED)
    # bearer_token = bearer.split()[1]
    # logger.info(f"Bearer Token: {bearer_token}")

    try:
        neo4j_manager = Neo4jManager(config)
        recs: List[dict] = neo4j_manager.query_all()
        logger.debug(f"Records found: {len(recs)}")

        start_process_recs_thread(recs, config)
    finally:
        neo4j_manager.close()

    # Because it will take time for the cell_type_counts to be processed...
    return make_response('Processing begun', HTTPStatus.ACCEPTED)
