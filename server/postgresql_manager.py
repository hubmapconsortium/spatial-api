import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
# pylint: disable=no-name-in-module
from psycopg2.errors import UniqueViolation
from typing import List
import configparser
import logging

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


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

    def insert(self, record):
        cursor = self.conn.cursor()
        statement: str = "INSERT INTO "
        cursor.execute(statement)
        cursor.close()


if __name__ == '__main__':
    manager = PostgresqlManager()
