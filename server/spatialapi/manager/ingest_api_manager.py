import logging
from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.utils.ssh import Ssh
import configparser
import requests
import time
import json
from urllib import parse
from typing import List
from flask import abort
from spatialapi.utils import json_error

logger = logging.getLogger(__name__)


class IngestApiManager(object):

    def __init__(self, config):
        ingest_api_config = config['ingestApi']
        self.ingest_api_url: str = ingest_api_config.get('Url').rstrip('/')
        logger.info(f"IngestApiManager IngestApiUrl: '{parse.quote(self.ingest_api_url)}'")

    def close(self) -> None:
        logger.info(f'IngestApiManager: Closing')

    # Login through the UI (https://portal.hubmapconsortium.org/) to get the credentials...
    # In Firefox open 'Tools > Browser Tools > Web Developer Tools'.
    # Click on "Storage" then the dropdown for "Local Storage" and then the url,
    # Applications use the "nexus_token" from the returned information.
    # UI times-out in 15 min so close the browser window, and the token will last for a day or so.
    # nexus_token:"Agzm4GmNjj5rdwEm2zwJrB9EdgpeDXzz3EYxGaNrrVbedgV5qKHkC9WJlGg1p8bQwKa0aNGVenggo4SpxnaD7t7bex"
    def ds_uuid_to_psc_path(self, ds_uuid: str, bearer_token: str) -> str:
        ingest_uri: str = f'{self.ingest_api_url}/datasets/{ds_uuid}/file-system-abs-path'
        headers: dict = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % bearer_token
        }
        response: str = requests.get(ingest_uri, headers=headers)
        if response.status_code != 200:
            if response.status_code == 404:
                logger.info(f"ds_uuid_to_psc_path: ds_uuid '{ds_uuid}' not found.")
                return None
            logger.info(f"ds_uuid_to_psc_path: ds_uuid '{ingest_uri}' status code: {response.status_code}.")
            return None
        response_json: dict = response.json()
        if 'path' not in response_json:
            return None
        return response_json['path']

    def extract_cell_count_from_secondary_analysis_files(self, bearer_token: str, ds_uuids: List[str]) -> dict:
        ingest_uri: str = f'{self.ingest_api_url}/dataset/extract-cell-count-from-secondary-analysis-files'
        headers: dict = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer %s' % bearer_token
        }
        request: dict = {'ds_uuids': ds_uuids}
        logger.info(f"extract_cell_count_from_secondary_analysis_files; request: {request}")
        response: str = requests.post(ingest_uri, headers=headers, json=request)
        if response.status_code != 200:
            abort(json_error(f"extract_cell_count_from_secondary_analysis_files: ds_uuids:{','.join(str(i) for i in ds_uuids)}",
                             response.status_code))
        return response.json()


if __name__ == '__main__':
    import argparse

    class RawTextArgumentDefaultsHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawTextHelpFormatter
    ):
        pass

    parser = argparse.ArgumentParser(description='Interface to Ingest API',
                                     formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("-b", '--bearer_token', type=str,
                        help='bearer token to use for the Ingest API call')
    parser.add_argument("-p", '--psc_path', type=str,
                        help='get the psc path for the dataset uuid argument')

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    manager = IngestApiManager(config)

    try:
        if args.psc_path is not None and args.bearer_token is not None:
            path: str = manager.ds_uuid_to_psc_path(args.psc_path, args.bearer_token)
            logger.info(f"ds_uuid_to_psc_path: path:{path}")
    finally:
        manager.close()
        logger.info('Done!')