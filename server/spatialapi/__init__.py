from flask import Flask, jsonify, g
import logging
import time

from spatialapi.routes.db_rebuild import db_rebuild_blueprint
from spatialapi.routes.sample_extract_cell_count import sample_extract_cell_type_count_blueprint, sample_extracted_cell_count_blueprint
from spatialapi.routes.sample_reindex import sample_reindex_blueprint
from spatialapi.routes.search_hubmap_id import search_hubmap_id_to_radius_blueprint
from spatialapi.routes.spatial_search_hubmap_id import spatial_search_hubmap_id_blueprint
from spatialapi.routes.spatial_search_point import spatial_search_point_blueprint
from spatialapi.routes.status import status_blueprint

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_app(testing=False):
    app = Flask(__name__, instance_relative_config=True)
    app.debug = True  # Enable reloader and debugger

    app.register_blueprint(db_rebuild_blueprint)
    app.register_blueprint(sample_extract_cell_type_count_blueprint)
    app.register_blueprint(sample_extracted_cell_count_blueprint)
    app.register_blueprint(sample_reindex_blueprint)
    app.register_blueprint(search_hubmap_id_to_radius_blueprint)
    app.register_blueprint(spatial_search_hubmap_id_blueprint)
    app.register_blueprint(spatial_search_point_blueprint)
    app.register_blueprint(status_blueprint)

    @app.route("/", methods=['GET'])
    def hello():
        return "Hello! This is HuBMAP Spatial API service :)"

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

    @app.errorhandler(400)
    def http_bad_request(e):
        return jsonify(error=str(e)), 400

    @app.errorhandler(401)
    def http_unauthorized(e):
        return jsonify(error=str(e)), 401

    @app.errorhandler(404)
    def http_not_found(e):
        return jsonify(error=str(e)), 404

    @app.errorhandler(500)
    def http_internal_server_error(e):
        return jsonify(error=str(e)), 500

    logger.info('create_app: Done!')
    return app
