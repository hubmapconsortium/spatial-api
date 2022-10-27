from flask import Blueprint, request, abort, Response
import configparser
from http import HTTPStatus
import logging

from spatialapi.manager.cell_type_count_manager import CellTypeCountManager

logger = logging.getLogger(__name__)


samples_extracted_cell_count_blueprint =\
    Blueprint('finish updating the sample_uuid cell_type_count data with data from Ingest-Api', __name__)


# Ingest-api will call this when it has computed the 'cell_type_counts' from the initiation above
@samples_extracted_cell_count_blueprint.route(
    '/samples/extracted-cell-type-counts-from-secondary-analysis-files',
    methods=['PUT'])
def samples_extracted_cell_type_counts_from_secondary_analysis_files():
    logger.info(f'finish_sample_update_uuid: PUT /sample/extracted-cell-count-from-secondary-analysis-files')

    config = configparser.ConfigParser()
    app_properties: str = 'resources/app.properties'
    logger.info(f'sample_extracted_cell_count_from_secondary_analysis_files: Reading properties file: {app_properties}')
    config.read(app_properties)

    cell_type_count_manager = CellTypeCountManager(config)

    sample_uuid: str = request.json['sample_uuid']
    cell_type_counts: dict = request.json['cell_type_counts']

    cell_type_count_manager.sample_extracted_cell_type_counts_from_secondary_analysis_files(sample_uuid, cell_type_counts)

    return Response("Processing has been initiated", HTTPStatus.ACCEPTED)
