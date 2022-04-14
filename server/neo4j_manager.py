import neo4j
import configparser
import logging
from ast import literal_eval
from typing import List

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jManager(object):

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('resources/app.properties')
        neo4j_config = config['neo4j']
        server: str = neo4j_config.get('Server')
        username: str = neo4j_config.get('Username')
        password: str = neo4j_config.get('Password')
        logger.info(f'Username: {username} Password: {password} Server: {server}')
        self.driver = neo4j.GraphDatabase.driver(server, auth=(username, password))

    # https://neo4j.com/docs/api/python-driver/current/api.html
    def close(self):
        self.driver.close()

    @staticmethod
    def process_record(record: dict) -> dict:
        try:
            uuid: str = record.get('uuid')
            hubmap_id: str = record.get('hubmap_id')
            organ: dict = {'organ': record.get('organ'), 'uuid': record.get('organ_uuid')}
            try:
                rui_location: str = record.get('rui_location')
                rui_location_json: dict = literal_eval(rui_location)
            except (SyntaxError, ValueError) as e:
                logger.info(f'Error literal_eval parsing: {record}')
                return None

            if rui_location_json['@type'] != 'SpatialEntity' and \
                    rui_location_json['placement']['@type'] != 'SpatialPlacement':
                logger.info(f'Error @type is not SpatialEntry, or placement.@type is not SpatialPlacement: {record}')
                return None
            spatial_data: dict = {
                'target': rui_location_json['placement']['target'],
                'dimension': {
                    'value': {
                        'x': rui_location_json['x_dimension'],
                        'y': rui_location_json['y_dimension'],
                        'z': rui_location_json['z_dimension']
                    },
                    'units': rui_location_json['dimension_units']
                },
                'scaling': {
                    'value': {
                        'x': rui_location_json['placement']['x_scaling'],
                        'y': rui_location_json['placement']['y_scaling'],
                        'z': rui_location_json['placement']['z_scaling']
                    },
                    'units': rui_location_json['placement']['scaling_units']
                },
                'rotation': {
                    'value': {
                        'x': rui_location_json['placement']['x_rotation'],
                        'y': rui_location_json['placement']['y_rotation'],
                        'z': rui_location_json['placement']['z_rotation']
                    },
                    'units': rui_location_json['placement']['rotation_units']
                },
                'translation': {
                    'value': {
                        'x': rui_location_json['placement']['x_translation'],
                        'y': rui_location_json['placement']['y_translation'],
                        'z': rui_location_json['placement']['z_translation']
                    },
                    'units': rui_location_json['placement']['translation_units']
                },
            }
            rec: dict = {'uuid': uuid, 'hubmap_id': hubmap_id, 'spatial_data': spatial_data, 'organ': organ}
            return rec
        except KeyError:
            return None

    def query_with_cypher(self, cypher: str) -> List[dict]:
        recs: List[dict] = []
        results_n: int = 0
        bad_parse_n: int = 0
        with self.driver.session() as session:
            results: neo4j.Result = session.run(cypher)
            for record in results:
                # import pdb; pdb.set_trace()
                results_n = results_n + 1
                processed_rec: dict = self.process_record(record)
                if processed_rec is not None:
                    recs.append(processed_rec)
                else:
                    bad_parse_n = bad_parse_n + 1
        logger.info(f'results: {results_n}; Parse Errors: {bad_parse_n}')
        return recs

    def query_all(self) -> List[dict]:
        cypher: str =\
            "MATCH (s:Sample)<-[*]-(organ:Sample {specimen_type:'organ'})" \
            " WHERE exists(s.rui_location) AND s.rui_location <> ''" \
            " RETURN s.uuid AS uuid, s.hubmap_id AS hubmap_id, s.specimen_type AS specimen_type," \
            " organ.organ AS organ_name, organ.uuid AS organ_uuid, s.rui_location AS rui_location"
        return self.query_with_cypher(cypher)

    def query_organ(self, organ):
        cypher: str =\
            "MATCH (s:Sample)<-[*]-(organ:Sample {specimen_type:'organ'})" \
            f" WHERE exists(s.rui_location) AND s.rui_location <> '' AND organ.organ = '{organ}'" \
            " RETURN s.uuid AS uuid, s.hubmap_id AS hubmap_id, s.specimen_type AS specimen_type," \
            " organ.organ AS organ, organ.uuid AS organ_uuid, s.rui_location AS rui_location"
        return self.query_with_cypher(cypher)

    def query_right_kidney(self) -> List[dict]:
        return self.query_organ('RK')


if __name__ == '__main__':
    manager = Neo4jManager()
    recs: List[dict] = manager.query_right_kidney()
    import pdb; pdb.set_trace()
    manager.close()
