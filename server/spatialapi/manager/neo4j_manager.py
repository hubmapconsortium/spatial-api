import neo4j
import logging
import json
from ast import literal_eval
from typing import List

logger = logging.getLogger(__name__)


cypher_common_match: str = \
    "MATCH (dn:Donor)-[:ACTIVITY_INPUT]->(:Activity)-[:ACTIVITY_OUTPUT]->(o:Sample {specimen_type:'organ'})-[*]->(s:Sample)"

cypher_common_where: str = \
    " WHERE exists(s.rui_location) AND trim(s.rui_location) <> ''"

# If changing this, also change "process_record()" which repackages this information into a dict...
cypher_common_return: str = \
    " RETURN distinct s.uuid as sample_uuid, s.hubmap_id AS sample_hubmap_id," \
    " s.rui_location as sample_rui_location, s.specimen_type as sample_specimen_type," \
    " s.last_modified_timestamp as sample_last_modified_timestamp," \
    " dn.uuid as donor_uuid, dn.metadata as donor_metadata," \
    " o.uuid as organ_uuid, o.organ as organ_code"


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
        if self.driver is not None:
            logger.info(f'Neo4jManager: Closing connection to Neo4J')
            self.driver.close()
            self.driver = None

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
                logger.error(f"Error there is no donor_metadata for record with sample_hubmap_id: {record['sample_hubmap_id']}")
                return None
            donor_metadata = donor_metadata.replace("'", '"')
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
                logger.error(f'Error literal_eval parsing: {record}; error: {e}')
                return None

            if rui_location_json['@type'] != 'SpatialEntity' and \
                    rui_location_json['placement']['@type'] != 'SpatialPlacement':
                logger.error(f'Error @type is not SpatialEntry, or placement.@type is not SpatialPlacement: {record}')
                return None

            sample: dict = {
                'uuid': record.get('sample_uuid'),
                'hubmap_id': record.get('sample_hubmap_id'),
                'specimen_type': record.get('sample_specimen_type'),
                'last_modified_timestamp': record.get('sample_last_modified_timestamp'),
                'rui_location': rui_location_json
            }
            rec: dict = {
                'sample': sample,
                'organ': organ,
                'donor': donor
            }
            return rec
        except KeyError as e:
            logger.error(f"Key error: {e}")
            return None

    def query_with_cypher(self, cypher: str) -> List[dict]:
        recs: List[dict] = []
        results_n: int = 0
        bad_parse_n: int = 0
        with self.driver.session() as session:
            results: neo4j.Result = session.run(cypher)
            for record in results:
                processed_rec: dict = self.process_record(record)
                #import pdb; pdb.set_trace()
                if processed_rec is not None:
                    recs.append(processed_rec)
                    results_n = results_n + 1
                else:
                    bad_parse_n = bad_parse_n + 1
        logger.info(f'results: {results_n}; Parse Errors: {bad_parse_n}')
        return recs

    def query_all(self) -> List[dict]:
        cypher: str = \
            cypher_common_match + cypher_common_where + cypher_common_return
        return self.query_with_cypher(cypher)

    def query_organ(self, organ: str) -> List[dict]:
        cypher: str = \
            cypher_common_match + cypher_common_where + f" AND o.organ = '{organ}'" + cypher_common_return
        return self.query_with_cypher(cypher)

    def query_sample_uuid(self, sample_uuid: str) -> List[dict]:
        cypher: str =\
            cypher_common_match + cypher_common_where + f" AND s.uuid = '{sample_uuid}'" + cypher_common_return
        return self.query_with_cypher(cypher)

    def retrieve_datasets_that_have_rui_location_information_for_sample_uuid(self, sample_uuid: str) -> List[dict]:
        datasets: List[dict] = []
        # Note: ds.data_types is actually a string pretending to be a list.
        cypher: str = \
            cypher_common_match + cypher_common_where + f" AND s.uuid = '{sample_uuid}'" \
            " OPTIONAL MATCH (ds:Dataset)<-[*]-(s)" \
            " WHERE (ds.data_types CONTAINS 'salmon_rnaseq_snareseq'" \
            " OR ds.data_types CONTAINS 'salmon_sn_rnaseq_10x'" \
            " OR ds.data_types CONTAINS 'salmon_rnaseq_slideseq')" \
            " AND ds.status IN ['QA', 'Published']" \
            " RETURN DISTINCT ds.uuid AS ds_uuid, ds.last_modified_timestamp as ds_last_modified_timestamp"
        with self.driver.session() as session:
            results: neo4j.Result = session.run(cypher)
            for result in results:
                ds_uuid: str = result.get('ds_uuid')
                if ds_uuid is not None:
                    datasets.append({'uuid': ds_uuid, 'last_modified_timestamp': result.get('ds_last_modified_timestamp')})
        if len(datasets) == 0:
            logger.info('retrieve_datasets_that_have_rui_location_information_for_sample_uuid:'
                        f' ZERO datasets found for sample_uuid {sample_uuid}')
        return datasets
