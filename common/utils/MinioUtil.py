from datetime import timedelta
from io import BytesIO

import pandas as pd
from minio import Minio
from minio.helpers import ObjectWriteResult
from minio.error import S3Error
import logging.config
import time
from typing import BinaryIO
import json

from common.config.setting_logger import LOGGING
from common.utils.VaultUtils import VaultUtils
from constants import MINIO_URL_STR, ACCESS_KEY_STR, SECRET_KEY_STR

logging.config.dictConfig(LOGGING)
logger = logging.getLogger()

vault_utils = VaultUtils()
secret_data = vault_utils.read_secret(path='minio')

# MINIO_SERVICE_NAME = 'minio'
# NAMESPACE = 'minio'
MINIO_URL = secret_data['minio_url']
ACCESS_KEY = secret_data['access_key']
SECRET_KEY = secret_data['secret_key']
MAX_RETRIES = 3


class MinioUtil:
    __instance = None

    @staticmethod
    def get_instance_default():
        """ Static access method to get or create the default MinioUtil instance. """
        MinioUtil.__instance = MinioUtil(MINIO_URL, ACCESS_KEY, SECRET_KEY)
        return MinioUtil.__instance

    @staticmethod
    def get_instance(minio_url: str, access_key: str, secret_key: str):
        """ Static access method to get or create a MinioUtil instance"""
        if not MinioUtil.__instance:
            MinioUtil.__instance = MinioUtil(minio_url, access_key, secret_key)
        else:
            MinioUtil.__instance.minio_url = minio_url
            MinioUtil.__instance.access_key = access_key
            MinioUtil.__instance.secret_key = secret_key
            MinioUtil.__instance.client = Minio(
                MinioUtil.__instance.minio_url,
                access_key=MinioUtil.__instance.access_key,
                secret_key=MinioUtil.__instance.secret_key,
                secure=False
            )
        return MinioUtil.__instance

    def __init__(self, minio_url: str, access_key: str, secret_key: str):
        # self.minio_url = MINIO_URL
        # self.access_key = ACCESS_KEY
        # self.secret_key = SECRET_KEY
        # self.client = Minio(
        #     self.minio_url,
        #     access_key=self.access_key,
        #     secret_key=self.secret_key,
        #     secure=False,
        # )
        self.minio_url = minio_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.client = Minio(
            self.minio_url,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )

    def presigned_get_object(self, bucket_name, object_name):
        url = self.client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(days=7)
        )
        return url

    def presigned_put_object(self, bucket_name, object_name):
        url = self.client.presigned_put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(minutes=45)
        )
        return url

    def get_object(self, bucket_name, object_name):
        try:
            # Tải file về từ MinIO
            response = self.client.get_object(bucket_name, object_name)
            # Đọc nội dung file
            file_content = response.read()

            # Phân tích nội dung JSON
            json_data = json.loads(file_content.decode('utf-8'))
            return json_data
        except S3Error as e:
            logger.error(f"An error occurred: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")

    def check_file_name_exists(self, bucket_name, file_name):
        try:
            self.client.stat_object(bucket_name=bucket_name, object_name=file_name)
            return True
        except Exception as e:
            logger.info(f'Can not read {file_name} in {bucket_name} bucket')
            logger.error(f'[x] Exception: {e}')
            return False

    def put_object(self, bucket_name, object_name, file_data: BinaryIO):
        retry_count = 0
        while True:
            try:
                result: ObjectWriteResult = self.client.put_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    data=file_data,
                    length=-1,
                    part_size=10 * 1024 * 1024
                )
                logger.info(f"Uploaded object '{object_name}' to bucket '{bucket_name}' successfully")
                return result
            except S3Error as s3error:
                if retry_count < MAX_RETRIES:
                    delay = 2
                    logger.error(f"Error uploading object '{object_name}'. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    retry_count += 1
                else:
                    logger.error(f"Failed to upload object '{object_name}' after {MAX_RETRIES} retries.")
                    raise s3error

    def fput_object(self, bucket_name, object_name, local_file_path):
        retry_count = 0
        while True:
            try:
                result: ObjectWriteResult = self.client.fput_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    file_path=local_file_path
                )
                logger.info(f"Uploaded object '{object_name}' to bucket '{bucket_name}' successfully")
                return result
            except S3Error as s3error:
                if retry_count < MAX_RETRIES:
                    delay = 2
                    logger.error(f"Error uploading object '{object_name}'. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    retry_count += 1
                else:
                    logger.error(f"Failed to upload object '{object_name}' after {MAX_RETRIES} retries.")
                    raise s3error

    def delete_object(self, bucket_name, file_name):
        try:
            self.client.remove_object(bucket_name, file_name)
            result = {
                'bucket_name': bucket_name,
                'file_name': file_name,
                'message': f"'{file_name}' was removed successfully"
            }
            return result
        except Exception as e:
            raise Exception(e)

    def fetch_parquet_file(self, bucket_name: str, file_path: str) -> pd.DataFrame:
        try:

            response = self.client.get_object(bucket_name, file_path)
            return pd.read_parquet(BytesIO(response.read()), engine='pyarrow')
        except S3Error as err:
            print(f"Error occurred: {err}")
            return pd.DataFrame()

    def check_connect_and_check_bucket_exists(self, bucket_name):
        """
        Checks the connection to MinIO and whether the specified bucket exists.
        Parameters:
        ----------
            - bucket_name: The name of the bucket to check for existence.
        Returns:
        ----------
        tuple(bool, bool)
            - The first value indicates the result of the connection check to MinIO.
                - `True` if the connection to MinIO is successful, `False` otherwise.
            - The second value indicates whether the bucket exists.
                - `True` if the bucket exists, `False` if the bucket does not exist.
        """
        try:
            if self.client.bucket_exists(bucket_name):
                logger.info(f"Bucket '{bucket_name}' exists. Connection successful!")
                return True, True
            else:
                logger.info(f"Bucket '{bucket_name}' not exists. Connection successful!")
                return True, False
        except S3Error as e:
            logger.error(f"Failed to connect Minio: {e}")
            raise e
