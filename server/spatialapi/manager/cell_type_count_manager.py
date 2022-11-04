import logging
from datetime import datetime, timedelta
from typing import List
import threading
import time
import json
from psycopg2 import DatabaseError
from psycopg2.errors import UniqueViolation, NotNullViolation

from spatialapi.manager.ingest_api_manager import IngestApiManager
from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager

logger = logging.getLogger(__name__)

cell_type_count_manager_request_log: List[dict] = []
lock = threading.Lock()
REQUEST_TIMEOUT_HOURS = 2


def request_log_add(sample_uuid: str) -> None:
    lock.acquire()
    try:
        cell_type_count_manager_request_log.append({'sample_uuid': sample_uuid, 'request_time': datetime.now()})
    finally:
        lock.release()


def request_log_delete(sample_uuid: str) -> datetime:
    request_time = None
    lock.acquire()
    try:
        for sample_log_entry in cell_type_count_manager_request_log.copy():
            if sample_log_entry.get('sample_uuid') == sample_uuid:
                cell_type_count_manager_request_log.remove(sample_log_entry)
                request_time = sample_log_entry.get('request_time')
    finally:
        lock.release()
    return request_time


def request_log_length() -> int:
    lock.acquire()
    try:
        log_len: int = len(cell_type_count_manager_request_log)
    finally:
        lock.release()
    return log_len


def log_check_timeouts_thread(lock, cell_type_count_manager_request_log) -> None:
    while True:
        logger.info(f'cell_type_count_manager_request_log length: {request_log_length()}')
        time.sleep(60*5)
        lock.acquire()
        try:
            for sample_log_entry in cell_type_count_manager_request_log.copy():
                if sample_log_entry.get('request_time') + timedelta(hours=REQUEST_TIMEOUT_HOURS) > datetime.now():
                    logger.error('*** Ingest-api cell_type_count request for sample_uuid '
                                 f'{sample_log_entry.get("sample_uuid")} has not returned data in '
                                 f'{REQUEST_TIMEOUT_HOURS} hours')
                    cell_type_count_manager_request_log.remove(sample_log_entry)
        finally:
            lock.release()


threading.Thread(target=log_check_timeouts_thread,
                 args=[lock, cell_type_count_manager_request_log],
                 name='Thread to check for timeouts')\
    .start()
# This thread will run forever, so we don't need a handle on it to .join()


class CellTypeCountManager(object):

    def __init__(self, config):
        self.ingest_api_manager = IngestApiManager(config)
        self.neo4j_manager = Neo4jManager(config)
        self.postgresql_manager = PostgresqlManager(config)

        celltypecount_config = config['celltypecount']
        unknown_cell_type_name_file: str = celltypecount_config.get('UnknownFile')
        self.unknown_cell_type_name_fp = open(unknown_cell_type_name_file, "a")
        cell_type_name_mapping_file_name: str = celltypecount_config.get('CellTypeNameMappingFile')
        cell_type_name_mapping_file_fp = open(cell_type_name_mapping_file_name, "r")
        self.cell_type_name_mappings = json.load(cell_type_name_mapping_file_fp)
        cell_type_name_mapping_file_fp.close()

    def close(self):
        logger.info(f'CellTypeCountManager: Closing')
        self.ingest_api_manager.close()
        self.neo4j_manager.close()
        self.postgresql_manager.close()
        self.unknown_cell_type_name_fp.close()

    def save_unknown_cell_type_name(self, cell_type_name) -> None:
        self.unknown_cell_type_name_fp.writelines(f'{cell_type_name}\n')

    def map_cell_type_name(self, cell_type_name):
        if cell_type_name in self.cell_type_name_mappings:
            return self.cell_type_name_mappings[cell_type_name]
        return cell_type_name

    def begin_extract_cell_type_counts_for_all_samples_for_organ_code(self,
                                                                      bearer_taken: str,
                                                                      organ_code: str) -> None:
        recs: List[dict] = self.neo4j_manager.query_organ(organ_code)
        logger.debug(f"Records found for organ: {len(recs)}")
        for rec in recs:
            sample_uuid: str = rec['sample']['uuid']
            self.begin_extract_cell_type_counts_for_sample_uuid(bearer_taken, sample_uuid)

    # This is called to initiate the cell_type_counts extraction through ingest-api on the PSC machine
    # on which the files live.
    def begin_extract_cell_type_counts_for_sample_uuid(self,
                                                       bearer_token: str,
                                                       sample_uuid: str) -> None:
        ds_uuids: List[str] =\
            self.neo4j_manager.retrieve_ds_uuids_that_have_rui_location_information_for_sample_uuid(sample_uuid)
        # Ingest will determine which files to process for the data sets in a thread which posts the data back
        # on another call. The 'cell_type_counts' from that is used in 'finish_update_sample_uuid' below.
        if len(ds_uuids) == 0:
            logger.info(f'*** begin_extract_cell_type_counts_for_sample_uuid: sample_uuid:{sample_uuid} has no dataset uuids that have rui location information')
        self.ingest_api_manager.begin_extract_cell_count_from_secondary_analysis_files(
            bearer_token, sample_uuid, ds_uuids
        )
        request_log_add(sample_uuid)

    # https://www.oracletutorial.com/python-oracle/transactions/
    def sample_extracted_cell_type_counts_from_secondary_analysis_files(self,
                                                                        sample_uuid: str,
                                                                        cell_type_counts: dict) -> None:
        logger.info('sample_extracted_cell_type_counts_from_secondary_analysis_files; '
                    f'sample_uuid: {sample_uuid} cell_type_counts: {cell_type_counts}')
        try:
            cursor = self.postgresql_manager.new_cursor()
            if cell_type_counts is not None:
                for cell_type_name, cell_type_count in cell_type_counts.items():
                    cursor.execute("SELECT * FROM cell_annotation_details WHERE cell_type_name = %(cell_type_name)",
                                   {'cell_type_name': cell_type_name})
                    if cursor.fetchone() is None:
                        logger.error(f"cell_type_name '{cell_type_name}' not found in 'cell_annotation_details' table")
                        self.save_unknown_cell_type_name(cell_type_name)
        finally:
            if cursor is not None:
                cursor.close()

        try:
            cursor = self.postgresql_manager.new_cursor()

            cursor.execute("DELETE FROM cell_types WHERE sample_uuid = %(sample_uuid)s",
                           {'sample_uuid': sample_uuid})

            if cell_type_counts is not None:
                for cell_type_name, cell_type_count in cell_type_counts.items():
                    cursor.execute('CALL add_cell_type_count_sp(%s, %s, %s)',
                                   (sample_uuid, self.map_cell_type_name(cell_type_name), cell_type_count))

            self.postgresql_manager.commit()
            logger.info("finish_update_sample_uuid committed!")
        except (Exception, DatabaseError, UniqueViolation, NotNullViolation) as e:
            self.postgresql_manager.rollback()
            logger.error(f'Exception Type causing rollback: {e.__class__.__name__}: {e}')
        finally:
            if cursor is not None:
                cursor.close()
        request_log_delete(sample_uuid)
