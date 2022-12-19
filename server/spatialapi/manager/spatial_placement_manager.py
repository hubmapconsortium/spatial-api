import logging
import requests
import json

logger = logging.getLogger(__name__)


# With patch to fix RUI 0.5 Kidney and Spleen Placements found at:
# https://github.com/hubmapconsortium/ccf-ui/blob/main/projects/ccf-database/src/lib/hubmap/hubmap-data.ts#L447-L462
# In other words, "hack till they fix their code!"
def adjust_placement_target_if_necessary(rec: dict) -> None:
    rui_location: dict = rec['sample']['rui_location']
    donor_sex = rec['donor']['sex'].lower()
    placement_target: str = rui_location['placement']['target']
    if placement_target.startswith('http://purl.org/ccf/latest/ccf.owl#VHSpleenCC'):
        if donor_sex == 'male':
            rui_location['placement']['target'].replace('#VHSpleenCC', '#VHMSpleenCC')
        else:
            rui_location['placement']['target'].replace('#VHSpleenCC', '#VHFSpleenCC')
    elif placement_target.startswith('http://purl.org/ccf/latest/ccf.owl#VHLeftKidney') or \
            placement_target.startswith('http://purl.org/ccf/latest/ccf.owl#VHRightKidney'):
        if donor_sex == 'male':
            rui_location['placement']['target'] = placement_target.replace('#VH', '#VHM') + '_Patch'
        else:
            rui_location['placement']['target'] = placement_target.replace('#VH', '#VHMF') + '_Patch'


class SpatialPlacementException(Exception):
    pass


# This is the interface to the MSAPI Endpoint at Illinois which adjusts the placement of the sample in the
# organ relative to the body.
class SpatialPlacementManager(object):

    def __init__(self, config):
        spatial_config = config['spatialPlacement']
        self.server = spatial_config.get('Server')
        logger.info(f'SpatialPlacementManager: Server: {self.server}')

    def close(self):
        logger.info(f'SpatialPlacementManager: Closing')

    # https://ccf-api--staging.herokuapp.com/#/operations/get-spatial-placement
    def placement_relative_to_target(self, target: str,  sample_rui_location: dict) -> dict:
        target_iri: str = f"http://purl.org/ccf/latest/ccf.owl#{target}"
        logger.info(f'request: target_iri: {target_iri}; sample_rui_location: {json.dumps(sample_rui_location)}')
        resp = requests.post(self.server,
            headers={
                "Content-Type": "application/json"
            },
            json={
                "target_iri": target_iri,
                "rui_location": sample_rui_location
            }
        )
        if resp.status_code != 200:
            logger.error(f"**** SpatialPlacementManager/request: POST {self.server}: status: {resp.status_code};"
                         f" rui_location: {json.dumps(sample_rui_location)}")
            raise SpatialPlacementException()
        placement: dict = resp.json()
        logger.debug(f"SpatialPlacementManager/request: {self.server} placement: {placement}")
        return placement
