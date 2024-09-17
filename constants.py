# Config connection constant
TRINO_CONNECTION_STRING = "trino://admin@trino.trino.svc.cluster.local/iceberg"
# TRINO_CONNECTION_STRING = "trino://admin@localhost:8088/iceberg"
TEMP_CATALOG = 'iceberg'
TEMP_SCHEMA = 'temp'
DEFAULT_CATALOG = 'iceberg'
DEFAULT_SCHEMA = 'cdp'
HIVE_CATALOG = 'hive'

# Path of share volume airflow and fast api
NFS_PATH = '/nfs/'

# API URL
SEND_SMS_API_URL = 'https://dev.cdp-tma.link/api/cdp-data/api/send-message/e-sms'
MINIO_BUCKET_NAME = 'cdp-schema'

TRINO_DATA_TYPE_MAPPING = {
    "int": "INTEGER",
    "float": "DOUBLE",
    "decimal": "DECIMAL",
    "string": "VARCHAR",
    "str": "VARCHAR",
    "date": "DATE",
    "time": "TIME",
    "datetime": "TIMESTAMP",
    "bool": "BOOLEAN"
}

MINIO_URL_STR = "minio_url"
ACCESS_KEY_STR = "access_key"
SECRET_KEY_STR = "secret_key"
BUCKET_NAME_STR = 'bucket_name'

MINIO_SERVICE_NAME = 'minio'