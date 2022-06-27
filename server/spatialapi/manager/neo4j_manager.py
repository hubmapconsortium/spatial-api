import neo4j
import logging
import json
from ast import literal_eval
from typing import List

logger = logging.getLogger(__name__)


class Neo4jManager(object):

    def __init__(self, config):
        neo4j_config = config['neo4j']
        server: str = neo4j_config.get('Server')
        username: str = neo4j_config.get('Username')
        password: str = neo4j_config.get('Password')
        logger.info(f'Neo4jManager: Username: {username} Server: {server}')
        # Could throw: neo4j.exceptions.ServiceUnavailable
        self.driver = neo4j.GraphDatabase.driver(server, auth=(username, password))

    # https://neo4j.com/docs/api/python-driver/current/api.html
    def close(self) -> None:
        logger.info(f'Neo4jManager: Closing connection to Neo4J')
        if self.driver is not None:
            self.driver.close()

    def search_organ_donor_data_for_grouping_concept_preferred_term(self,
                                                                    organ_donor_data_list: List[dict],
                                                                    grouping_concept_preferred_term: str) -> str:
        for organ_donor_data in organ_donor_data_list:
            if organ_donor_data["grouping_concept_preferred_term"] == grouping_concept_preferred_term:
                return organ_donor_data["preferred_term"].lower()
        return None

    def process_record(self, record: dict) -> dict:
        try:
            organ: dict = {
                'uuid': record.get('organ_uuid'),
                'code': record.get('organ_code')
            }
            donor_metadata: str = record.get('donor_metadata')
            if donor_metadata is None:
                logger.info(f"Error there is no donor_metadata for record with sample_hubmap_id: {record['sample_hubmap_id']}")
                return None
            organ_donor_data: dict = json.loads(donor_metadata)

            organ_donor_data_list: List[dict] = organ_donor_data['organ_donor_data']
            donor: dict = {
                'uuid': record.get('donor_uuid'),
                'sex': self.search_organ_donor_data_for_grouping_concept_preferred_term(organ_donor_data_list, 'Sex')
            }
            try:
                rui_location: str = record.get('sample_rui_location')
                rui_location_json: dict = literal_eval(rui_location)
            except (SyntaxError, ValueError) as e:
                logger.info(f'Error literal_eval parsing: {record}')
                return None

            if rui_location_json['@type'] != 'SpatialEntity' and \
                    rui_location_json['placement']['@type'] != 'SpatialPlacement':
                logger.info(f'Error @type is not SpatialEntry, or placement.@type is not SpatialPlacement: {record}')
                return None

            sample: dict = {
                'uuid': record.get('sample_uuid'),
                'hubmap_id': record.get('sample_hubmap_id'),
                'specimen_type': record.get('sample_specimen_type'),
                'rui_location': rui_location_json
            }
            rec: dict = {
                'sample': sample,
                'organ': organ,
                'donor': donor
            }
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
                results_n = results_n + 1
                processed_rec: dict = self.process_record(record)
                #import pdb; pdb.set_trace()
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

    def query_organ(self, organ) -> List[dict]:
        # cypher: str =\
        #     "MATCH (s:Sample)<-[*]-(organ:Sample {specimen_type:'organ'})" \
        #     f" WHERE exists(s.rui_location) AND s.rui_location <> '' AND organ.organ = '{organ}'" \
        #     " RETURN s.uuid AS uuid, s.hubmap_id AS hubmap_id, s.specimen_type AS specimen_type," \
        #     " organ.organ AS organ, organ.uuid AS organ_uuid, s.rui_location AS rui_location"
        cypher: str =\
            "MATCH (dn:Donor)-[:ACTIVITY_INPUT]->(:Activity)-[:ACTIVITY_OUTPUT]->(o:Sample {specimen_type:'organ'})-[*]->(s:Sample)" \
            f" WHERE exists(s.rui_location) AND trim(s.rui_location) <> '' AND o.organ = '{organ}'" \
            " RETURN distinct s.uuid as sample_uuid, s.hubmap_id AS sample_hubmap_id, s.rui_location as sample_rui_location, s.specimen_type as sample_specimen_type," \
            " dn.uuid as donor_uuid, dn.metadata as donor_metadata," \
            " o.uuid as organ_uuid, o.organ as organ_code"
        return self.query_with_cypher(cypher)

    def query_cell_types(self) -> List[dict]:
        recs: List[dict] = []
        cypher: str = \
            "MATCH (dn:Donor)-[:ACTIVITY_INPUT]->(:Activity)-[:ACTIVITY_OUTPUT]->(o:Sample {specimen_type:'organ'})-[*]->(s:Sample)" \
            " WHERE NOT s.rui_location IS NULL AND NOT trim(s.rui_location) = '' AND (o.organ = 'LK' or o.organ = 'RK')" \
            " OPTIONAL MATCH (ds:Dataset)<-[*]-(s)" \
            " WHERE (ds.data_types CONTAINS 'salmon_rnaseq_snareseq' OR ds.data_types CONTAINS 'salmon_sn_rnaseq_10x' OR ds.data_types CONTAINS 'salmon_rnaseq_slideseq')" \
            " RETURN DISTINCT s.uuid AS sample_uuid, ds.uuid AS ds_uuid, dn.uuid, dn.metadata, s.rui_location"
        with self.driver.session() as session:
            results: neo4j.Result = session.run(cypher)
            for record in results:
                if record.get('ds_uuid') is not None:
                    processed_rec: dict = {
                        # Key into the column sample.sample_uuid
                        'sample_uuid': record.get('sample_uuid'),
                        # Used to get the psc path from the ingest api
                        'ds_uuid': record.get('ds_uuid')
                    }
                    recs.append(processed_rec)
        return recs

    def query_right_kidney(self) -> List[dict]:
        return self.query_organ('RK')
