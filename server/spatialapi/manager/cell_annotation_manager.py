import logging
from spatialapi.manager.postgresql_manager import PostgresqlManager
import configparser
import requests
from bs4 import BeautifulSoup
import re
from typing import List

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class CellAnnotationManager(object):

    def __init__(self, config):
        cell_annotation_config = config['cellAnnotation']
        self.azmuth_uri: str = cell_annotation_config.get('Azmuth')

        self.postgresql_manager = PostgresqlManager(config)

    # https://neo4j.com/docs/api/python-driver/current/api.html
    def close(self) -> None:
        logger.info(f'CellAnnotationManager: Closing connection to PostgreSQL')
        self.postgresql_manager.close()

    def load_annotation_details(self):
        html_text: str = requests.get(self.azmuth_uri).text
        bs_object = BeautifulSoup(html_text, 'html.parser')
        details =  bs_object \
            .find("body") \
            .find("main", attrs={"id": "content"}) \
            .find("div", attrs={"class": "container"}) \
            .find("section", attrs={"class": "main-content"}) \
            .find("div", attrs={"class": "section"}) \
            .find_all("details")
        for detail in details:
            if detail.find("summary", string=re.compile(r'^.*annotation\.l3.*$')) is not None:
                # Skip the header row...
                rows = detail.find("table").find_all("tr")[1:]
                for row in rows:
                    cell_type_name: str = row.select('td:nth-of-type(1)')[0].string.strip()
                    obo_ontology_id_uri: str = row.select('td:nth-of-type(2)')[0].find('a').get("href")
                    markers: List[str] = row.select('td:nth-of-type(3)')[0].string.strip().split(',')
                    markers_stripped: List[str] = [s.strip() for s in markers]
                    id: int = manager.postgresql_manager.create_annotation_details(
                        cell_type_name, obo_ontology_id_uri, markers_stripped
                    )
                    logger.info(f"cell_annotation_details: {id}")


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

    # id: int = manager.postgresql_manager.create_annotation_details(
    #     'Afferent / Efferent Arteriole Endothelial',
    #     'http://www.ontobee.org/ontology/CL?iri=http://purl.obolibrary.org/obo/CL_1001096',
    #     ['VEGFC', 'ADGRL4', 'CCDC3', 'CD34', 'ADAMTS6', 'PALMD', 'CDH13', 'GFOD1', 'CHRM3', 'TEK']
    # )
    # logger.info(f"cell_annotation_details: {id}")

    #manager.load_annotation_details()

    #cell_type_bame: str = 'Afferent / Efferent Arteriole Endothelial'
    cell_type_name: str = 'Cortical Collecting Duct Intercalated Type A'
    annotation_details =\
        manager.postgresql_manager.dump_anotation_detail_of_cell_type_name(cell_type_name)
    print(f'annotation_details: {annotation_details}')

    manager.close()
