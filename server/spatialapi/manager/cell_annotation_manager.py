import logging
from spatialapi.manager.postgresql_manager import PostgresqlManager
import configparser

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

CELL_MARKER_TABLE: str = 'cell_marker'


class CellAnnotationManager(object):

    def __init__(self, config):
        self.postgresql_manager = PostgresqlManager(config)

    # https://neo4j.com/docs/api/python-driver/current/api.html
    def close(self) -> None:
        logger.info(f'CellAnnotationManager: Closing connection to PostgreSQL')
        self.postgresql_manager.close()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('resources/app.local.properties')
    manager = CellAnnotationManager(config)

    # id: int = manager.postgresql_manager.get_cell_marker_id('PAX8')
    # logger.info(f"First insert: {id}")
    # id: int = manager.postgresql_manager.get_cell_marker_id('PKHD1')
    # logger.info(f"Second insert: {id}")

    # ids: List[int] = manager.postgresql_manager.create_call_markers(
    #     ['VEGFC','ADGRL4','CCDC3','CD34','ADAMTS6','PALMD','CDH13','GFOD1','CHRM3','TEK']
    # )
    # logger.info(f"Cell Marker IDs: {ids}")

    id: int = manager.postgresql_manager.create_annotation_details(
        'Afferent / Efferent Arteriole Endothelial',
        'http://www.ontobee.org/ontology/CL?iri=http://purl.obolibrary.org/obo/CL_1001096',
        ['VEGFC', 'ADGRL4', 'CCDC3', 'CD34', 'ADAMTS6', 'PALMD', 'CDH13', 'GFOD1', 'CHRM3', 'TEK']
    )
    logger.info(f"cell_annotation_details: {id}")

    manager.close()
