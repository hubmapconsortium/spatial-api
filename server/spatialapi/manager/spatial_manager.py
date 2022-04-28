import logging
from typing import List
from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager
import json
import configparser

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class SpatialManager(object):

    def __init__(self, config):
        spatial_config = config['spatial']
        self.table = spatial_config.get('Table')
        self.neo4j_manager = Neo4jManager(config)
        self.postgresql_manager = PostgresqlManager(config)
        logger.info(f'SpatialManager: Table: {self.table}')

    def close(self):
        logger.info(f'Neo4jManager: Closing connection to Neo4J & PostgreSQL')
        self.neo4j_manager.close()
        self.postgresql_manager.close()

    def create_YZ_plane_at_X(self, xyz: dict) -> str:
        return f"((" \
               f"{xyz['x']} {-xyz['y']} {-xyz['z']}, " \
               f"{xyz['x']} {-xyz['y']} {xyz['z']}, " \
               f"{xyz['x']} {xyz['y']} {xyz['z']}, " \
               f"{xyz['x']} {xyz['y']} {-xyz['z']}, " \
               f"{xyz['x']} {-xyz['y']} {-xyz['z']}" \
               f"))"

    def create_XY_plane_at_Z(self, xyz: dict) -> str:
        # f"((-5 -5 -5, 5 -5 -5, 5 5 -5, -5 5 -5, -5 -5 -5))," \
        return f"((" \
               f"{-xyz['x']} {-xyz['y']} {xyz['z']}, " \
               f"{-xyz['x']} {xyz['y']} {xyz['z']}, " \
               f"{xyz['x']} {xyz['y']} {xyz['z']}, " \
               f"{xyz['x']} {-xyz['y']} {xyz['z']}, " \
               f"{-xyz['x']} {-xyz['y']} {xyz['z']}" \
               f"))"

    def create_XZ_plane_at_Y(self, xyz: dict) -> str:
        return f"((" \
               f"{-xyz['x']} {xyz['y']} {-xyz['z']}, " \
               f"{-xyz['x']} {xyz['y']} {xyz['z']}, " \
               f"{xyz['x']} {xyz['y']} {xyz['z']}, " \
               f"{xyz['x']} {xyz['y']} {-xyz['z']}, " \
               f"{-xyz['x']} {xyz['y']} {-xyz['z']}" \
               f"))"

    # The PostGRIS geometry should be constructed with the centroid of the object being at POINT(0,0,0)
    def create_multipolygon_geom(self, xyz: dict) -> str:
        return f"'MULTIPOLYGON Z(" \
               f"{self.create_YZ_plane_at_X({'x': -xyz['x']/2, 'y': xyz['y']/2, 'z': xyz['z']/2})}" \
               f",{self.create_YZ_plane_at_X({'x': xyz['x']/2, 'y': xyz['y']/2, 'z': xyz['z']/2})}" \
               f",{self.create_XZ_plane_at_Y({'x': xyz['x']/2, 'y': -xyz['y']/2, 'z': xyz['z']/2})}" \
               f",{self.create_XZ_plane_at_Y({'x': xyz['x']/2, 'y': xyz['y']/2, 'z': xyz['z']/2})}" \
               f",{self.create_XY_plane_at_Z({'x': xyz['x']/2, 'y': xyz['y']/2, 'z': -xyz['z']/2})}" \
               f",{self.create_XY_plane_at_Z({'x': xyz['x']/2, 'y': xyz['y']/2, 'z': xyz['z']/2})}" \
               f" )'"

    def create_geometry(self, rec: dict) -> str:
        geom: str = self.create_multipolygon_geom(rec['dimension']['value'])
        return "ST_Translate(" \
               "ST_Scale(" \
               "ST_RotateZ(ST_RotateY(ST_RotateX(" \
               f"ST_GeomFromText({geom})," \
               f" {rec['rotation']['value']['x']}), {rec['rotation']['value']['y']}), {rec['rotation']['value']['z']})," \
               f" {rec['scaling']['value']['x']}, {rec['scaling']['value']['y']}, {rec['scaling']['value']['z']})," \
               f" {rec['translation']['value']['x']}, {rec['translation']['value']['y']}, {rec['translation']['value']['z']})"

    def create_sql_insert(self, rec: dict) -> str:
        return f"INSERT INTO {self.table} (uuid, hubmap_id, organ_uuid, organ_code, donor_uuid, donor_sex, geom_data, geom)" \
               " VALUES (" \
               f"'{rec['uuid']}', '{rec['hubmap_id']}', " \
               f"'{rec['organ']['uuid']}', '{rec['organ']['code']}', " \
               f"'{rec['donor']['uuid']}', '{rec['donor']['sex']}', " \
               f"'{json.dumps(rec['spatial_data'])}', {self.create_geometry(rec['spatial_data'])}" \
               f")" \
               f" RETURNING id;"

    def insert_rec(self, rec) -> None:
        sql: str = self.create_sql_insert(rec)
        id: int = self.postgresql_manager.insert(sql)
        logger.info(f"Inserting geom record as; id={id}")

    def insert_organ_data(self, organ: str) -> None:
        logger.info(f"Inserting data for organ: {organ}")
        recs: List[dict] = self.neo4j_manager.query_organ(organ)
        for rec in recs:
            self.insert_rec(rec)

    def find_within_radius_at_origin(self, radius: float, origin: dict) -> List[int]:
        sql: str = f"""SELECT hubmap_id FROM {self.table}
        WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ({origin['x']} {origin['y']} {origin['z']})'), {radius});
        """
        return self.postgresql_manager.select(sql)

    def find_within_radius_at_hubmap_id(self, radius: float, hubmap_id: str) -> List[int]:
        sql: str = f"""SELECT geom_data FROM {self.table}
        WHERE hubmap_id = '{hubmap_id}';
        """
        recs: List[str] = self.postgresql_manager.select(sql)
        if len(recs) != 1:
            logger.error(f'Query against a single hubmap_id={hubmap_id} did not return just one item.')
            return []
        geom_data: str = json.loads(recs[0])
        return self.find_within_radius_at_origin(radius, geom_data['translation']['value'])


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
