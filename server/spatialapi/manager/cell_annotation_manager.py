import logging
import configparser
import requests
from bs4 import BeautifulSoup
import re
from urllib import parse
import psycopg2
from typing import List

from spatialapi.manager.postgresql_manager import PostgresqlManager

logger = logging.getLogger(__name__)


class CellAnnotationManager(object):

    def __init__(self, config):
        cell_annotation_config = config['cellAnnotation']
        self.azimuth_uri: str = cell_annotation_config.get('Azimuth')
        logger.info(f"CellAnnotationManager Azimuth: {parse.quote(self.azimuth_uri)}")

        self.postgresql_manager = PostgresqlManager(config)

    # https://neo4j.com/docs/api/python-driver/current/api.html
    def close(self) -> None:
        logger.info(f'CellAnnotationManager: Closing')
        self.postgresql_manager.close()

    def find_rows_in_azimuth_uri_table(self, summary_re: re, first_label_entry: str):
        html_text: str = requests.get(self.azimuth_uri).text
        bs_object = BeautifulSoup(html_text, 'html.parser')
        details = bs_object \
            .find("body") \
            .find("main", attrs={"id": "content"}) \
            .find("div", attrs={"class": "container"}) \
            .find("section", attrs={"class": "main-content"}) \
            .find("div", attrs={"class": "section"}) \
            .find_all("details")
        for detail in details:
            summary: str = detail.find("summary", string=re.compile(summary_re))
            if summary is not None:
                logger.info(f"find_rows_in_azimuth_uri_table summary: {summary}")
                # Skip the header row...
                rows: List[str] = detail.find("table").find_all("tr")[1:]
                if rows[0].select('td:nth-of-type(1)')[0].string.strip() == first_label_entry:
                    return rows

    def load_annotation_details_from_azimuth_uri_table(self, url_table_summary: re, first_label_entry: str):
        rows = self.find_rows_in_azimuth_uri_table(url_table_summary, first_label_entry)
        #import pdb; pdb.set_trace()
        for row in rows:
            cell_type_name: str = row.select('td:nth-of-type(1)')[0].string.strip()
            try:
                obo_ontology_id_uri: str = row.select('td:nth-of-type(2)')[0].find('a').get("href")
            except AttributeError as e:
                obo_ontology_id_uri: str = 'None'
            markers: List[str] = row.select('td:nth-of-type(3)')[0].string.strip().split(',')
            markers_stripped: List[str] = [s.strip() for s in markers]
            try:
                id: int = self.postgresql_manager.create_annotation_details(
                    cell_type_name, obo_ontology_id_uri, markers_stripped
                )
                logger.info(f"cell_annotation_details: {id}")
            except psycopg2.errors.UniqueViolation as e:
                logger.info(f"create_annotation_details {e}")

    def load_annotation_details(self):
        self.load_annotation_details_from_azimuth_uri_table(r'^.*annotation\.l3.*$', 'Afferent / Efferent Arteriole Endothelial')
        self.load_annotation_details_from_azimuth_uri_table(r'^.*annotation\.l2.*$', 'Afferent / Efferent Arteriole Endothelial')
        self.load_annotation_details_from_azimuth_uri_table(r'^.*annotation\.l1.*$', 'Ascending Thin Limb')

    def check_annotation_details_from_azimuth_uri_table(self, url_table_summary: re):
        rows = self.find_rows_in_azimuth_uri_table(url_table_summary)
        for row in rows:
            cell_type_name: str = row.select('td:nth-of-type(1)')[0].string.strip()
            obo_ontology_id_uri: str = row.select('td:nth-of-type(2)')[0].find('a').get("href")
            markers: List[str] = row.select('td:nth-of-type(3)')[0].string.strip().split(',')
            markers_stripped: List[str] = [s.strip() for s in markers]
            data: List = manager.postgresql_manager.dump_anotation_detail_of_cell_type_name(cell_type_name)
            if data[0] != cell_type_name:
                logger.error(f"The cell_type_names do not match web: {cell_type_name}, db: {data[0]}")
            if data[1] != obo_ontology_id_uri:
                logger.error(f"The obo_ontology_id_uris do not match web: {obo_ontology_id_uri}, db: {data[1]}")
            if  sorted(markers_stripped) != sorted(data[2]):
                logger.error(f"The markers do not match web: {markers_stripped}, db: {data[2]}")
        logger.info(f'Done! check_annotation_details {len(rows)} processed')

    def check_annotation_details(self):
        self.check_annotation_details_from_azimuth_uri_table(r'^.*annotation\.l3.*$')
        self.check_annotation_details_from_azimuth_uri_table(r'^.*annotation\.l2.*$')
        self.check_annotation_details_from_azimuth_uri_table(r'^.*annotation\.l1.*$')


if __name__ == '__main__':
    import argparse

    class RawTextArgumentDefaultsHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawTextHelpFormatter
    ):
        pass

    # https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(
        description='Tissue Sample Cell Type Manager',
        formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("-C", '--config', type=str, default='resources/app.local.properties',
                        help='config file to use')
    parser.add_argument("-c", '--check', action="store_true",
                        help='check cell_annotation_details and related tables by scraping Azimuth data from web page')
    # (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/cell_annotation_manager.py -d 'Connecting Tubule')
    parser.add_argument("-d", "--detail_cell_type_name", type=str,
                        help='dump cell_anotation_details of cell_type_name')
    parser.add_argument("-m", "--get_cell_marker_id", type=str,
                        help='get cell_marker id from marker_name')

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    manager = CellAnnotationManager(config)

    try:

        # ids: List[int] = manager.postgresql_manager.create_cell_markers(
        #     ['VEGFC','ADGRL4','CCDC3','CD34','ADAMTS6','PALMD','CDH13','GFOD1','CHRM3','TEK']
        # )
        # logger.info(f"Cell Marker IDs: {ids}")

        # id: int = manager.postgresql_manager.create_annotation_details(
        #     'Afferent / Efferent Arteriole Endothelial',
        #     'http://www.ontobee.org/ontology/CL?iri=http://purl.obolibrary.org/obo/CL_1001096',
        #     ['VEGFC', 'ADGRL4', 'CCDC3', 'CD34', 'ADAMTS6', 'PALMD', 'CDH13', 'GFOD1', 'CHRM3', 'TEK']
        # )
        # logger.info(f"cell_annotation_details: {id}")

        if args.check:
            manager.check_annotation_details()
        elif args.detail_cell_type_name is not None:
            print(f'detail_cell_type_name: {args.detail_cell_type_name}')
            annotation_details = \
                manager.postgresql_manager.dump_anotation_detail_of_cell_type_name(args.detail_cell_type_name)
            print(f'annotation_details (cell_type_name, obo_ontoloty_id_uri, ontology_id, markers): {annotation_details}')
        elif args.get_cell_marker_id is not None:
            id: int = manager.postgresql_manager.get_cell_marker_id(args.get_cell_marker_id)
            logger.info(f"cell_marker.marker:{args.get_cell_marker_id} id: {id}")

    finally:
        manager.close()
        logger.info('Done!')
