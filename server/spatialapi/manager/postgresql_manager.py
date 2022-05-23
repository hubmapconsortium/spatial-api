import psycopg2
from typing import List
import logging
from flask import abort
from spatialapi.utils import json_error
from http import HTTPStatus

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class PostgresqlManager(object):

    def __init__(self, config):
        postgresql_config = config['postgresql']
        server: str = postgresql_config.get('Server')
        host_port: List[str] = server.split(':')
        connection: dict = {
            'dbname': postgresql_config.get('Db'),
            'user': postgresql_config.get('Username'),
            'password': postgresql_config.get('Password'),
            'host': host_port[0]
        }
        if len(host_port) > 1:
            connection['port'] = host_port[1]
        logger.info(f"PostgresqlManager: Username: {postgresql_config.get('Username')} Server: {postgresql_config.get('Server')}")
        self.conn = psycopg2.connect(**connection)

    def close(self) -> None:
        logger.info(f'PostgresqlManager: Closing connection to PostgreSQL')
        if self.conn is not None:
            self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def insert(self, sql: str) -> int:
        id: int = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            # get the generated id back
            id = cursor.fetchone()[0]
        except (Exception, psycopg2.DatabaseError) as e:
            logger.error(e)
        finally:
            if cursor is not None:
                cursor.close()
        return id

    def get_cell_marker_id(self, marker: str) -> int:
        try:
            cursor = self.conn.cursor()
            cursor.execute('CALL get_cell_marker_sp(%s, %s)', (marker, '0'))
            self.conn.commit()
            results = cursor.fetchone()
            logger.info(f'get_cell_marker_id({marker}); results: {results}')
        except (Exception, psycopg2.DatabaseError) as e:
            logger.error(e)
        finally:
            if cursor is not None:
                cursor.close()
        return results[0]

    def create_cell_markers(self, markers: List[str]) -> int:
        try:
            cursor = self.conn.cursor()
            cursor.execute('CALL create_cell_markers_sp(%s, %s)', (markers, []))
            self.conn.commit()
            results = cursor.fetchone()
            logger.info(f'create_cell_markers({markers}); results: {results}')
        except (Exception, psycopg2.DatabaseError) as e:
            logger.error(e)
        finally:
            if cursor is not None:
                cursor.close()
        return results[0]

    def create_annotation_details(self,
                                  cell_type_name: str,
                                  obo_ontology_id_uri: str,
                                  markers: List[str]
                                  ) -> int:
        ontology_id: str = obo_ontology_id_uri.rsplit('/', 1)[-1]
        logger.info(f'obo_ontology_id_uri end {ontology_id}')
        ontology_id = ontology_id.replace('_', ' ')
        logger.info(f'ontology_id: {ontology_id}')
        try:
            cursor = self.conn.cursor()
            cursor.execute('CALL create_annotation_details_sp(%s, %s, %s, %s, %s)',
                           (cell_type_name, obo_ontology_id_uri, ontology_id, markers, 0))
            self.conn.commit()
            results = cursor.fetchone()
        except (Exception, psycopg2.DatabaseError) as e:
            logger.error(e)
            #abort(json_error(f'Request Body: the attribute hibmap_id has no rui_location data', HTTPStatus.CONFLICT))
            raise e
        finally:
            if cursor is not None:
                cursor.close()
        return results[0]

    def select(self, sql: str) -> List[int]:
        data: List[int] = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            data = [row[0] for row in cursor.fetchall()]
            logger.info(f'Returned {len(data)} rows')
        except (Exception, psycopg2.DatabaseError) as e:
            logger.error(e)
        finally:
            if cursor is not None:
                cursor.close()
        return data
