import logging
from typing import List
from psycopg2 import DatabaseError
from psycopg2.errors import UniqueViolation, NotNullViolation

from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.manager.spatial_manager import SpatialManager

logger = logging.getLogger(__name__)


class SampleLoadManager(object):

    def __init__(self, config):
        self.neo4j_manager = Neo4jManager(config)
        self.postgresql_manager = PostgresqlManager(config)
        self.spatial_manager = SpatialManager(config)

    def close(self):
        logger.info(f'SampleLoadManager: Closing')
        self.neo4j_manager.close()
        self.postgresql_manager.close()
        self.spatial_manager.close()

    # Called from PUT '/db/rebuild/organ-sample-data' Request: {'organ_code': RK}
    def insert_organ_data(self, organ_code: str) -> None:
        logger.info(f"Inserting data for organ: {organ_code}")
        recs: List[dict] = self.neo4j_manager.query_organ(organ_code)
        logger.debug(f"Records found for organ: {len(recs)}")
        for rec in recs:
            self.insert_sample_data(rec)

    # NOTE: This does not handle cell_type_counts
    def insert_sample_data(self, rec: dict) -> None:
        # TODO: Need only one line per sample, so the geom data should be normalized.
        sql_upsert_placement_relative_to_organ_code: str =\
            self.spatial_manager.create_sample_rec_sql_upsert(rec['organ']['code'], rec)

        sql_upsert_placement_relative_to_body: str =\
            self.spatial_manager.create_sample_rec_sql_upsert_placement_relative_to_body(rec)

        try:
            cursor = self.postgresql_manager.new_cursor()

            cursor.execute(sql_upsert_placement_relative_to_organ_code)
            # NOTE: This needs to be run on prod because of interaction with Indiana code...
            cursor.execute(sql_upsert_placement_relative_to_body)

            self.postgresql_manager.commit()
            logger.info("All work committed!")
        except (Exception, DatabaseError, UniqueViolation, NotNullViolation) as e:
            self.postgresql_manager.rollback()
            logger.error(f'Exception Type causing rollback: {e.__class__.__name__}: {e}')
        finally:
            if cursor is not None:
                cursor.close()
