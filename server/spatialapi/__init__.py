from flask import g, Flask
import logging
import time
from manager.spatial_manager import SpatialManager
from search_hubmap_id import search_hubmap_id_to_radius
import configparser

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(testing=False):
    app = Flask(__name__, instance_relative_config=True)

    app.register_blueprint(search_hubmap_id_to_radius)

    config = configparser.ConfigParser()
    config.read('../../resources/app.properties')
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

    return app
