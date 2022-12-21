import logging
from psycopg2 import DatabaseError
from psycopg2.errors import UniqueViolation, NotNullViolation

from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.manager.spatial_manager import SpatialManager
from spatialapi.manager.spatial_placement_manager import SpatialPlacementException

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

    # NOTE: This does not handle cell_type_counts
    def insert_sample_data(self, rec: dict) -> None:
        try:
            cursor = self.postgresql_manager.new_cursor()
            sample_uuid: str = rec['sample']['uuid']

            # This also deletes the rows in 'cell_types' that contain 'sample_uuid' because
            # of the REFERENCES sample (sample_uuid) ON DELETE CASCADE
            delete_existing_cell_type_data: str =\
                f"DELETE FROM cell_types WHERE sample_uuid='{sample_uuid}';"
            cursor.execute(delete_existing_cell_type_data)
            delete_existing_sample_data: str =\
                f"DELETE FROM sample WHERE sample_uuid='{sample_uuid}';"
            cursor.execute(delete_existing_sample_data)

            sql_upsert_placement_relative_to_organ_code: str = \
                self.spatial_manager.create_sample_rec_sql_upsert(rec['organ']['code'], rec)
            cursor.execute(sql_upsert_placement_relative_to_organ_code)

            # NOTE: This needs to be run on prod because of interaction with Indiana code...
            try:
                sql_upsert_placement_relative_to_body: str = \
                    self.spatial_manager.create_sample_rec_sql_upsert_placement_relative_to_body(rec)
                cursor.execute(sql_upsert_placement_relative_to_body)
            except SpatialPlacementException:
                logger.error(f'An error occurred while determining placing the sample rui location within the body.')

            self.postgresql_manager.commit()
            logger.info("All work committed!")
        except (Exception, DatabaseError, UniqueViolation, NotNullViolation) as e:
            self.postgresql_manager.rollback()
            logger.error(f'Exception Type causing rollback: {e.__class__.__name__}: {e}')
        finally:
            if cursor is not None:
                cursor.close()
