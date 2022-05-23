import logging
from flask import abort
from typing import List
from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.manager.spatial_placement_manager import SpatialPlacementManager
from spatialapi.utils import json_error
from http import HTTPStatus
import json
import configparser

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class SpatialManager(object):

    def __init__(self, config):
        self.neo4j_manager = Neo4jManager(config)
        self.postgresql_manager = PostgresqlManager(config)
        self.spatial_placement_manager = SpatialPlacementManager(config)

        spatial_config = config['spatial']
        self.table = spatial_config.get('Table')
        logger.info(f'SpatialManager: Table: {self.table}')

    def close(self):
        logger.info(f'Neo4jManager: Closing connection to Neo4J & PostgreSQL')
        self.neo4j_manager.close()
        self.postgresql_manager.close()

    def create_YZ_plane_at_X(self, x: float, y: float, z: float) -> str:
        return f"((" \
               f"{x} {-y} {-z}, " \
               f"{x} {-y} {z}, " \
               f"{x} {y} {z}, " \
               f"{x} {y} {-z}, " \
               f"{x} {-y} {-z}" \
               f"))"

    def create_XY_plane_at_Z(self, x: float, y: float, z: float) -> str:
        # f"((-5 -5 -5, 5 -5 -5, 5 5 -5, -5 5 -5, -5 -5 -5))," \
        return f"((" \
               f"{-x} {-y} {z}, " \
               f"{-x} {y} {z}, " \
               f"{x} {y} {z}, " \
               f"{x} {-y} {z}, " \
               f"{-x} {-y} {z}" \
               f"))"

    def create_XZ_plane_at_Y(self, x: float, y: float, z: float) -> str:
        return f"((" \
               f"{-x} {y} {-z}, " \
               f"{-x} {y} {z}, " \
               f"{x} {y} {z}, " \
               f"{x} {y} {-z}, " \
               f"{-x} {y} {-z}" \
               f"))"

    # The PostGRIS geometry should be constructed with the centroid of the object being at POINT(0,0,0)
    def create_multipolygon_geom_with_dimension(self, x: float, y: float, z: float) -> str:
        return f"'MULTIPOLYGON Z(" \
               f"{self.create_YZ_plane_at_X(-x/2, y/2, z/2)}" \
               f",{self.create_YZ_plane_at_X(x/2, y/2, z/2)}" \
               f",{self.create_XZ_plane_at_Y(x/2, -y/2, z/2)}" \
               f",{self.create_XZ_plane_at_Y(x/2, y/2, z/2)}" \
               f",{self.create_XY_plane_at_Z(x/2, y/2, -z/2)}" \
               f",{self.create_XY_plane_at_Z(x/2, y/2, z/2)}" \
               f" )'"

    # TODO: We are doing NOTHING with '*_units' or 'rotation_order' here...
    def create_geometry(self, rui_location: dict) -> str:
        geom: str = self.create_multipolygon_geom_with_dimension(
            rui_location['x_dimension'], rui_location['y_dimension'], rui_location['z_dimension'])
        placement: dict = rui_location['placement']
        return "ST_Translate(" \
               "ST_Scale(" \
               "ST_RotateZ(ST_RotateY(ST_RotateX(" \
               f"ST_GeomFromText({geom})," \
               f" {placement['x_rotation']}), {placement['y_rotation']}), {placement['z_rotation']})," \
               f" {placement['x_scaling']}, {placement['y_scaling']}, {placement['z_scaling']})," \
               f" {placement['x_translation']}, {placement['y_translation']}, {placement['z_translation']})"

    def create_sql_insert(self, target_iri: str, rec: dict) -> str:
        return f"INSERT INTO {self.table}" \
               " (organ_uuid, organ_code," \
               " donor_uuid, donor_sex," \
               " relative_spatial_entry_iri," \
               " sample_uuid, sample_hubmap_id, sample_specimen_type," \
               " sample_rui_location, sample_geom" \
               ") VALUES (" \
               f"'{rec['organ']['uuid']}', '{rec['organ']['code']}', " \
               f"'{rec['donor']['uuid']}', '{rec['donor']['sex']}', " \
               f"'{target_iri}', " \
               f"'{rec['sample']['uuid']}', '{rec['sample']['hubmap_id']}', '{rec['sample']['specimen_type']}', " \
               f"'{json.dumps(rec['sample']['rui_location'])}', {self.create_geometry(rec['sample']['rui_location'])}" \
               f")" \
               f" RETURNING id;"

    def insert_rec(self, target_iri: str, rec: dict) -> None:
        sql_insert_statement: str = self.create_sql_insert(target_iri, rec)
        id: int = self.postgresql_manager.insert(sql_insert_statement)
        logger.info(f"Inserting geom record as; id={id}")

    def insert_rec_with_placement_at_target(self, target: str, rec: dict) -> None:
        placement: dict = \
            self.spatial_placement_manager.placement_relative_to_target(target, rec['sample']['rui_location'])
        rec['sample']['rui_location']['placement'] = placement
        self.insert_rec(target, rec)

    # Patch to fix RUI 0.5 Kidney and Spleen Placements
    # https://github.com/hubmapconsortium/ccf-ui/blob/main/projects/ccf-database/src/lib/hubmap/hubmap-data.ts#L447-L462
    def adjust_placement_target_if_necessary(self, rec) -> dict:
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
        return rec

    def insert_rec_relative_to_spatial_entry_iri(self, rec: dict) -> None:
        donor_sex: str = rec['donor']['sex'].lower()
        if donor_sex == 'male':
            self.insert_rec_with_placement_at_target('VHMale', self.adjust_placement_target_if_necessary(rec))
        if donor_sex == 'female':
            self.insert_rec_with_placement_at_target('VHFemale', self.adjust_placement_target_if_necessary(rec))

    def insert_organ_data(self, organ: str) -> None:
        logger.info(f"Inserting data for organ: {organ}")
        recs: List[dict] = self.neo4j_manager.query_organ(organ)
        for rec in recs:
            # TODO: Need only one line per sample, so the geom data should be normalied.
            self.insert_rec(rec['organ']['code'], rec)
            self.insert_rec_relative_to_spatial_entry_iri(rec)


    def find_within_radius_at_origin(self, radius: float, x: float, y: float, z: float) -> List[int]:
        sql: str =\
            f"""SELECT sample_hubmap_id FROM {self.table}
            WHERE ST_3DDWithin(sample_geom, ST_GeomFromText('POINTZ({x} {y} {z})'), {radius});
            """
        return self.postgresql_manager.select(sql)

    def find_relative_to_spatial_entry_iri_within_radius_from_point(self,
                                                                    spatial_entry_iri: str,
                                                                    radius: float,
                                                                    x: float, y: float, z: float
                                                                    ) -> List[int]:
        sql: str =\
            f"""SELECT sample_hubmap_id FROM {self.table}
            WHERE relative_spatial_entry_iri = '{spatial_entry_iri}'
            AND ST_3DDWithin(sample_geom, ST_GeomFromText('POINTZ({x} {y} {z})'), {radius});
            """
        return self.postgresql_manager.select(sql)

    # This should probably be a Ne04J query until we get all of the data with rui_locations...
    def hubmap_id_rui_location(self, hubmap_id: str) -> dict:
        sql: str =\
            f"""SELECT sample_rui_location FROM {self.table}
            WHERE sample_hubmap_id = '{hubmap_id}';
            """
        recs: List[str] = self.postgresql_manager.select(sql)
        if len(recs) == 0:
            abort(json_error(f'Request Body: the attribute hibmap_id has no rui_location data', HTTPStatus.BAD_REQUEST))
        if len(recs) != 1:
            logger.error(f'Query against a single sample_hubmap_id={hubmap_id} returned multiple rows')
        logger.info(f'hubmap_id_rui_location: hubmap_id: {hubmap_id}; rui_location: {recs[0]}')
        return json.loads(recs[0])

    def find_relative_to_spatial_entry_iri_within_radius_from_hubmap_id(self,
                                                                        spatial_entry_iri: str,
                                                                        radius: float,
                                                                        hubmap_id: str
                                                                        ) -> List[int]:
        rui_location: dict = self.hubmap_id_rui_location(hubmap_id)
        sql: str =\
            f"""SELECT sample_hubmap_id FROM {self.table}
            WHERE relative_spatial_entry_iri = '{spatial_entry_iri}'
            AND ST_3DDWithin(sample_geom,
                ST_GeomFromText(
                    'POINTZ({rui_location['x_dimension']} {rui_location['y_dimension']} {rui_location['z_dimension']})'
                ),
                {radius});
            """
        return self.postgresql_manager.select(sql)


    def find_within_radius_at_sample_hubmap_id(self, radius: float, hubmap_id: str) -> List[int]:
        rui_location: dict = self.hubmap_id_rui_location(hubmap_id)
        return self.find_within_radius_at_origin(radius,
                                                 rui_location['x_dimension'], rui_location['y_dimension'],
                                                 rui_location['z_dimension'])


# NOTE: When running in a local docker container the tables are created automatically.
# TODO: Nothing is being done with units.
if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('resources/app.local.properties')
    manager = SpatialManager(config)
    # Rather than using RK use the UBERON number. If there is no UBERON number it doesn't exist yet.
    # RK:
    # description: Kidney (Right)
    # iri: http://purl.obolibrary.org/obo/UBERON_0004539
    # https://raw.githubusercontent.com/hubmapconsortium/search-api/master/src/search-schema/data/definitions/enums/organ_types.yaml
    manager.insert_organ_data('RK')
    manager.insert_organ_data('LK')

    manager.close()
