import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
# pylint: disable=no-name-in-module
from psycopg2.errors import UniqueViolation
from typing import List, Tuple
import configparser
import logging

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TABLE: str = 'sample'


class PostgresqlManager(object):

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('resources/app.properties')
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
        self.conn = psycopg2.connect(**connection)
        #import pdb; pdb.set_trace()

    def close(self) -> None:
        self.conn.close()

    def commit(self) -> None:
        self.conn.commit()

    def insert(self, sql: str) -> int:
        id: int = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            # get the generated id back
            id = cursor.fetchone()[0]
            #import pdb; pdb.set_trace()
            self.conn.commit()
            cursor.close()
        except (Exception, psycopg2.DatabaseError) as e:
            logger.error(e)
        return id

    def select(self, sql: str) -> List[int]:
        data: List[int] = None
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)
            data = [row[0] for row in cursor.fetchall()]
            #import pdb; pdb.set_trace()
            logger.info(f'Returned {len(data)} rows')
            cursor.close()
        except (Exception, psycopg2.DatabaseError) as e:
            logger.error(e)
        return data


if __name__ == '__main__':
    manager = PostgresqlManager()
