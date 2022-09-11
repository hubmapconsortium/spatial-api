import logging
from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.manager.ingest_api_manager import IngestApiManager
from spatialapi.utils.ssh import Ssh
import configparser
import requests
import time
import json
from urllib import parse
from typing import List

logger = logging.getLogger(__name__)


# 1) use the query to get the cell_types data
# In the results of the Neo4J cypher each 'sample_uuid' will be the PostgreSQL 'cell_types.sample_uuid'.
# To resolve each 'ds.uuid' from the results of the Neo4J cypher to the location of a file on the PSC file system
# use the ingest-api call: /datasets/<ds_uuid>/file-system-abs-path
# 2) write a program that aggregates the
# Do all of this work on 'hivevm192.psc.edu' which needs to be accessed through the gateway 'hive.psc.edu' (ssh)
# $ ssh kollar@hive.psc.edu
# $ ssh kollar@hivevm192.psc.edu
class TissueSampleCellTypeManager(object):

    def __init__(self, config):
        self.ingest_api_manager = IngestApiManager(config)
        self.neo4j_manager = Neo4jManager(config)
        self.postgresql_manager = PostgresqlManager(config)
        self.ssh = Ssh(config)

    # https://neo4j.com/docs/api/python-driver/current/api.html
    def close(self) -> None:
        logger.info(f'TissueSampleCellTypeManager: Closing connection to Neo4J, PostgreSQL, and Ssh')
        self.ingest_api_manager.close()
        self.neo4j_manager.close()
        self.postgresql_manager.close()
        self.ssh.close()

    def get_cell_types_data(self, bearer_token: str) -> List[dict]:
        recs: List[dict] = self.neo4j_manager.query_cell_types()
        for rec in recs:
            psc_path: str = self.ingest_api_manager.ds_uuid_to_psc_path(rec['ds_uuid'], bearer_token)
            if psc_path is not None:
                rec['psc_file'] = psc_path+'/secondary_analysis.h5ad'
        return recs

    def process_files_for_sample_uuid(self, bearer_token: str, sample_uuid: str) -> None:
        ds_uuids: List[str] =\
            self.neo4j_manager.retrieve_ds_uuids_with_rui_location_information_for_sample_uuid(sample_uuid)
        # TODO: Delete everything from the 'cell_types' table with this sample_uuid.
        resp_json: dict =\
            self.ingest_api_manager.process_all_ds_uuid_secondary_analysis_files(bearer_token, ds_uuids)
        cell_type_counts: dict = resp_json['cell_type_counts']
        if cell_type_counts is not None:
            for cell_type_name, cell_type_count in cell_type_counts.items():
                self.postgresql_manager.add_cell_type_count(sample_uuid, cell_type_name, cell_type_count)

    def dump_cell_types_data(self, bearer_token: str, json_file: str) -> None:
        cell_types_data: List[dict] = manager.get_cell_types_data(bearer_token)
        with open(json_file, 'w') as f:
            json.dump(cell_types_data, f)

    def build_cell_types_table(self, json_from_psc_file: str) -> List[str]:
        ds_uuid_missing_cell_type_counts: List[str] = []
        input_file = open(json_from_psc_file)
        data_list: List[dict] = json.load(input_file)
        for data in data_list:
            if 'cell_type_counts' in data:
                sample_uuid: str = data['sample_uuid']
                cell_type_counts: dict = data['cell_type_counts']
                for cell_type_name, cell_type_count_str in cell_type_counts.items():
                    cell_type_count = int(cell_type_count_str)
                    self.postgresql_manager.add_cell_type_count(sample_uuid, cell_type_name, cell_type_count)
            else:
                ds_uuid_missing_cell_type_counts.append(data['ds_uuid'])
        return ds_uuid_missing_cell_type_counts

    def get_missing_cell_type_names(self) -> List[str]:
        return self.postgresql_manager.get_missing_cell_type_names()


if __name__ == '__main__':
    import argparse

    class RawTextArgumentDefaultsHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawTextHelpFormatter
    ):
        pass

    # https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(
        description='''Tissue Sample Cell Type Manager
        
Steps:
1) Build the data.json file you will need to run 'tissue_sample_cell_type_manager.py --build_json_token BEARER_TOKEN'
 See the note below for a description of how to get the BEARER_TOKEN
2) To process the data.json file converting it to a data_out.json file; log into the PSC server, and run the following:
$ ssh kollar@hive.psc.edu
$ ssh kollar@hivevm191.psc.edu
$ cd ~/bin/psc
$ ./mkvenv.sh
$ source venv/bin/activate
$ ./test.py
3) To process the data_out.json file you will need to run 'tissue_sample_cell_type_manager.py --process_json'

NOTE: To retrieve the token for the build_json_token:
In Firefox open 'Tools > Browser Tools > Web Developer Tools'.
Login through the UI(https://portal.hubmapconsortium.org/).
In the Web Developer Tools, click on 'Network', and then one of the search endpoints.
Copy the 'Request Header', 'Authoriation : Bearer' token.

UI times-out in 15 min so close the browser window, and the token will last for a day or so.
''',
        formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("-C", '--config', type=str, default='resources/app.local.properties',
                        help='config file to use for processing')
    parser.add_argument("-b", '--build_json_token', type=str,
                        help='build the .json file that is processed at the psc, the value is a bearer token to use for ingest_api endpoint call')
    parser.add_argument("-p", '--process_json', action="store_true",
                        help='process the .json file created at the psc')
    parser.add_argument("-r", "--run_psc", action="store_true",
                        help='run code on the psc')
    # $ (cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/tissue_sample_cell_type_manager.py -d b2362226c142a855ddaa0fba0db29b95 -b )
    parser.add_argument("-d", '--process_data_files_for_sample_id', type=str,
                        help='the sample id or which to process the secondary analysis files')

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    manager = TissueSampleCellTypeManager(config)

    psc_working_dir: str = '~/bin/psc'
    local_working_dir: str = '../scripts/psc'

    try:
        if args.process_data_files_for_sample_id is not None and args.build_json_token is not None:
            sample_uuid: str = args.process_data_files_for_sample_id
            bearer_token: str = args.build_json_token
            logger.info(f"Testing IngestApiManager.extract_cell_count_from_secondary_analysis_files")
            logger.info(f"Bearer token: {bearer_token}")
            logger.info(f"sample_uuid: {sample_uuid}")
            ds_uuids: List[str] = \
                manager.neo4j_manager.retrieve_ds_uuids_with_rui_location_information_for_sample_uuid(sample_uuid)
            logger.info(f"Neo4jManager.retrieve_ds_uuids_with_rui_location_information_for_sample_uuid; ds_uuids: {', '.join(ds_uuids)}")
            resp_json: dict =\
                manager.ingest_api_manager.extract_cell_count_from_secondary_analysis_files(bearer_token, ds_uuids)
            logger.info(f"cell type counts: {resp_json['cell_type_counts']}")

        elif args.build_json_token is not None:
            logger.info(f'** Building data.json and sending it to {psc_working_dir}...')

            manager.dump_cell_types_data(args.build_json_token, '../scripts/psc/data.json')

            ssh = Ssh(config)

            ssh.send_shell(f'mkdir -f {psc_working_dir}')
            ssh.scp_put('../scripts/psc/mkvenv.sh', psc_working_dir)
            ssh.scp_put('../scripts/psc/requirements.txt', psc_working_dir)
            ssh.scp_put('../scripts/psc/test.py', psc_working_dir)
            ssh.scp_put('../scripts/psc/data.json', psc_working_dir)

        elif args.run_psc:
            logger.info(f'** Building data.json on psc server...')

            # $ ssh kollar@hive.psc.edu
            # $ ssh kollar@hivevm191.psc.edu
            # $ cd ~/bin/psc
            # $ ./mkvenv.sh
            #

            # ssh.send_shell('cd ~/bin')
            # ssh.send_shell('rm -rf ./psc')
            # ssh.scp_put_dir('../scripts/psc', '~/bin')
            # ssh.send_shell('cd ./psc')
            # ssh.send_shell('./mkvenv.sh') # THIS TAKES FOREVER ON THE PSC MACHINES

            ssh = Ssh(config)

            ssh.open_shell()
            ssh.send_shell(f'cd {psc_working_dir}')
            ssh.send_shell('source ./venv/bin/activate')
            ssh.send_shell('./test.py')

            time.sleep(10)
            logger.info(f'last line of received data: {ssh.get_strdata()}')
            logger.info(f'complete data received: {ssh.get_fulldata()}')

        elif args.process_json:
            logger.info(f'** Building cell_types table and retrieving it to {local_working_dir}...')

            ssh = Ssh(config)
            ssh.scp_get(f'{psc_working_dir}/data_out.json', local_working_dir)

            manager.build_cell_types_table('../scripts/psc/data_out.json')
            logger.info(f"Missing cell_type_names: {', '.join(manager.get_missing_cell_type_names())}")
    finally:
        manager.close()
        logger.info('Done!')
