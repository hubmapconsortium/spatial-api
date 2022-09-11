import logging
from typing import List
from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.manager.spatial_placement_manager import SpatialPlacementManager
from flask import abort
from spatialapi.utils import json_error
from http import HTTPStatus
import json
import configparser
import random

logger = logging.getLogger(__name__)


class SpatialManager(object):

    def __init__(self, config):
        self.neo4j_manager = Neo4jManager(config)
        self.postgresql_manager = PostgresqlManager(config)
        self.spatial_placement_manager = SpatialPlacementManager(config)

        spatial_config = config['spatial']
        self.table = spatial_config.get('Table')
        logger.info(f'{self.__class__.__name__}: Table: {self.table}')

    def close(self):
        logger.info(f'Neo4jManager: Closing connection to Neo4J & PostgreSQL')
        self.neo4j_manager.close()
        self.postgresql_manager.close()

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

    def create_sql_upsert(self, target_iri: str, rec: dict) -> str:
        organ_uuid: str = rec['organ']['uuid']
        organ_code: str = rec['organ']['code']
        donor_uuid: str = rec['donor']['uuid']
        donor_sex: str = rec['donor']['sex']
        sample_uuid: str = rec['sample']['uuid']
        sample_hubmap_id: str = rec['sample']['hubmap_id']
        sample_specimen_type: str = rec['sample']['specimen_type']
        sample_rui_location: str = json.dumps(rec['sample']['rui_location'])
        sample_geom: str = self.create_geometry(rec['sample']['rui_location'])
        return f"INSERT INTO {self.table}" \
               " (organ_uuid, organ_code, donor_uuid, donor_sex, relative_spatial_entry_iri, sample_uuid," \
               " sample_hubmap_id, sample_specimen_type, sample_rui_location, sample_geom)" \
               " VALUES (" \
               f"'{organ_uuid}', '{organ_code}', '{donor_uuid}', '{donor_sex}', '{target_iri}', '{sample_uuid}'," \
               f" '{sample_hubmap_id}', '{sample_specimen_type}', '{sample_rui_location}', {sample_geom}" \
               ")" \
               " ON CONFLICT ON CONSTRAINT sample_relative_spatial_entry_sample_uuid_key DO UPDATE SET" \
               f" organ_uuid = '{organ_uuid}', organ_code = '{organ_code}', donor_uuid = '{donor_uuid}'," \
               f" donor_sex = '{donor_sex}', sample_hubmap_id = '{sample_hubmap_id}'," \
               f" sample_specimen_type = '{sample_specimen_type}', sample_rui_location = '{sample_rui_location}'," \
               f" sample_geom = {sample_geom}" \
               " RETURNING id;"

    def upsert_rec(self, target_iri: str, rec: dict) -> None:
        sql_insert_statement: str = self.create_sql_upsert(target_iri, rec)
        id: int = self.postgresql_manager.insert(sql_insert_statement)
        logger.info(f"Inserting geom record as; id={id}")

    # def upsert_rec(self, target_iri: str, rec: dict) -> None:
    #     self.postgresql_manager.add_sample(
    #         rec['organ']['uuid'], rec['organ']['code'], rec['donor']['uuid'], rec['donor']['sex'],
    #         target_iri, rec['sample']['uuid'], rec['sample']['hubmap_id'], rec['sample']['specimen_type'],
    #         json.dumps(rec['sample']['rui_location']),
    #         self.create_geometry(rec['sample']['rui_location'])
    #     )
    #     logger.info(f"Inserting sample record")

    def insert_rec_with_placement_at_target(self, target: str, rec: dict) -> None:
        placement: dict = \
            self.spatial_placement_manager.placement_relative_to_target(target, rec['sample']['rui_location'])
        rec['sample']['rui_location']['placement'] = placement
        self.upsert_rec(target, rec)

    # With patch to fix RUI 0.5 Kidney and Spleen Placements found at:
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
            # TODO: Need only one line per sample, so the geom data should be normalized.
            self.upsert_rec(rec['organ']['code'], rec)
            self.insert_rec_relative_to_spatial_entry_iri(rec)

    def upsert_sample_uuid_data(self, sample_uuid: str) -> None:
        logger.info(f"Upserting data for sample uuid: {sample_uuid}")
        recs: List[dict] = self.neo4j_manager.query_sample_uuid(sample_uuid)
        if len(recs) == 0:
            abort(json_error(f'The Neo4J query for the sample uuid ({sample_uuid}) returned no results', HTTPStatus.NOT_FOUND))
        if len(recs) > 1:
            abort(json_error(f'The Neo4J query for the sample uuid ({sample_uuid}) returned multiple entries', HTTPStatus.CONFLICT))
        rec: dict = recs[0]
        self.upsert_rec(rec['organ']['code'], rec)
        self.insert_rec_relative_to_spatial_entry_iri(rec)

    def find_within_radius_at_origin(self, radius: float, x: float, y: float, z: float) -> List[str]:
        sql: str =\
            f"""SELECT sample_hubmap_id FROM {self.table}
            WHERE ST_3DDWithin(sample_geom, ST_GeomFromText('POINTZ(%(x)s %(y)s %(z)s)'), %(radius)s);
            """
        return self.postgresql_manager.select(sql, {
            'radius': radius,
            'x': x, 'y': y, 'z': z
        })

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
        #logger.debug(f"hubmap_id_sample_rui_location; sql: {sql} recs: {recs}")
        if len(recs) == 0:
            abort(json_error(f'The attributes hubmap_id: {sample_hubmap_id}, with relative_spatial_entri_iri: {relative_spatial_entry_iri} has no sample_rui_location geom data', HTTPStatus.NOT_FOUND))
        if len(recs) != 1:
            logger.error(f'Query against a single sample_hubmap_id={sample_hubmap_id} returned multiple rows')
        #logger.debug(f'hubmap_id_sample_rui_location(hubmap_id: {sample_hubmap_id}, relative_spatial_entri_iri: {relative_spatial_entry_iri}) => sample_rui_location: {recs[0]}')
        return json.loads(recs[0])

    def list_to_rec_for_debugging(self, l: list) -> dict:
        rec: dict = {}
        rec['id'] = l[0]
        rec['organ'] = {}
        rec['organ']['uuid'] = l[1]
        rec['organ']['code'] = l[2]
        rec['donor'] = {}
        rec['donor']['uuid'] = l[3]
        rec['donor']['sex'] = l[4]
        rec['relative_spatial_entry_iri'] = l[5]
        rec['sample'] = {}
        rec['sample']['uuid'] = l[6]
        rec['sample']['hubmap_id'] = l[7]
        rec['sample']['specimen_type'] = l[8]
        rec['sample']['rui_location'] = json.loads(l[9])
        rec['sample']['geom'] = l[10]
        return rec

    def sample_geome_of_id_as_text(self, id: str) -> str:
        sql: str = \
            f"""SELECT ST_AsText(sample_geom) as sample_geom_text
             FROM {manager.table}
             WHERE id = %(id)s;
            """
        recs: List[str] = self.postgresql_manager.select(sql, {'id': id})
        return recs[0]

    def geometry_as_text(self, geometry: str) -> str:
        sql: str = \
            f"""SELECT ST_AsText('{geometry}') as sample_geom_text;
            """
        recs: List[str] = self.postgresql_manager.select(sql)
        return recs[0]

    def text_as_geometry(self, text: str) -> str:
        sql: str = \
            f"""SELECT ST_GeomFromText({text}) as sample_geom_text;
            """
        recs: List[str] = self.postgresql_manager.select(sql)
        return recs[0]

    def geom_check(self, id: int = None) -> None:
        logger.info(f'Determine if geometries are: closed, solids, and have the correct volume...')
        # NOTE: ST_IsValid(sample_geom) does not support POLYHEDRALSURFACE.
        sql: str = 'SELECT' \
                   ' sample_hubmap_id, sample_rui_location, ST_IsClosed(sample_geom),' \
                   ' ST_Volume(sample_geom), ST_3DArea(sample_geom), ST_IsSolid(sample_geom)' \
                   f' FROM {self.table}'
        if id is not None:
            sql += f' WHERE id = %(id)s'
            logger.info(f'Checking geometry with id = {id}.')
        else:
            logger.info('Checking all geometries.')
        sql += ';'
        results: list = self.postgresql_manager.select_all(sql, {'id': id})
        logger.info(f'Checking {len(results)} geometries!')
        for result in results:
            sample_hubmap_id: str = result[0]
            sample_rui_location: dict = json.loads(result[1])
            placement: dict = sample_rui_location['placement']
            sample_rui_location_volume: float = \
                sample_rui_location["x_dimension"] * placement['x_scaling'] \
                * sample_rui_location["y_dimension"] * placement['y_scaling'] \
                * sample_rui_location["z_dimension"] * placement['z_scaling']
            sample_rui_location_volume = round(sample_rui_location_volume, 0)
            is_closed: str = result[2]
            # ST_Volume — Computes the volume of a 3D solid. If applied to surface (even closed) geometries will return 0.
            st_volume: float = round(float(result[3]), 0)
            # ST_3DArea — Computes area of 3D surface geometries. Will return 0 for solids.
            st_3darea: float = result[4]
            if is_closed is not True:
                logger.error(f'The sample_geom for sample_hubmap_id: {sample_hubmap_id}; IS NOT CLOSED!')
            if sample_rui_location_volume != st_volume:
                logger.error(
                    f'The sample_geom for sample_hubmap_id: {sample_hubmap_id}; sample_rui_location_volume:{sample_rui_location_volume} != st_volume:{st_volume}')
            # https://access.crunchydata.com/documentation/postgis/3.2.1/ST_3DArea.html
            # ST_3DArea — Computes area of 3D surface geometries. Will return 0 for solids.
            if st_3darea != 0:
                logger.error(f'The sample_geom for sample_hubmap_id: {sample_hubmap_id}; ST_3DArea should return 0 for solids!')

    # There is an error generated when trying go shrink after enlarging
    # Solid is invalid : PolyhedralSurface (shell) 0 is invalid: Polygon 0 is invalid: points don't lie in the same plane
    # This is likely due to rounding error in the scaling.
    # Because translation is additive, this would likely work for that.
    # NOTE: The inverse of scaling_factor == 10.0 is 0.1 and not -10.0
    def modify_and_check_sample_id(self, id: int, scaling_factor: int = 10.0):
        sql_id: str = f"""SELECT * from {manager.table} WHERE id = %(id)s;"""
        recs: List[str] = manager.postgresql_manager.select_all(sql_id, {'id': id})
        rec: dict = manager.list_to_rec_for_debugging(recs[0])
        donor_sex: str = rec['donor']['sex']
        if rec['donor']['sex'] == 'male':
            rec['donor']['sex'] = 'female'
        else:
            rec['donor']['sex'] = 'male'
        # Scale the sample by 10x so that we can see the difference with QGIS...
        placement: dict = rec['sample']['rui_location']['placement']
        placement['x_scaling'] *= scaling_factor
        placement['y_scaling'] *= scaling_factor
        placement['z_scaling'] *= scaling_factor
        manager.upsert_rec(rec['relative_spatial_entry_iri'], rec)
        recs2: List[str] = manager.postgresql_manager.select_all(sql_id, {'id': id})
        rec2: dict = manager.list_to_rec_for_debugging(recs2[0])
        if rec['sample']['geom'] == rec2['sample']['geom']:
            logger.error(f"The geometry should have changed????")
        if donor_sex == rec2['donor']['sex']:
            logger.error(f"The donor sex should have changed????")
        manager.geom_check(rec['id'])


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


    def find_within_radius_at_sample_hubmap_id_and_target(self,
                                                          radius: float,
                                                          hubmap_id: str,
                                                          relative_spatial_entry_iri: str
                                                          ) -> List[str]:
        sample_rui_location: dict = \
            self.hubmap_id_sample_rui_location(hubmap_id, relative_spatial_entry_iri)
        return self.find_within_radius_at_origin(radius,
                                                 sample_rui_location['x_dimension'],
                                                 sample_rui_location['y_dimension'],
                                                 sample_rui_location['z_dimension'])


# NOTE: When running in a local docker container the tables are created automatically.
# TODO: Nothing is being done with units.
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
    parser.add_argument("-m", "--sample_modify", action="store_true",
                        help='modify a sample that is currently in the database and exit')
    parser.add_argument("-S", "--scaling_factor", type=float, default=10.0,
                        help='modify a sample that is currently in the database by applying this scaling factor to it and exit')
    parser.add_argument('-i', '--sample_id', type=int,
                        help='choose this sample id for the test')
    parser.add_argument('-u', '--update_sample_uuid', type=str,
                        help='update the given sample_uuid data in the PostgreSQL database from a Neo4J query')

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    manager = SpatialManager(config)

    try:
        if args.sample_modify is True:
            if args.sample_id is not None:
                id: int = args.sample_id
            else:
                sql_count: str = f"""SELECT count(*) from {manager.table};"""
                recs: List[str] = manager.postgresql_manager.select(sql_count)
                id = random.randint(0, recs[0]-1)+1
            manager.modify_and_check_sample_id(id, args.scaling_factor)
            #import pdb;pdb.set_trace();

        # Same as the MSAPI call found in server/spatialapi/sample_update_uuid
        elif args.update_sample_uuid is not None:
            manager.upsert_sample_uuid_data(args.update_sample_uuid)

        elif args.polyhedralsurface is not None:
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

        else:
            # Rather than using RK use the UBERON number. If there is no UBERON number it doesn't exist yet.
            # RK:
            # description: Kidney (Right)
            # iri: http://purl.obolibrary.org/obo/UBERON_0004539
            # https://raw.githubusercontent.com/hubmapconsortium/search-api/master/src/search-schema/data/definitions/enums/organ_types.yaml
            manager.insert_organ_data('RK')
            manager.insert_organ_data('LK')
    finally:
        manager.close()
        logger.info('Done!')
