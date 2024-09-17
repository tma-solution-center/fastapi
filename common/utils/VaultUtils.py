import hvac
import logging.config
from common.config.setting_logger import LOGGING
import os

logging.config.dictConfig(LOGGING)
logger = logging.getLogger()

vault_url = os.getenv('VAULT_URL')
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
        # for key in vault_unsual_key_list:
        #     unseal_response = self.client.sys.submit_unseal_key(key)
        #     if unseal_response['sealed'] is False:
        #         logger.info("Vault unseal completed!")
        #         break

        self.client.token = vault_token

        if not self.client.is_authenticated():
            raise Exception("Authentication failed. Please check the token.")

    def read_secret(self, path):
        """
        Read secret from Vault.

        :param mount_point: The "path" the secret engine was mounted on.
        :param path: Specifies the path of the secret to read. This is specified as part of the URL.
        :return: Secret data.
        """
        try:
            read_response = self.client.secrets.kv.v2.read_secret_version(mount_point='secrets', path=path)
            secret_data = read_response['data']['data']
            return secret_data
        except Exception as e:
            raise Exception(f"Error reading secret: {e}")

    def create_or_update_secret_to_vault(self, secret_path, secret_data):
        """
        Thêm một secret key vào HashiCorp Vault.
        :param secret_path: Đường dẫn lưu trữ secret (ví dụ: secret/myapp)
        :param secret_data: Dictionary chứa các secret cần thêm (ví dụ: {'key': 'value'})
        """
        try:
            # Thêm secret vào Vault
            self.client.secrets.kv.v2.create_or_update_secret(
                mount_point='secrets',
                path=secret_path,
                secret=secret_data
            )

            logger.info(f"Secret added at path: {secret_path}")

        except Exception as e:
            logger.error(f"Error adding secret: {str(e)}")
            raise e
