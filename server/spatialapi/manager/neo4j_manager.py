import neo4j
import logging
import json
from ast import literal_eval
from typing import List

logger = logging.getLogger(__name__)

# NOTE: Nothing in this file should modify the Neo4J database

cypher_common_match: str = \
    "MATCH (dn:Donor)-[:ACTIVITY_INPUT]->(:Activity)-[:ACTIVITY_OUTPUT]->(o:Sample {sample_category:'organ'})-[*]->(s:Sample)"

cypher_common_where: str = \
    " WHERE exists(s.rui_location) AND trim(s.rui_location) <> ''"

# If changing this, also change "process_record()" which repackages this information into a dict...
cypher_common_return: str = \
    " RETURN DISTINCT s.uuid as sample_uuid, s.hubmap_id AS sample_hubmap_id," \
    " s.rui_location as sample_rui_location, s.sample_category as sample_sample_category," \
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
                'sample_category': record.get('sample_sample_category'),
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
                # import pdb; pdb.set_trace()
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

    def retrieve_datasets_that_have_rui_location_information_for_sample_uuid(self, sample_uuid=None) -> dict:
        """Return a dictionary of the form:
        {sample_uuid_0: {dataset_uuid_0: dataset_timestamp_0, ..., dataset_uuid_n: dataset_timestamp_n} ...}
        Here the 'sample_uuid' is the key and the value is a dictionary of the form
        key:dataset_uuid, value:dataset_timestamp for each dataset associated with that sample_uuid.
        """
        datasets: dict = {}
        cypher: str = cypher_common_match + cypher_common_where
        if sample_uuid is not None:
            cypher += f" AND s.uuid = '{sample_uuid}'"
        # Using the following to map the old data_types field to the new dataset_type field:
        # MATCH (ds:Dataset) RETURN DISTINCT ds.data_types, ds.dataset_type
        # "['salmon_rnaseq_snareseq']"	"SNARE-seq2 [Salmon]"
        # "['salmon_sn_rnaseq_10x']"	"RNAseq [Salmon]"
        # "['salmon_rnaseq_slideseq']"	"Slide-seq [Salmon]"
        # where the old query contained...
        # "(ds.data_types CONTAINS 'salmon_rnaseq_snareseq'" \
        # " OR ds.data_types CONTAINS 'salmon_sn_rnaseq_10x'" \
        # " OR ds.data_types CONTAINS 'salmon_rnaseq_slideseq')" \
        cypher += \
            " OPTIONAL MATCH (ds:Dataset)<-[*]-(s)" \
            " WHERE" \
            " ds.dataset_type IN ['SNARE-seq2 [Salmon]', 'RNAseq [Salmon]', 'Slide-seq [Salmon]']" \
            " AND ds.status IN ['QA', 'Published']" \
            " RETURN DISTINCT" \
            " s.uuid AS sample_uuid, ds.uuid AS ds_uuid, ds.last_modified_timestamp as ds_last_modified_timestamp"
        logger.debug(f"retrieve_datasets_that_have_rui_location_information_for_sample_uuid({sample_uuid}) : {cypher}")
        with self.driver.session() as session:
            results: neo4j.Result = session.run(cypher)
            for result in results:
                sample_uuid: str = result.get('sample_uuid')
                ds_uuid: str = result.get('ds_uuid')
                ds_last_modified_timestamp: int = result.get('ds_last_modified_timestamp')
                if ds_uuid is not None and ds_last_modified_timestamp is not None:
                    ds_entry: dict = {ds_uuid: ds_last_modified_timestamp}
                    if sample_uuid not in datasets:
                        datasets[sample_uuid] = ds_entry
                    else:
                        ds_entries: dict = datasets.get(sample_uuid)
                        ds_entries.update(ds_entry)
        if len(datasets) == 0:
            logger.info('retrieve_datasets_that_have_rui_location_information_for_sample_uuid:'
                        f' ZERO datasets found for sample_uuid {sample_uuid}')
        return datasets
