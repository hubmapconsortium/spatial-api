from flask import g, Flask
import logging
import time
import configparser
from spatialapi.manager.spatial_manager import SpatialManager
from spatialapi.search_hubmap_id import search_hubmap_id_to_radius_blueprint

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(testing=False):
    app = Flask(__name__, instance_relative_config=True)

    app.register_blueprint(search_hubmap_id_to_radius_blueprint)

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'Reading properties file: {app_properties}')
    config.read(app_properties)
    g.spatial_manager = SpatialManager(config)

    @app.before_request
    def before_request():
        g.request_start_time = time.time()

    @app.teardown_request
    def teardown_request(exception=None):
        diff = time.time() - g.request_start_time
        logger.info(f'Request runtime: {diff}')

    @app.teardown_appcontext
    def close_db(error): # pylint: disable=unused-argument
        if 'spatial_manager' in g:
            logger.info(f"Closing SpatialManager db connections")
            g.spatial_manager.close()

    logger.info('Serving...')
    return app
