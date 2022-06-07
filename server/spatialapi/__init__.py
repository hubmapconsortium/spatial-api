from flask import g, Flask
import logging
import time
from spatialapi.search_hubmap_id import search_hubmap_id_to_radius_blueprint
from spatialapi.spatial_search_point import spatial_search_point_blueprint
from spatialapi.spatial_search_hubmap_id import spatial_search_hubmap_id_blueprint

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_app(testing=False):
    app = Flask(__name__, instance_relative_config=True)
    app.debug = True  # Enable reloader and debugger

    app.register_blueprint(search_hubmap_id_to_radius_blueprint)
    app.register_blueprint(spatial_search_point_blueprint)
    app.register_blueprint(spatial_search_hubmap_id_blueprint)

    @app.route("/")
    def hello():
        return "Hello World!"

    @app.before_request
    def before_request():
        start_time = time.time()
        g.request_start_time = start_time

    @app.teardown_request
    def teardown_request(exception=None):
        diff = time.time() - g.request_start_time
        logger.info(f'teardown_request: Request runtime: {round(diff, 3)*1000.0} msec')

    @app.teardown_appcontext
    def close_db(error): # pylint: disable=unused-argument
        if 'spatial_manager' in g:
            logger.info(f"Closing SpatialManager db connections")
            g.spatial_manager.close()

    logger.info('create_app: Done!')
    return app
