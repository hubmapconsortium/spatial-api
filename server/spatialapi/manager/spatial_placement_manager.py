import logging
import requests
import json

logger = logging.getLogger(__name__)


class SpatialPlacementManager(object):

    def __init__(self, config):
        spatial_config = config['spatialPlacement']
        self.server = spatial_config.get('Server')
        logger.info(f'SpatialPlacementManager: Server: {self.server}')

    # https://ccf-api--staging.herokuapp.com/#/operations/get-spatial-placement
    def placement_relative_to_target(self, target: str,  sample_rui_location: dict) -> dict:
        target_iri: str = f"http://purl.org/ccf/latest/ccf.owl#{target}"
        logger.info(f'request: target_iri: {target_iri}; sample_rui_location: {json.dumps(sample_rui_location)}')
        resp = requests.post(self.server,
            headers = {
                "Content-Type": "application/json"
            },
            json = {
                "target_iri": target_iri,
                "rui_location": sample_rui_location
            }
        )
        if resp.status_code != 200:
            logger.info(f"SpatialPlacementManager/request: POST {self.server}: status: {resp.status_code}; rui_location: {json.dumps(sample_rui_location)}")
            exit()
        placement: dict = resp.json()
        logger.debug(f"SpatialPlacementManager/request: {self.server} placement: {placement}")
        return placement
