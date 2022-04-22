from flask import Blueprint, redirect, current_app, jsonify, make_response, session, g
import logging

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

search_hubmap_id_to_radius_blueprint = Blueprint('search_hubmap_id_to_radius_blueprint', __name__)


@search_hubmap_id_to_radius_blueprint.route('/search/hubmap_id/<id>/radius/<r>', methods=['GET'])
def search_hubmap_id_to_radius(id, r):
    logger.info(f'search_hubmap_id_to_radius: GET /search/hubmap_id/{id}/radius/{r}')
    #replace by the correct way to check token validity.
    # authenticated = session.get('is_authenticated')
    # if not authenticated:
    #     #return redirect(url_for('login.login'))
    #     redirect_url = current_app.config['FLASK_APP_BASE_URI'].rstrip('/') + '/login'
    #     return redirect(redirect_url)
    results = g.spatial_manager.find_within_radius_at_hubmap_id(r, id)
    logger.info(f'search_hubmap_id_to_radius; find_within_radius_at_hubmap_id({id},{r}): {results}')
    response = make_response(jsonify(ids=results), 200)
    response.headers["Content-Type"] = "application/json"
    return response
