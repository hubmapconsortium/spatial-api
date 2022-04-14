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

    def load_db_all(self) -> List[dict]:
        recs: List[dict] = self.neo4j_manager.query_all()
        for rec in recs:
            self.load_db_record(rec)

    def load_db_organ(self, organ: str):
        recs: List[dict] = self.neo4j_manager.query_organ(organ)
        for rec in recs:
            self.load_db_record(rec)

    def load_db_record(self, record: dict) -> None:
        # A polygon is a representation of an area. The outer boundary of the polygon is represented by a ring.
        # This ring is a linestring that is both closed and simple as defined above.
        # https://postgis.net/docs/PostGIS_Special_Functions_Index.html#PostGIS_3D_Functions
        # https://postgis.net/docs/ST_GeomFromGeoJSON.html

        # https://postgis.net/docs/manual-2.2/using_postgis_dbmanagement.html
        # 4.4.1. Loading Data Using SQL
        # INSERT INTO roads (road_id, roads_geom, road_name)
        #   VALUES (1,ST_GeomFromText('LINESTRING(191232 243118,191108 243242)',-1),'Jeff Rd');
        #
        # 4.5.1. Using SQL to Retrieve Data
        # SELECT road_id, ST_AsText(road_geom) AS geom, road_name FROM roads;
        #
        # Query will use the bounding box of the polygon for comparison purposes:
        # SELECT road_id, road_name FROM roads
        # WHERE roads_geom && ST_GeomFromText('POLYGON((...))',312);
        #
        # 4.6.1. GiST Indexes
        # CREATE INDEX [indexname] ON [tablename] USING GIST ( [geometryfield] );
        #
        # 4.7.1. Taking Advantage of Indexes
        # SELECT the_geom
        # FROM geom_table
        # WHERE ST_Distance(the_geom, ST_GeomFromText('POINT(100000 200000)', 312)) < 100
        pass


if __name__ == '__main__':
    manager = SpatialManager()
    recs: List[dict] = manager.load_db_organ('RK')
    import pdb; pdb.set_trace()
    for rec in recs:
        manager.load_db_record(rec)
    manager.close()