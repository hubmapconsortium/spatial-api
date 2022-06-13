import logging
from typing import List
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.manager.spatial_manager import SpatialManager
import configparser
import math
import json

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

        sample_rui_location: dict = \
            self.spatial_manager.hubmap_id_sample_rui_location(sample_hubmap_id, relative_spatial_entry_iri)
        self.p: Point3D = self.centroid_from_sample_rui_location(sample_rui_location)

        self.distances: List[dict] = self.build_distance_for_all_hubmap_ids(relative_spatial_entry_iri)

    def close(self) -> None:
        logger.info(f'{self.__class__.__name__}: Closing connection to PostgreSQL and Spatial Manager')
        self.postgresql_manager.close()
        self.spatial_manager.close()


    def centroid_from_sample_rui_location(self,
                                          sample_rui_location: dict
                                          ) -> Point3D:
        placement: dict = sample_rui_location['placement']
        return Point3D(
            sample_rui_location['x_dimension']/2 + placement['x_translation'],
            sample_rui_location['y_dimension']/2 + placement['y_translation'],
            sample_rui_location['z_dimension']/2 + placement['z_translation']
        )

    def distance_from_sample_rui_location(self,
                                          sample_rui_location: dict
                                          ) -> float:
        p: Point3D = self.centroid_from_sample_rui_location(sample_rui_location)
        return math.sqrt((self.p.x - p.x) ** 2 + (self.p.y - p.y) ** 2 + (self.p.z - p.z) ** 2)

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
            # import pdb; pdb.set_trace();
            distances.append({
                'sample_hubmap_id': sample_hubmap_id,
                'distance': self.distance_from_sample_rui_location(sample_rui_location)})
        return distances

    def hubmap_ids_within_radius_of_centroid(self,
                                             radius: float,
                                             ) -> List[str]:
        hubmap_ids: List[str] = []
        for d in self.distances:
            if d['distance'] <= radius:
                hubmap_ids.append(d['sample_hubmap_id'])
        return hubmap_ids


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
    parser.add_argument('-i', '--sample_hubmap_id', type=str, default='HBM795.TSPP.994',
                        help='usd the centroid of this hubmap_id as the point to search from')
    parser.add_argument("-s", "--relative_spatial_entry_iri", type=str, default='VHMale',
                        help='the body associated with the sample_hubmap_id')
    # parser.add_argument('-t', '--cell_type', type=str, default='Connecting Tubule',
    #                     help='only consider hubmap_ids that have a sample with this cell type')
    parser.add_argument('-r', '--radius', type=float, default=100.0,
                        help='radius to search within the centroid of the hubmap_id given')

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read('resources/app.local.properties')
    manager = Geom(config, args.sample_hubmap_id, args.relative_spatial_entry_iri)

    should_find_sample_hubmap_ids: List[str] =\
        manager.hubmap_ids_within_radius_of_centroid(args.radius)

    found_sample_hubmap_ids: List[str] =\
        manager.spatial_manager.find_relative_to_spatial_entry_iri_within_radius_from_point(
            args.relative_spatial_entry_iri, args.radius, manager.p.x, manager.p.y, manager.p.z)

    logger.info(f"Should find {len(should_find_sample_hubmap_ids)} sample_hubmap_ids: {', '.join(should_find_sample_hubmap_ids)}")
    logger.info(f"Fond in search {len(found_sample_hubmap_ids)} sample_hubmap_ids: {', '.join(found_sample_hubmap_ids)}")
    not_in_both = set(should_find_sample_hubmap_ids) ^ set(found_sample_hubmap_ids)
    logger.info(f"Not in both: {', '.join(not_in_both)}")
    for sample_hubmap_id in not_in_both:
        sample_rui_location: dict = \
            manager.spatial_manager.hubmap_id_sample_rui_location(sample_hubmap_id, args.relative_spatial_entry_iri)
        distance: float = manager.distance_from_sample_rui_location(sample_rui_location)
        logger.info(f"sample_hubmap_id: {sample_hubmap_id} distance: {distance}")

    logger.info("Done!")

    manager.close()
