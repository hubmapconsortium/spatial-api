import logging
import threading
import paramiko
import scp

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

strdata=''
fulldata=''

# https://stackoverflow.com/questions/6203653/how-do-you-execute-multiple-commands-in-a-single-session-in-paramiko-python
class Ssh:
    shell = None
    client = None
    transport = None
    scp_client = None

    def __init__(self, config):
        tissue_sample_cell_type_config = config['ssh']
        self.psc_username: str = tissue_sample_cell_type_config.get('PscUsername')
        self.psc_password: str = tissue_sample_cell_type_config.get('PscPassword')
        self.psc_gateway_host: str = tissue_sample_cell_type_config.get('PscGatewayHost')
        self.psc_working_host: str = tissue_sample_cell_type_config.get('PscWorkingHost')

        logger.info(f"Connecting to server {self.psc_username}@{self.psc_gateway_host}")
        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        try:
            self.client.connect(self.psc_gateway_host, username=self.psc_username, password=self.psc_password, look_for_keys=False)
        except Exception as ex:
            logger.error(f'Ssh connection failed: {ex}')
            return
        self.transport = paramiko.Transport((self.psc_gateway_host, 22))
        self.transport.connect(username=self.psc_username, password=self.psc_password)

        thread = threading.Thread(target=self.process)
        thread.daemon = True
        thread.start()

        # https://pypi.org/project/scp/
        self.scp_client = scp.SCPClient(self.client.get_transport())

    def close(self):
        logger.info(f'Ssh: Closing connection')
        if self.client is not None:
            self.client.close()
            self.transport.close()

    def open_shell(self):
        self.shell = self.client.invoke_shell()

    def send_shell(self, command):
        if self.shell:
            self.shell.send(command + "\n")
        else:
            logger.error("Ssh: Shell not opened.")

    def process(self):
        global strdata, fulldata
        while True:
            # Print data when available
            if self.shell is not None and self.shell.recv_ready():
                alldata = self.shell.recv(1024)
                while self.shell.recv_ready():
                    alldata += self.shell.recv(1024)
                strdata = strdata + str(alldata)
                fulldata = fulldata + str(alldata)
                strdata = self.print_lines(strdata) # print all received data except last line

    def print_lines(self, data):
        last_line = data
        if '\n' in data:
            lines = data.splitlines()
            for i in range(0, len(lines)-1):
                print(lines[i])
            last_line = lines[len(lines) - 1]
            if data.endswith('\n'):
                print(last_line)
                last_line = ''
        return last_line

    def get_strdata(self) -> str:
        return strdata

    def get_fulldata(self) -> str:
        return fulldata


    # https://pypi.org/project/scp/
    def scp_put(self, src: str, dest: str) -> None:
        self.scp_client.put(src, dest)

    def scp_put_dir(self, src: str, dest: str) -> None:
        self.scp_client.put(src, recursive=True, remote_path=dest)

    def scp_get(self, src: str, dest: str) -> None:
        self.scp_client.get(src, dest)
