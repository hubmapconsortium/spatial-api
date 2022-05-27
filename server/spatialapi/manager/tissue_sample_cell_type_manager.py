import logging
from spatialapi.manager.neo4j_manager import Neo4jManager
from spatialapi.manager.postgresql_manager import PostgresqlManager
from spatialapi.utils.ssh import Ssh
import configparser
import requests
import time
import json
from typing import List

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
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
        self.neo4j_manager = Neo4jManager(config)
        self.postgresql_manager = PostgresqlManager(config)
        self.ssh = Ssh(config)

        tissue_sample_cell_type_config = config['tissueSampleCellType']
        self.ingest_api_url: str = tissue_sample_cell_type_config.get('IngestApiUrl').rstrip('/')

    # https://neo4j.com/docs/api/python-driver/current/api.html
    def close(self) -> None:
        logger.info(f'Neo4jManager: Closing connection to Neo4J, PostgreSQL, and Ssh')
        self.neo4j_manager.close()
        self.postgresql_manager.close()
        self.ssh.close()

    # Login through the UI (https://portal.hubmapconsortium.org/) to get the credentials...
    # In Firefox (Tools > Browser Tools > Web Developer Tools).
    # Click on "Storage" then the dropdown for "Local Storage" and then the url,
    # Applications use the "nexus_token" from the returned information.
    # UI times-out in 15 min so close the browser window, and the token will last for a day or so.
    # nexus_token:"Agzm4GmNjj5rdwEm2zwJrB9EdgpeDXzz3EYxGaNrrVbedgV5qKHkC9WJlGg1p8bQwKa0aNGVenggo4SpxnaD7t7bex"
    def ds_uuid_to_psc_path(self, ds_uuid: str, bearer_token: str) -> str:
        ingest_uri: str = f'{self.ingest_api_url}/datasets/{ds_uuid}/file-system-abs-path'
        headers: dict = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % bearer_token
        }
        response: str = requests.get(ingest_uri, headers=headers)
        if response.status_code != 200:
            if response.status_code == 404:
                logger.info(f"ds_uuid_to_psc_path: ds_uuid '{ds_uuid}' not found.")
                return None
            logger.info(f"ds_uuid_to_psc_path: ds_uuid '{ingest_uri}' status code: {response.status_code}.")
            return None
        response_json: dict = response.json()
        if 'path' not in response_json:
            return None
        return response_json['path']

    def get_cell_types_data(self, bearer_token: str) -> List[dict]:
        recs: List[dict] = self.neo4j_manager.query_cell_types()
        for rec in recs:
            psc_path: str = self.ds_uuid_to_psc_path(rec['ds_uuid'], bearer_token)
            if psc_path is not None:
                rec['psc_file'] = psc_path+'/secondary_analysis.h5ad'
        return recs

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
                    self.postgresql_manager.insert_cell_types_row(sample_uuid, cell_type_name, cell_type_count)
            else:
                ds_uuid_missing_cell_type_counts.append(data['ds_uuid'])
        return ds_uuid_missing_cell_type_counts

if __name__ == '__main__':
    import argparse

    class RawTextArgumentDefaultsHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawTextHelpFormatter
    ):
        pass

    # https://docs.python.org/3/howto/argparse.html
    parser = argparse.ArgumentParser(
        description='Tissue Sample Cell Type Manager',
        formatter_class=RawTextArgumentDefaultsHelpFormatter)
    parser.add_argument("-b", '--build_json', action="store_true",
                        help='build the .json file that is processed at the psc')
    parser.add_argument("-p", '--process_json', action="store_true",
                        help='process the .json file created at the psc')
    parser.add_argument("-r", "--run_psc", action="store_true",
                        help='run code on the psc')

    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read('resources/app.local.properties')
    manager = TissueSampleCellTypeManager(config)

    psc_working_dir: str = '~/bin/psc'
    local_working_dir: str = '../scripts/psc'

    try:
        if args.build_json:
            logger.info(f'** Building data.json and sending it to {psc_working_dir}...')

            token = 'Agm9bW6Brq7gGlX6gz2omp7WzdaxzzEn9yz8n3Vw9qXW1nznndF8CwGaBNqEBlyBawx957nEa5oYB7U6382eatm2aQ'
            manager.dump_cell_types_data(token, '../scripts/psc/data.json')

            ssh = Ssh(config)

            ssh.send_shell(f'mkdir -f {psc_working_dir}')
            ssh.scp_put('../scripts/psc/mkenv.sh', psc_working_dir)
            ssh.scp_put('../scripts/psc/requirements.txt', psc_working_dir)
            ssh.scp_put('../scripts/psc/test.py', psc_working_dir)
            ssh.scp_put('../scripts/psc/data.json', psc_working_dir)

        elif args.run_psc:
            logger.info(f'** Building data.json on psc server...')

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
    finally:
        manager.close()
        logger.info('Done!')
