import logging
from typing import List
from neo4j_manager import Neo4jManager
from postgresql_manager import PostgresqlManager

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class SpatialManager(object):

    def __init__(self):
        self.neo4j_manager = Neo4jManager()
        self.postgresql_manager = PostgresqlManager()

    def close(self):
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

    def create_sql_insert(self, table: str, rec: dict) -> str:
        return f"INSERT INTO {table} (uuid, hubmap_id, organ_uuid, organ_organ, geom)" \
               f" VALUES ('{rec['uuid']}', '{rec['hubmap_id']}', '{rec['organ']['uuid']}', '{rec['organ']['organ']}'," \
               f" {self.create_geometry(rec['spatial_data'])})" \
               f" RETURNING id;"

    def insert_organ_data(self, organ: str) -> None:
        recs: List[dict] = self.neo4j_manager.query_organ(organ)
        for rec in recs:
            sql: str = self.create_sql_insert('public.sample', rec)
            id: int = self.postgresql_manager.insert(sql)
            logger.info(f"Inserting geom record as; id={id}")


if __name__ == '__main__':
    manager = SpatialManager()
    manager.insert_organ_data('RK')
    #import pdb; pdb.set_trace()
    manager.close()
