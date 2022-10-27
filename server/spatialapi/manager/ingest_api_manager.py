import logging
import requests
import json
from typing import List
from flask import abort

from spatialapi.utils import json_error

logger = logging.getLogger(__name__)


class IngestApiManager(object):

    def __init__(self, config):
        ingest_api_config = config['ingestApi']
        self.ingest_api_url: str = ingest_api_config.get('Url').rstrip('/')

        logger.info(f"IngestApiManager IngestApiUrl: '{self.ingest_api_url}'")

    def close(self) -> None:
        logger.info(f'IngestApiManager: Closing')

    # Login through the UI (https://portal.hubmapconsortium.org/) to get the credentials...
    # In Firefox open 'Tools > Browser Tools > Web Developer Tools'.
    # Click on "Storage" then the dropdown for "Local Storage" and then the url,
    # Applications use the "nexus_token" from the returned information.
    # UI times-out in 15 min so close the browser window, and the token will last for a day or so.
    # nexus_token:"Agzm4GmNjj5rdwEm2zwJrB9EdgpeDXzz3EYxGaNrrVbedgV5qKHkC9WJlGg1p8bQwKa0aNGVenggo4SpxnaD7t7bex"

    def begin_extract_cell_count_from_secondary_analysis_files(self,
                                                               bearer_token: str,
                                                               sample_uuid: str,
                                                               ds_uuids: List[str]) -> None:
        """ The endpoint called in ingest-api asks it to start to process the secondary analysis files to extract the
        cell_type_count for the data sets given (ds_uuids). This involves ingest-api putting the request into a queue,
        and have it acted upon at a later time. So, the end point called here in ingest-api just returns a 202
        (I'm working on it). The thread that does the data processing in ingest-api will return the data to spacial-api
        through an endpoint found in routes/samples_extracted_cell_count
        PUT /samples/extracted-cell-type-counts-from-secondary-analysis-files.
        """
        ingest_uri: str = f'{self.ingest_api_url}/dataset/begin-extract-cell-count-from-secondary-analysis-files-async'
        headers: dict = {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % bearer_token
        }
        request: dict = {
            'sample_uuid': sample_uuid,
            'ds_uuids': ds_uuids
        }
        request_json = json.dumps(request)
        logger.info(f"begin_extract_cell_count_from_secondary_analysis_files; headers: {headers} request: {request_json}")
        response: str = requests.post(ingest_uri, headers=headers, json=request)
        if response.status_code == 202:
            logger.info(f"begin_extract_cell_count_from_secondary_analysis_files: url: {ingest_uri} with ds_uuids:{','.join(str(i) for i in ds_uuids)} status 202")
        else:
            abort(json_error(f"begin_extract_cell_count_from_secondary_analysis_files: url: {ingest_uri} with ds_uuids:{','.join(str(i) for i in ds_uuids)}",
                             response.status_code))
