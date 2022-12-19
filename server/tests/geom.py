import logging
from typing import List
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.manager.spatial_manager import SpatialManager
import configparser
import math
import json
import re

logger = logging.getLogger(__name__)

class Point3D(object):

    def __init__(self, x: float, y: float, z: float):
        self._x = x
        self._y = y
        self._z = z

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def z(self):
        return self._z


class Geom(object):

    def __init__(self, config,
                 sample_hubmap_id: str,
                 relative_spatial_entry_iri=None) -> None:
        self.postgresql_manager = PostgresqlManager(config)
        self.spatial_manager = SpatialManager(config)

        spatial_config = config['spatial']
        self.table = spatial_config.get('Table')
        logger.info(f'{self.__class__.__name__}: Table: {self.table}')

        self.sample_hubmap_id = sample_hubmap_id
        sample_rui_location: dict = \
            self.spatial_manager.hubmap_id_sample_rui_location(sample_hubmap_id, relative_spatial_entry_iri)
        self.p: Point3D = self.centroid_from_sample_rui_location(sample_rui_location)
        logger.info(f'Centroid of sample_rui_location ({sample_rui_location}): {self.p}')

        self.distances: List[dict] = self.build_distance_for_all_hubmap_ids(relative_spatial_entry_iri)

    def close(self) -> None:
        logger.info(f'{self.__class__.__name__}: Closing connection to PostgreSQL and Spatial Manager')
        self.postgresql_manager.close()
        self.spatial_manager.close()

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

    # Since the object is created with its centroid at <0, 0, 0> the only location data that matters is the translation.
    def centroid_from_sample_rui_location(self,
                                          sample_rui_location: dict
                                          ) -> Point3D:
        placement: dict = sample_rui_location['placement']
        return Point3D(
            placement['x_translation'],
            placement['y_translation'],
            placement['z_translation']
            )

    def distance_between_Point3Ds(self, p1: Point3D, p2: Point3D) -> float:
        return math.sqrt(
            (p1.x - p2.x) ** 2 +
            (p1.y - p2.y) ** 2 +
            (p1.z - p2.z) ** 2
            )

    def distance_from_sample_rui_location(self,
                                          sample_rui_location: dict
                                          ) -> float:
        p: Point3D = self.centroid_from_sample_rui_location(sample_rui_location)
        return self.distance_between_Point3Ds(self.p, p)

    def closest_point_distance(self,
                               sample_hubmap_id: str
                               ) -> List[float]:
        # https://postgis.net/docs/ST_3DClosestPoint.html
        sql: str = \
            'WITH' \
            f" s(poly) AS (SELECT sample_geom FROM {self.table} WHERE sample_hubmap_id = %(sample_hubmap_id_a)s)" \
            f", t(poly) AS (SELECT sample_geom FROM {self.table} WHERE sample_hubmap_id = %(sample_hubmap_id_b)s)" \
            " SELECT ST_AsEWKT(ST_3DClosestPoint(s.poly, t.poly))" \
            " FROM s, t;"
        points: list = self.postgresql_manager.select_all(
            sql,
            {'sample_hubmap_id_a': sample_hubmap_id,
             'sample_hubmap_id_b': self.sample_hubmap_id
             })
        distances: List[float] = []
        for point in points:
            pts: list = [float(s) for s in re.findall(r'-?\d+\.?\d*', point[0])]
            p: Point3D = Point3D(pts[0], pts[1], pts[2])
            distances.append(self.distance_between_Point3Ds(self.p, p))
        return distances

    def build_distance_for_all_hubmap_ids(self,
                                          relative_spatial_entry_iri=None
                                          ) -> List[dict]:
        distances: List[dict] = []
        sql: str = \
            f'SELECT sample_hubmap_id, sample_rui_location' \
            f' FROM {self.table}' \
            f' WHERE relative_spatial_entry_iri = %(relative_spatial_entry_iri)s;'
        hubmap_id_locations: list = self.postgresql_manager.select_all(
            sql,
            {'relative_spatial_entry_iri': relative_spatial_entry_iri})
        for hil in hubmap_id_locations:
            sample_hubmap_id: str = hil[0]
            sample_rui_location: dict = json.loads(hil[1])
            distances.append({
                'sample_hubmap_id': sample_hubmap_id,
                'distance': self.distance_from_sample_rui_location(sample_rui_location)
            })
        return distances

    def hubmap_ids_within_radius_of_centroid(self,
                                             radius: float,
                                             ) -> List[str]:
        hubmap_ids: List[str] = []
        for d in self.distances:
            if d['distance'] <= radius:
                hubmap_ids.append(d['sample_hubmap_id'])
        return hubmap_ids

    def distance_check(self, relative_spatial_entry_iri: str, radius: float) -> None:
        # NOTE: Things seem to break between -r 99-167
        logger.info(f">>> Called with; sample_hubmap_id: {self.sample_hubmap_id};"
                    f" relative_spatial_entry_iri: {relative_spatial_entry_iri};"
                    f" radius {radius}")

        should_find_sample_hubmap_ids: List[str] = \
            self.hubmap_ids_within_radius_of_centroid(radius)

        found_sample_hubmap_ids: List[str] = \
            self.spatial_manager.find_relative_to_spatial_entry_iri_within_radius_from_point(
                relative_spatial_entry_iri, radius, self.p.x, self.p.y, self.p.z)
        logger.info(
            f">>> Should find {len(should_find_sample_hubmap_ids)} sample_hubmap_ids: {', '.join(should_find_sample_hubmap_ids)}")
        logger.info(
            f">>> Fond in search {len(found_sample_hubmap_ids)} sample_hubmap_ids: {', '.join(found_sample_hubmap_ids)}")
        not_in_both = set(should_find_sample_hubmap_ids) ^ set(found_sample_hubmap_ids)
        logger.info(f">>> Not in both {len(not_in_both)} sample_hubmap_ids: {', '.join(not_in_both)}")

        for sample_hubmap_id in not_in_both:
            sample_rui_location: dict = \
                self.spatial_manager.hubmap_id_sample_rui_location(sample_hubmap_id, relative_spatial_entry_iri)
            distance: float = self.distance_from_sample_rui_location(sample_rui_location)
            distances: List[float] = self.closest_point_distance(sample_hubmap_id)
            logger.info(f"Distances to sample_hubmap_id: {sample_hubmap_id}: {distances}")
            # import pdb; pdb.set_trace();
            logger.info(
                f"sample_hubmap_id: {sample_hubmap_id} computed distance: {distance} x: {sample_rui_location['x_dimension']} y: {sample_rui_location['y_dimension']} z: {sample_rui_location['z_dimension']}")


# (cd server; export PYTHONPATH=.; python3 ./tests/geom.py -h)
if __name__ == '__main__':
    import argparse

    class RawTextArgumentDefaultsHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawTextHelpFormatter
    ):
        pass

    # https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(
        description='''
Test of geom sample rui location search capabilities.

First find the distance from the centroid of the --sample_hubmap_id given to all other hubmap_ids,
and locate those within the given --radius using the sample_rui_location information.
Next do a PostgreSQL geom search from the centroid of the --sample_hubmap_id given to locate
all hubmap_ids within the given --radius.

Finally, compare the lists returned. ''',
        formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("-C", '--config', type=str, default='resources/app.local.properties',
                        help='config file to use for processing')
    parser.add_argument('-i', '--sample_hubmap_id', type=str, default='HBM795.TSPP.994',
                        help='usd the centroid of this hubmap_id as the point to search from')
    parser.add_argument("-s", "--relative_spatial_entry_iri", type=str, default='VHMale',
                        help='the body associated with the sample_hubmap_id')
    parser.add_argument('-r', '--radius', type=float, default=100.0,
                        help='radius to search within the centroid of the hubmap_id given')
    parser.add_argument("-c", '--geom_check', action="store_true",
                        help='ONLY Determine if ALL geometries are: closed, solids, and have the correct volume...')
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    manager = Geom(config, args.sample_hubmap_id, args.relative_spatial_entry_iri)

    try:
        if args.geom_check:
            manager.geom_check()
        else:
            manager.distance_check(args.relative_spatial_entry_iri, args.radius)
    finally:
        manager.close()
        logger.info('Done!')
