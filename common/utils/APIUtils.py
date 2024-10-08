from common.utils.VaultUtils import VaultUtils
import logging.config
from common.config.setting_logger import LOGGING

vault_utils = VaultUtils()
minio_data = vault_utils.read_secret('minio/keys')

# minio constants
ENDPOINT_URL = minio_data['endpointURL']
ACCESS_KEY = minio_data['accessKey']
SECRET_KEY = minio_data['secretKey']
BUCKET_NAME_POSTGRES = minio_data['bucketNamePostgres']
BUCKET_NAME_API_MINIO = minio_data['bucketNameApiMinio']
BUCKET_NAME_MYSQl = minio_data['bucketNameMysql']

# nifi constants
nifi_data = vault_utils.read_secret('nifi/keys')
USERNAME = nifi_data['username']
PASSWORD = nifi_data['password']
NIFI_URL = nifi_data['nifiUrl']
IDROOT = nifi_data['idroot']

# mysql constants
mysql_data = vault_utils.read_secret('mysql')
host = mysql_data['host']
port = mysql_data['port']
user = mysql_data['username']
password = mysql_data['password']
catalog = mysql_data['dbname']
dbname_test_conn = mysql_data['dbname_test_conn']
host_local = mysql_data['service_name']
port_local = mysql_data['port_local']

# connection to mysql for getting and saving data
mysql_connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{catalog}"

# define logger
logging.config.dictConfig(LOGGING)
LOGGER = logging.getLogger()





