import logging
from datetime import datetime, timedelta
from typing import List
import threading
import time
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
                    logger.error('Ingest-api cell_type_count request for sample_uuid '
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


# Austin Hartman Novemer 8, 2022 10:41 AM
# The ‘annotation details’ marker tables can be found within the azimuth website repo here:
# https://github.com/satijalab/azimuth_website/tree/master/static/csv. However, the annotations
# listed may not (actually usually don’t) line up with ASCT+B cell types as you point out.
# So for the kidney, the azimuth website lists the original annotations at 3 levels of resolution
# and the secondary_analysis.h5ad files contain ASCT+B annotations which are mapped from the level 3
# annotations using this table:
# https://github.com/hubmapconsortium/azimuth-annotate/blob/main/data/kidney.json
# where keys represent the level 3 annotations (kidney_l3.csv) and values are ASCT+B names
def load_cell_type_mapping() -> dict:
    from urllib.request import urlopen
    import json
    from bs4 import BeautifulSoup
    url_str: str = "https://raw.githubusercontent.com/hubmapconsortium/azimuth-annotate/main/data/kidney.json"
    mapping: dict = {}
    url = urlopen(url_str)
    content = url.read()
    soup = BeautifulSoup(content, "html.parser")
    content_json = json.loads(str(soup))
    content_mapping = content_json['mapping']
    for k, v in content_mapping.items():
        # it is reversed from what we need...
        mapping[v] = k
    # logger.debug(f'Loaded cell_type_mapping: {mapping}')
    return mapping


class CellTypeCountManager(object):

    def __init__(self, config):
        self.ingest_api_manager = IngestApiManager(config)
        self.neo4j_manager = Neo4jManager(config)
        self.postgresql_manager = PostgresqlManager(config)

        celltypecount_config = config['celltypecount']

        # cell_type_name_mapping_file_name: str = celltypecount_config.get('CellTypeNameMappingFile')
        # logger.debug(f"Reading json from '{cell_type_name_mapping_file_name}'")
        # cell_type_name_mapping_file_fp = open(cell_type_name_mapping_file_name, "r")
        # self.cell_type_name_mapping = json.load(cell_type_name_mapping_file_fp)
        # cell_type_name_mapping_file_fp.close()
        self.cell_type_name_mapping = load_cell_type_mapping()

        unknown_cell_type_name_file: str = celltypecount_config.get('UnknownFile')
        logger.debug(f"Opening for append '{unknown_cell_type_name_file}'")
        self.unknown_cell_type_name_fp = open(unknown_cell_type_name_file, "a")

    def close(self):
        logger.info(f'CellTypeCountManager: Closing')
        self.ingest_api_manager.close()
        self.neo4j_manager.close()
        self.postgresql_manager.close()
        self.unknown_cell_type_name_fp.close()

    def save_unknown_cell_type_name(self, cell_type_name) -> None:
        self.unknown_cell_type_name_fp.writelines(f'{cell_type_name}\n')

    def map_cell_type_name(self, cell_type_name):
        if cell_type_name in self.cell_type_name_mapping:
            return self.cell_type_name_mapping[cell_type_name]
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
        neo4j_sample_datasets: dict =\
            self.neo4j_manager.retrieve_datasets_that_have_rui_location_information_for_sample_uuid(sample_uuid)
        # Ingest will determine which files to process for the datasets in a thread which posts the data back
        # on another call. The 'cell_type_counts' from that is used in 'finish_update_sample_uuid' below.
        if len(neo4j_sample_datasets) == 0:
            logger.info('begin_extract_cell_type_counts_for_sample_uuid: '
                        f'sample_uuid:{sample_uuid} has no datasets with rui location information')
            return
        datasets: dict = neo4j_sample_datasets.get(sample_uuid)
        self.ingest_api_manager.begin_extract_cell_count_from_secondary_analysis_files(
            bearer_token, sample_uuid, list(datasets.keys())
        )
        try:
            cursor = self.postgresql_manager.new_cursor()
            for ds_uuid, ds_ts in datasets.items():
                logger.info(f'begin_extract_cell_type_counts_for_sample_uuid:'
                            f' inserting into dataset and sample_dataset tables; ds_uuid: {ds_uuid} & ds_ts: {ds_ts}')
                if ds_ts is None:
                    logger.info("begin_extract_cell_type_counts_for_sample_uuid;"
                                f" invalid timestamp in datasets: {datasets}")
                    continue
                cursor.execute("INSERT INTO dataset (uuid, last_modified_timestamp) VALUES(%s, %s) "
                               "ON CONFLICT (uuid) DO UPDATE "
                               "SET last_modified_timestamp = EXCLUDED.last_modified_timestamp;",
                               (ds_uuid, ds_ts,))
                cursor.execute("INSERT INTO sample_dataset (sample_uuid, dataset_uuid) VALUES(%s, %s) "
                               "ON CONFLICT (sample_dataset_pkey) DO NOTHING;",
                               (sample_uuid, ds_uuid,))
            self.postgresql_manager.commit()
        except (Exception, DatabaseError, UniqueViolation) as e:
            self.postgresql_manager.rollback()
            logger.error('begin_extract_cell_type_counts_for_sample_uuid:'
                         f' Exception Type causing rollback: {e.__class__.__name__}: {e}')
        finally:
            if cursor is not None:
                cursor.close()
        request_log_add(sample_uuid)

    # https://www.oracletutorial.com/python-oracle/transactions/
    def sample_extracted_cell_type_counts_from_secondary_analysis_files(self,
                                                                        sample_uuid: str,
                                                                        cell_type_counts: dict) -> None:
        logger.info('sample_extracted_cell_type_counts_from_secondary_analysis_files; '
                    f'sample_uuid: {sample_uuid} cell_type_counts: {cell_type_counts}')
        verified_cell_type: dict = {}
        try:
            cursor = self.postgresql_manager.new_cursor()
            if cell_type_counts is not None:
                for cell_type_name, cell_type_count in cell_type_counts.items():
                    if cell_type_name not in self.cell_type_name_mapping:
                        cursor.execute("SELECT * FROM cell_annotation_details WHERE cell_type_name = %(cell_type_name)s",
                                       {'cell_type_name': cell_type_name})
                        if cursor.fetchone() is None:
                            logger.error(f"cell_type_name '{cell_type_name}'"
                                         " not found in 'cell_annotation_details' table")
                            self.save_unknown_cell_type_name(cell_type_name)
                        else:
                            verified_cell_type[cell_type_name] = cell_type_count
                    else:
                        verified_cell_type[cell_type_name] = cell_type_count
        finally:
            if cursor is not None:
                cursor.close()

        try:
            cursor = self.postgresql_manager.new_cursor()

            cursor.execute("DELETE FROM cell_types WHERE sample_uuid = %(sample_uuid)s",
                           {'sample_uuid': sample_uuid})

            if verified_cell_type is not None:
                for cell_type_name, cell_type_count in verified_cell_type.items():
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


if __name__ == '__main__':
    load_cell_type_mapping()
