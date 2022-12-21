import psycopg2
from typing import List
import logging

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
        if self.conn is not None:
            logger.info(f'PostgresqlManager: Closing connection to PostgreSQL')
            self.conn.close()
            self.conn = None

    def new_cursor(self):
        return self.conn.cursor()

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def insert(self, sql: str) -> int:
        id: int = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            self.conn.commit()
            # get the generated id back
            id = cursor.fetchone()[0]
        except (Exception, psycopg2.DatabaseError, psycopg2.errors.UniqueViolation) as e:
            self.conn.rollback()
            logger.error(f'Exception Type causing rollback: {e.__class__.__name__}: {e}')
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
        except (Exception, psycopg2.DatabaseError, psycopg2.errors.UniqueViolation) as e:
            self.conn.rollback()
            logger.error(f'Exception Type causing rollback: {e.__class__.__name__}: {e}')
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
        except (Exception, psycopg2.DatabaseError, psycopg2.errors.UniqueViolation) as e:
            self.conn.rollback()
            logger.error(f'Exception Type causing rollback: {e.__class__.__name__}: {e}')
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
        except (Exception, psycopg2.DatabaseError, psycopg2.errors.UniqueViolation) as e:
            self.conn.rollback()
            logger.error(f'Exception Type causing rollback: {e.__class__.__name__}: {e}')
            #abort(json_error(f'Request Body: the attribute hubmap_id has no rui_location data', HTTPStatus.CONFLICT))
            raise e
        finally:
            if cursor is not None:
                cursor.close()
        return results[0]

    def dump_anotation_detail_of_cell_type_name(self, cell_type_name: str) -> List:
        sql: str =\
            "SELECT cad.cell_type_name, cad.obo_ontology_id_uri, cad.ontology_id, array_agg(cm.marker) AS markers " \
            " FROM cell_annotation_details AS cad" \
            " JOIN cell_annotation_details_marker AS cadm ON cadm.cell_annotation_details_id = cad.id" \
            " LEFT JOIN cell_marker AS cm ON cadm.cell_marker_id = cm.id" \
            " WHERE cad.cell_type_name = %(cell_type_name)s" \
            " GROUP BY cad.cell_type_name, cad.obo_ontology_id_uri, cad.ontology_id"
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, {
                'cell_type_name': cell_type_name
            })
            data = cursor.fetchall()
            logger.info(f'Returned {len(data)} rows')
        except (Exception, psycopg2.DatabaseError, psycopg2.errors.UniqueViolation) as e:
            self.conn.rollback()
            logger.error(f'Exception Type causing rollback: {e.__class__.__name__}: {e}')
        finally:
            if cursor is not None:
                cursor.close()
        return data[0]

    def select(self, query: str, vars=None) -> List[int]:
        data: List[int] = None
        try:
            cursor = self.conn.cursor()
            # https://www.psycopg.org/docs/usage.html#query-parameters
            cursor.execute(query, vars)
            all: list = cursor.fetchall()
            #import pdb; pdb.set_trace();
            data = [row[0] for row in all]
            logger.info(f'Returned {len(data)} rows')
        except (Exception, psycopg2.DatabaseError) as e:
            logger.error(f'Exception Type: {e.__class__.__name__}: {e}')
        finally:
            if cursor is not None:
                cursor.close()
        return data

    def select_all(self, query: str, vars=None) -> list:
        all: list = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, vars)
            all: list = cursor.fetchall()
            logger.info(f'Returned {len(all)} rows')
        except (Exception, psycopg2.DatabaseError) as e:
            logger.error(f'Exception Type: {e.__class__.__name__}: {e}')
        finally:
            if cursor is not None:
                cursor.close()
        return all

    def execute(self, sql: str):
        logger.info('Erasing the database...')
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
        finally:
            if cursor is not None:
                cursor.close()
            logger.info('Database erasure is completed...')