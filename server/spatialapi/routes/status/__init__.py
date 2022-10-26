from flask import Blueprint, jsonify
from pathlib import Path
import configparser
import logging

from spatialapi.manager.postgresql_manager import PostgresqlManager

status_blueprint = Blueprint('status', __name__)
logger = logging.getLogger(__name__)


def test_postgresql_manager_connection() -> bool:
    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)
    try:
        postgresql_manager = PostgresqlManager(config)
        postgresql_manager.close()
        return True
    except:
        return False


@status_blueprint.route('/status', methods=['GET'])
def get_status():
    status_data = {
        # Use strip() to remove leading and trailing spaces, newlines, and tabs
        'version': (Path(__file__).absolute().parent.parent.parent.parent / 'VERSION').read_text().strip(),
        'build': (Path(__file__).absolute().parent.parent.parent.parent / 'BUILD').read_text().strip(),
        'database_connection': test_postgresql_manager_connection()
    }
    return jsonify(status_data)
