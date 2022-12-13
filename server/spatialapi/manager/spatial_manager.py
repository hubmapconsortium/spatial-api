import logging
from http import HTTPStatus
from typing import List
from flask import abort
import json
import configparser
import copy

from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.manager.spatial_placement_manager import SpatialPlacementManager, adjust_placement_target_if_necessary
from spatialapi.utils import json_error

logger = logging.getLogger(__name__)


def _donor_sex_to_target_iri(donor_sex: str) -> str:
    target_iri: str = None
    if donor_sex == 'male':
        target_iri = 'VHMale'
    elif donor_sex == 'female':
        target_iri = 'VHFemale'
    else:
        # TODO: Throw error
        pass
    return target_iri


class SpatialManager(object):
    # TODO: Nothing is being done with units.

    def __init__(self, config):
        self.neo4j_manager = Neo4jManager(config)
        self.postgresql_manager = PostgresqlManager(config)
        self.spatial_placement_manager = SpatialPlacementManager(config)

        spatial_config = config['spatial']
        self.table = spatial_config.get('Table')
        logger.info(f'{self.__class__.__name__}: Table: {self.table}')

    def close(self):
        logger.info(f'SpatialManager: Closing')
        self.neo4j_manager.close()
        self.postgresql_manager.close()
        self.spatial_placement_manager.close()

    # Example from https://postgis.net/docs/ST_IsClosed.html
    # There is a winding order for surfaces: inside->clockwise, outside -> counterclockwise.
    # ALL of these surfaces are wound counterclockwise which makes them outside surfaces.
    # They will build a POLYHEDRALSURFACE which ST_IsClosed.
    #
    # The naming convention below assumes that you are looking at the object down the Z-axis (positive to negative).
    # So, Right, Top, and Front surfaces always have x, y, z being positive, and
    # Left, Bottom, and Back surfaces always have x, y, z being negative.

    # https://gis.stackexchange.com/questions/214572/st-makesolid-creating-an-invalid-solid-from-closed-polyhedralsurfacez

    def create_XY_plane_at_Z_Front(self, x: float, y: float, z: float) -> str:
        return f"((" \
               f"{-x} {-y} {z}, " \
               f"{x} {-y} {z}, " \
               f"{x} {y} {z}, " \
               f"{-x} {y} {z}, " \
               f"{-x} {-y} {z}" \
               f"))"

    def create_XY_plane_at_Z_Back(self, x: float, y: float, z: float) -> str:
        return f"((" \
               f"{-x} {-y} {-z}, " \
               f"{-x} {y} {-z}, " \
               f"{x} {y} {-z}, " \
               f"{x} {-y} {-z}, " \
               f"{-x} {-y} {-z}" \
               f"))"

    def create_YZ_plane_at_X_Left(self, x: float, y: float, z: float) -> str:
        return f"((" \
               f"{-x} {-y} {-z}, " \
               f"{-x} {-y} {z}, " \
               f"{-x} {y} {z}, " \
               f"{-x} {y} {-z}, " \
               f"{-x} {-y} {-z}" \
               f"))"

    def create_YZ_plane_at_X_Right(self, x: float, y: float, z: float) -> str:
        return f"((" \
               f"{x} {-y} {-z}, " \
               f"{x} {y} {-z}, " \
               f"{x} {y} {z}, " \
               f"{x} {-y} {z}, " \
               f"{x} {-y} {-z}" \
               f"))"

    def create_XZ_plane_at_Y_Top(self, x: float, y: float, z: float) -> str:
        return f"((" \
               f"{-x} {y} {-z}, " \
               f"{-x} {y} {z}, " \
               f"{x} {y} {z}, " \
               f"{x} {y} {-z}, " \
               f"{-x} {y} {-z}" \
               f"))"

    def create_XZ_plane_at_Y_Bottom(self, x: float, y: float, z: float) -> str:
        return f"((" \
               f"{-x} {-y} {-z}, " \
               f"{x} {-y} {-z}, " \
               f"{x} {-y} {z}, " \
               f"{-x} {-y} {z}, " \
               f"{-x} {-y} {-z}" \
               f"))"

    # The PostGRIS geometry should be constructed with the centroid of the object being at POINT(0,0,0)
    def create_geom_with_dimension(self, x: float, y: float, z: float) -> str:
        # https://postgis.net/workshops/postgis-intro/3d.html
        # PolyhedralSurface - A 3D figure made exclusively of Polygons
        # POLYHEDRALSURFACE - A PolyhedralSurface is a contiguous collection of polygons, which share common boundary segments
        # From this https://gdal.org/development/rfc/rfc64_triangle_polyhedralsurface_tin.html
        # it appears that a MULTIPOLYGON is actually a collection of surfaces and not a single entity?!
        #
        # https://stackoverflow.com/questions/68379566/postgres-postgis-sfcgal-st-3darea-not-working
        # To represent a mesh surface in Postgres, we should use POLYHEDRALSURFACE.
        # This geometry is also a collection of polygons: they have to be "adjacent to each other",
        # AND they all have to be all "outside surfaces."
        return f"'POLYHEDRALSURFACE Z(" \
               f"{self.create_XY_plane_at_Z_Front(x/2, y/2, z/2)}" \
               f",{self.create_XY_plane_at_Z_Back(x/2, y/2, z/2)}" \
               f",{self.create_YZ_plane_at_X_Left(x/2, y/2, z/2)}" \
               f",{self.create_YZ_plane_at_X_Right(x/2, y/2, z/2)}" \
               f",{self.create_XZ_plane_at_Y_Top(x/2, y/2, z/2)}" \
               f",{self.create_XZ_plane_at_Y_Bottom(x/2, y/2, z/2)}" \
               f" )'"

    # TODO: We are doing NOTHING with '*_units' or 'rotation_order' here...
    # NOTE: When closed surfaces are created with WKT, they are treated as areal rather than solid.
    # To make them solid, you need to use ST_MakeSolid. Areal geometries have no volume.
    # ST_MakeSolid — Cast the geometry into a solid. No check is performed. To obtain a valid solid,
    # the input geometry must be a closed Polyhedral Surface or a closed TIN (see: python3 ./tests/geom.py -c).
    def create_geometry(self, rui_location: dict) -> str:
        geom: str = self.create_geom_with_dimension(
            rui_location['x_dimension'], rui_location['y_dimension'], rui_location['z_dimension'])
        placement: dict = rui_location['placement']
        return "ST_Translate(" \
               "ST_Scale(" \
               "ST_RotateZ(ST_RotateY(ST_RotateX(" \
               f"ST_MakeSolid({geom})," \
               f" {placement['x_rotation']}), {placement['y_rotation']}), {placement['z_rotation']})," \
               f" {placement['x_scaling']}, {placement['y_scaling']}, {placement['z_scaling']})," \
               f" {placement['x_translation']}, {placement['y_translation']}, {placement['z_translation']})"

    def create_sample_rec_sql_upsert(self, target_iri: str, rec: dict) -> str:
        organ_uuid: str = rec['organ']['uuid']
        organ_code: str = rec['organ']['code']
        donor_uuid: str = rec['donor']['uuid']
        donor_sex: str = rec['donor']['sex']
        sample_uuid: str = rec['sample']['uuid']
        sample_hubmap_id: str = rec['sample']['hubmap_id']
        sample_specimen_type: str = rec['sample']['specimen_type']
        sample_last_modified_timestamp: int = rec['sample']['last_modified_timestamp']
        sample_rui_location: str = json.dumps(rec['sample']['rui_location'])
        sample_geom: str = self.create_geometry(rec['sample']['rui_location'])
        return f"INSERT INTO {self.table}" \
               " (organ_uuid, organ_code, donor_uuid, donor_sex, relative_spatial_entry_iri, sample_uuid," \
               " sample_hubmap_id, sample_specimen_type, sample_rui_location," \
               " sample_last_modified_timestamp, sample_geom)" \
               " VALUES (" \
               f"'{organ_uuid}', '{organ_code}', '{donor_uuid}', '{donor_sex}', '{target_iri}', '{sample_uuid}'," \
               f" '{sample_hubmap_id}', '{sample_specimen_type}', '{sample_rui_location}'," \
               f" {sample_last_modified_timestamp}, {sample_geom}" \
               ")" \
               " ON CONFLICT ON CONSTRAINT sample_relative_spatial_entry_sample_uuid_key DO UPDATE SET" \
               f" organ_uuid = '{organ_uuid}', organ_code = '{organ_code}', donor_uuid = '{donor_uuid}'," \
               f" donor_sex = '{donor_sex}', sample_hubmap_id = '{sample_hubmap_id}'," \
               f" sample_specimen_type = '{sample_specimen_type}', sample_rui_location = '{sample_rui_location}'," \
               f" sample_geom = {sample_geom}" \
               " RETURNING id;"
    
    def create_sample_rec_sql_upsert_placement_relative_to_body(self, rec: dict) -> str:
        target_iri = _donor_sex_to_target_iri(rec['donor']['sex'].lower())
        logger.debug(f"Creating sql upsert placement relative to body with target_iri: {target_iri}")
        
        rec_new = copy.deepcopy(rec)
        adjust_placement_target_if_necessary(rec_new)
        rec_new['sample']['rui_location']['placement'] = \
            self.spatial_placement_manager.placement_relative_to_target(target_iri, rec['sample']['rui_location'])
        logger.debug(f"Creating sql upsert placement relative to body with placement: {rec_new}")
        return self.create_sample_rec_sql_upsert(target_iri, rec_new)

    # Used by: "POST /point-search
    def find_relative_to_spatial_entry_iri_within_radius_from_point(self,
                                                                    spatial_entry_iri: str,
                                                                    radius: float,
                                                                    x: float, y: float, z: float
                                                                    ) -> List[int]:
        sql: str =\
            f"""SELECT sample_hubmap_id FROM {self.table}
            WHERE relative_spatial_entry_iri = %(spatial_entry_iri)s
            AND ST_3DDWithin(sample_geom, ST_GeomFromText('POINTZ(%(x)s %(y)s %(z)s)'), %(radius)s);
            """
        return self.postgresql_manager.select(sql, {
            'spatial_entry_iri': spatial_entry_iri,
            'radius': radius,
            'x': x, 'y': y, 'z': z
        })

    def hubmap_id_sample_rui_location(self,
                                      sample_hubmap_id: str,
                                      relative_spatial_entry_iri=None
                                      ) -> dict:
        sql: str =\
            f"""SELECT sample_rui_location FROM {self.table}
            WHERE sample_hubmap_id = %(sample_hubmap_id)s
            """
        if relative_spatial_entry_iri is not None:
            sql += " AND relative_spatial_entry_iri = %(relative_spatial_entry_iri)s"
        sql += ';'
        recs: List[str] = self.postgresql_manager.select(sql, {
            'sample_hubmap_id': sample_hubmap_id,
            'relative_spatial_entry_iri': relative_spatial_entry_iri
        })
        # logger.debug(f"hubmap_id_sample_rui_location; sql: {sql} recs: {recs}")
        if len(recs) == 0:
            abort(json_error(f'The attributes hubmap_id: {sample_hubmap_id}, with'
                             f' relative_spatial_entri_iri: {relative_spatial_entry_iri}'
                             ' has no sample_rui_location geom data',
                             HTTPStatus.NOT_FOUND))
        if len(recs) != 1:
            logger.error(f'Query against a single sample_hubmap_id={sample_hubmap_id} returned multiple rows')
        # logger.debug(f'hubmap_id_sample_rui_location(hubmap_id: {sample_hubmap_id}, relative_spatial_entri_iri: {relative_spatial_entry_iri}) => sample_rui_location: {recs[0]}')
        return json.loads(recs[0])

    # Used by: "POST /spatial-search/hubmap_id"
    def find_relative_to_spatial_entry_iri_within_radius_from_hubmap_id(self,
                                                                        relative_spatial_entry_iri: str,
                                                                        radius: float,
                                                                        hubmap_id: str,
                                                                        cell_type_name=None
                                                                        ) -> List[int]:
        sample_rui_location: dict = self.hubmap_id_sample_rui_location(hubmap_id, relative_spatial_entry_iri)
        sql: str =\
            f"""SELECT sample_hubmap_id
                FROM {self.table}
            """
        if cell_type_name is None:
            sql += "WHERE"
        else:
            sql +=\
                f"""INNER JOIN cell_types
                    ON {self.table}.sample_uuid = cell_types.sample_uuid
                    INNER JOIN cell_annotation_details
                    ON cell_annotation_details.id = cell_types.cell_annotation_details_id
                    WHERE
                    cell_annotation_details.cell_type_name = %(cell_type_name)s
                    AND"""
        sql +=\
            f""" {self.table}.relative_spatial_entry_iri = %(relative_spatial_entry_iri)s
                AND ST_3DDWithin(sample_geom, ST_GeomFromText('POINTZ(%(x)s %(y)s %(z)s)'), %(radius)s);
            """
        logger.debug(f"find_relative_to_spatial_entry_iri_within_radius_from_hubmap_id({relative_spatial_entry_iri}, {radius}, {hubmap_id}, {cell_type_name}): sql: {sql}")
        return self.postgresql_manager.select(sql, {
            'cell_type_name': cell_type_name,
            'relative_spatial_entry_iri': relative_spatial_entry_iri,
            'x': sample_rui_location['x_dimension'],
            'y': sample_rui_location['y_dimension'],
            'z': sample_rui_location['z_dimension'],
            'radius': radius
        })

    # Used by "GET /search/hubmap_id/<id>/radius/<r>/target/<t>"
    def find_within_radius_at_sample_hubmap_id_and_target(self,
                                                          radius: float,
                                                          hubmap_id: str,
                                                          relative_spatial_entry_iri: str
                                                          ) -> List[str]:
        sample_rui_location: dict = \
            self.hubmap_id_sample_rui_location(hubmap_id, relative_spatial_entry_iri)
        sql: str =\
            f"""SELECT sample_hubmap_id FROM {self.table}
            WHERE ST_3DDWithin(sample_geom, ST_GeomFromText('POINTZ(%(x)s %(y)s %(z)s)'), %(radius)s);
            """
        return self.postgresql_manager.select(sql, {
            'radius': radius,
            'x': sample_rui_location['x_dimension'],
            'y': sample_rui_location['y_dimension'],
            'z': sample_rui_location['z_dimension']
        })


# NOTE: When running in a local docker container the tables are created automatically.
if __name__ == '__main__':
    import argparse

    class RawTextArgumentDefaultsHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawTextHelpFormatter
    ):
        pass

    # https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(
        description='Insert organ data into the database',
        formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("-C", '--config', type=str, default='resources/app.local.properties',
                        help='config file to use')
    parser.add_argument('-p', '--polyhedralsurface', type=str,
                        help='output a closed POLYHEDRALSURFACE from the three x y z dimensions given and exit')
    # $ (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/spatial_manager.py -p '10 10 10')

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    manager = SpatialManager(config)

    try:
        if args.polyhedralsurface is not None:
            try:
                xyz_list: List[float] = [float(x) for x in args.polyhedralsurface.split()]
            except ValueError:
                logger.error(f"You must specify 3 (float) dimensions: 'x y z'")
                exit(1)
            if len(xyz_list) != 3:
                logger.error(f"You must specify 3 (float) dimensions: 'x y z'")
                exit(1)
            x: float = xyz_list[0]
            y: float = xyz_list[1]
            z: float = xyz_list[2]
            logger.info(f'Dimensions given are x: {x}, y: {y}, z: {z}')
            print(manager.create_geom_with_dimension(x, y, z))

    finally:
        manager.close()
        logger.info('Done!')
