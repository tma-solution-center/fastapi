import hvac
import logging.config
from common.config.setting_logger import LOGGING
import os

logging.config.dictConfig(LOGGING)
logger = logging.getLogger()

vault_url = 'http://localhost:8200/'
vault_token = os.getenv('VAULT_TOKEN')
vault_unsual_key_1 = os.getenv('VAULT_UNSUAL_KEY_1')
vault_unsual_key_2 = os.getenv('VAULT_UNSUAL_KEY_2')
vault_unsual_key_3 = os.getenv('VAULT_UNSUAL_KEY_3')
vault_unsual_key_list = [vault_unsual_key_1, vault_unsual_key_2, vault_unsual_key_3]


class VaultUtils:
    def __init__(self):
        """
        Initialize the VaultUtils class with the URL and token of the Vault server.
        """
        # self.client = hvac.Client(url=VAULT_URL, token=VAULT_TOKEN)
        # Kết nối đến Vault server
        self.client = hvac.Client(url=vault_url)

        # Unseal Vault (nếu cần thiết)
        for key in vault_unsual_key_list:
            unseal_response = self.client.sys.submit_unseal_key(key)
            if unseal_response['sealed'] is False:
                logger.info("Vault unseal completed!")
                break

        self.client.token = vault_token

        if not self.client.is_authenticated():
            raise Exception("Authentication failed. Please check the token.")


    def read_secret(self, path):
        """
        Read secret from Vault.

        :param path: Path to the secret.
        :return: Secret data.
        """
        try:
            read_response = self.client.secrets.kv.v2.read_secret_version(mount_point='secrets',path=path)
            secret_data = read_response['data']['data']
            return secret_data
        except Exception as e:
            raise Exception(f"Error reading secret: {e}")
