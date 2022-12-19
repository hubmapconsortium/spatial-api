from flask import Blueprint, request, abort, Response
import configparser
from http import HTTPStatus
import logging

from spatialapi.manager.cell_type_count_manager import CellTypeCountManager

logger = logging.getLogger(__name__)


samples_cell_type_counts_blueprint =\
    Blueprint('finish updating the sample_uuid cell_type_count data with data from Ingest-Api', __name__)


# Ingest-api will call this when it has computed the 'cell_type_counts' from the initiation above
@samples_cell_type_counts_blueprint.route('/samples/cell-type-counts', methods=['PUT'])
def samples_cell_type_counts():
    logger.info(f'samples_cell_type_counts: finish_sample_update_uuid: PUT /samples/cell-type-counts')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'samples_cell_type_counts: Reading properties file: {app_properties}')
    config.read(app_properties)

    cell_type_count_manager = CellTypeCountManager(config)

    sample_uuid: str = request.json['sample_uuid']
    cell_type_counts: dict = request.json['cell_type_counts']

    cell_type_count_manager.sample_extracted_cell_type_counts_from_secondary_analysis_files(sample_uuid, cell_type_counts)

    return Response("Processing has been initiated", HTTPStatus.ACCEPTED)
