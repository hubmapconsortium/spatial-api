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
from spatialapi.manager.postgresql_manager import PostgresqlManager
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
    finally:
        if sample_load_manager is not None:
            sample_load_manager.close()
        if cell_type_count_manager is not None:
            cell_type_count_manager.close()


def process_recs_thread(recs, config, authhelper_instance: AuthHelper) -> None:
    logger.info('Thread processing samples BEGIN')
    # Because the Bearer token from the front end request may possibly timeout.
    bearer_token: str = authhelper_instance.getProcessSecret()
    for rec in recs:
        sample_uuid: str = rec['sample']['uuid']
        logger.info(f"process_recs for Sample_uuid: {sample_uuid}")
        sample_rec_reindex(rec, config, bearer_token)
    logger.info('Thread processing samples END')


def get_authhelper_instance(config) -> AuthHelper:
    """Since uwsgi workers run in different threads, we always need to check if an instance of the AuthHelper
    existe before we try to get it.
    """
    app_config = config['app']
    client_id: str = app_config.get('ClientId')
    client_secret: str = app_config.get('ClientSecret')
    if AuthHelper.isInitialized() is False:
        return AuthHelper.create(client_id, client_secret)
    return AuthHelper.instance()


def start_process_recs_thread(recs, config) -> None:
    # https://stackoverflow.com/questions/63500768/how-to-work-with-background-threads-in-flask
    # https://smirnov-am.github.io/background-jobs-with-flask/
    thread = threading.Thread(target=process_recs_thread,
                              args=[recs, config, get_authhelper_instance(config)],
                              name='Process Recs Thread')
    # Setting thread.daemon = True will allow the main program to exit.
    # Apps normally wait till all child threads are finished before completing.
    thread.daemon = True
    thread.start()
    logger.info(f"Daemon thread '{thread.name}' is started.")


@samples_reindex_blueprint.route('/samples/<sample_uuid>/reindex', methods=['PUT'])
def samples_reindex(sample_uuid):
    """ This doesn't need to be threaded because it is just reindexing one sample."""
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


def db_retrieve_sample_datasets(postgresql_manager: PostgresqlManager) -> List[dict]:
    """Return a list of dictionaries where the sample_uuid is the key,
    and the value is a dictionary of the form k:dataset_uuid, v:dataset_timestamp
    for each dataset associated with that sample.
    """
    rows: list = \
        postgresql_manager.select_all(
            "SELECT sample_dataset.sample_uuid,"
            " dataset.uuid AS dataset_uuid,"
            " dataset.last_modified_timestamp AS dataset_last_modified_timestamp"
            " FROM dataset"
            " INNER JOIN sample_dataset"
            " ON dataset.uuid = sample_dataset.dataset_uuid;"
        )
    datasets: List[dict] = []
    for row in rows:
        sample_uuid: str = row[0]
        ds_entry: dict = {row[1]: row[2]}
        ds_sample_uuid_list: list = [ds for ds in datasets if sample_uuid in ds]
        if len(ds_sample_uuid_list) == 0:
            datasets.append({sample_uuid: ds_entry})
        else:
            ds_entries: dict = ds_sample_uuid_list[0][sample_uuid]
            ds_entries.update(ds_entry)
    return datasets

@samples_reindex_blueprint.route('/samples/incremental-reindex', methods=['PUT'])
def samples_incremental_reindex():
    """Reindex only those recs which are newer in Neo4J"""
    logger.info(f'samples_incremental_reindex: PUT /samples/incremental-reindex')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)

    try:
        # TODO: Break this off into a thread because there is a lot of computation going on here...
        neo4j_manager = Neo4jManager(config)
        postgresql_manager = PostgresqlManager(config)

        sample_timestamp_list: list =\
            postgresql_manager.select_all(
                "SELECT sample_uuid, sample_last_modified_timestamp FROM sample;"
            )
        # Create a dict where the sample_uuid is the key to the sample_last_modified_timestamp value...
        sample_timestamp: dict = {row[0]: row[1] for row in sample_timestamp_list}

        db_sample_datasets: List[dict] =\
            db_retrieve_sample_datasets(postgresql_manager)

        neo4j_sample_datasets: List[dict] =\
            neo4j_manager.retrieve_datasets_that_have_rui_location_information_for_sample_uuid()

        all_recs: List[dict] = neo4j_manager.query_all()

        recs: list = []
        for rec in all_recs:
            sample_uuid: str = rec['sample']['uuid']
            sample_last_modified_timestamp: int = sample_timestamp.get(sample_uuid)
            # Reprocess the rec whose sample.last_modified_timestamp in Neo4J is greater than that in the database,
            # or if the sample does not exist in the database...
            if sample_last_modified_timestamp is None or\
                    rec['sample']['last_modified_timestamp'] > sample_last_modified_timestamp:
                recs.append(rec)
                continue
            # also process recs whose dataset.last_modified_timestamp in Neo4J is greater than that in the database
            db_sample_datasets: list = [ds for ds in db_sample_datasets if sample_uuid in ds]
            db_datasets: dict = db_sample_datasets[0].get(sample_uuid)
            neo4j_sample_datasets: list = [ds for ds in neo4j_sample_datasets if sample_uuid in ds]
            neo4j_datasets: dict = neo4j_sample_datasets[0].get(sample_uuid)
            for neo4j_ds_uuid, neo4j_ds_ts in neo4j_datasets.items():
                db_ds_ts = db_datasets.get(neo4j_ds_uuid)
                if db_ds_ts is None:
                    # neo4j dataset NEW since we last processed the sample
                    recs.append(rec)
                elif neo4j_ds_ts > db_ds_ts:
                    # neo4j dataset is NEWER since we last processed the sample
                    recs.append(rec)
        logger.debug(f"Records to be reindexed: {len(recs)}")

        start_process_recs_thread(recs, config)
    finally:
        neo4j_manager.close()
        postgresql_manager.close()

    # Because it will take time for the cell_type_counts to be processed...
    return make_response('Processing begun', HTTPStatus.ACCEPTED)


@samples_reindex_blueprint.route('/samples/reindex-all', methods=['PUT'])
def samples_reindex_all():
    """Reindex all recs found in Neo4J"""
    logger.info(f'samples_reindex_all: PUT /samples/reindex-all')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)

    try:
        neo4j_manager = Neo4jManager(config)
        recs: List[dict] = neo4j_manager.query_all()
        logger.debug(f"Records found: {len(recs)}")

        start_process_recs_thread(recs, config)
    finally:
        neo4j_manager.close()

    # Because it will take time for the cell_type_counts to be processed...
    return make_response('Processing begun', HTTPStatus.ACCEPTED)
