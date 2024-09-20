from common.utils.VaultUtils import VaultUtils

vault_utils = VaultUtils()
minio_data = vault_utils.read_secret('minio/keys')

# minio constants
ENDPOINT_URL = minio_data['endpointURL']
ACCESS_KEY = minio_data['accessKey']
SECRET_KEY = minio_data['secretKey']
BUCKET_NAME_POSTGRES = minio_data['bucketNamePostgres']
BUCKET_NAME_API_MINIO = minio_data['bucketNameApiMinio']

# nifi constants
nifi_data = vault_utils.read_secret('nifi/keys')
USERNAME = nifi_data['username']
PASSWORD = nifi_data['password']
NIFI_URL = nifi_data['nifiUrl']
IDROOT = nifi_data['idroot']

