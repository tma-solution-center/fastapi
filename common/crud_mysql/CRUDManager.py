import time
from typing import Literal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError, OperationalError, TimeoutError
import logging.config
from common.config.setting_logger import LOGGING
from common.crud_mysql.models.DataModelInfo import DataModelInfo
from common.utils.VaultUtils import VaultUtils
from constants import MAX_RETRIES, RETRY_DELAY

logging.config.dictConfig(LOGGING)
logger = logging.getLogger()

SUCCEED = 'succeed'
vault_utils = VaultUtils()
secret_data = vault_utils.read_secret(path='cdp-app-key')
db_username = secret_data['mysql_username']
db_password = secret_data['mysql_password']
db_host = secret_data['mysql_host']
db_port = secret_data['mysql_port']
db_database = secret_data['mysql_database']
engine_url = f'mysql+mysqldb://{db_username}:{db_password}@{db_host}:{db_port}/{db_database}'


class CRUDManager:
    def __init__(self):
        self.engine = create_engine(engine_url)
        self.Session = sessionmaker(bind=self.engine)
        # Base.metadata.create_all(self.engine)  # Tạo bảng nếu chưa tồn tại

    def create(self, obj):
        """Thêm một đối tượng mới vào database"""
        session = self.Session()
        try:
            session.add(obj)
            session.commit()
            logger.info("Record created successfully!")
            return SUCCEED
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to create record: {e}")
            raise e
        finally:
            session.close()

    def read(self, model, record_id):
        """Đọc một bản ghi theo model và record_id"""
        session = self.Session()
        try:
            record = session.query(model).filter_by(id=record_id).one()
            return record
        except NoResultFound:
            logger.error(f"Record with id {record_id} not found.")
            return None
        except SQLAlchemyError as e:
            logger.error(f"Failed to read record: {e}")
            raise e
        finally:
            session.close()

    def get_records_by_filter(self, model, **filters):
        """Lấy danh sách bản ghi từ bảng dựa trên model và điều kiện filter"""
        session = self.Session()
        try:
            query = session.query(model)
            for key, value in filters.items():
                query = query.filter(getattr(model, key) == value)
            records = query.all()
            return records
        except SQLAlchemyError as e:
            logger.error(f"Failed to get filtered records: {e}")
            raise e
        finally:
            session.close()

    def update(self, model, record_id, **kwargs):
        """Cập nhật một bản ghi dựa trên model, record_id, và các trường cần cập nhật"""
        session = self.Session()
        try:
            record = session.query(model).filter_by(id=record_id).one()
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            logger.info("Record updated successfully!")
            return SUCCEED
        except NoResultFound:
            msg = f"Record with id {record_id} not found."
            logger.info(msg)
            return msg
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update record: {e}")
            raise e
        finally:
            session.close()

    def delete(self, model, record_id):
        """Xóa một bản ghi dựa trên model và record_id"""
        session = self.Session()
        try:
            record = session.query(model).filter_by(id=record_id).one()
            session.delete(record)
            session.commit()
            logger.info("Record deleted successfully!")
            return SUCCEED
        except NoResultFound:
            msg = f"Record with id {record_id} not found."
            logger.info(msg)
            return msg
        except SQLAlchemyError as e:
            session.rollback()
            logger.info(f"Failed to delete record: {e}")
            raise e
        finally:
            session.close()

    def close(self):
        self.engine.dispose()

    def insert(self, objs):
        """Chèn nhiều đối tượng vào database"""
        session = self.Session()
        try:
            session.add_all(objs)  # Thêm nhiều bản ghi vào session
            session.commit()  # Commit transaction
            logger.info("Records inserted successfully!")
            return SUCCEED
        except SQLAlchemyError as e:
            session.rollback()  # Rollback nếu có lỗi
            logger.error(f"Failed to insert records: {e}")
            raise e
        finally:
            session.close()

    def add_update_delete_data_model_info_record(self, data: DataModelInfo, is_delete: bool = False,
                                                 max_retries: int = 3, retry_delay: int = 2):
        session = self.Session()
        attempt = 0
        max_retries = MAX_RETRIES
        retry_delay = RETRY_DELAY

        while attempt < max_retries:
            try:
                # Tìm bản ghi dựa trên username và table_name từ đối tượng data
                record = session.query(DataModelInfo).filter_by(username=data.username,
                                                                table_name=data.table_name).first()
                if is_delete:
                    if record:
                        session.delete(record)
                        logger.info(f"Record deleted for username: {data.username}, table_name: {data.table_name}")
                    else:
                        logger.info(f"No record found for username: {data.username}, table_name: {data.table_name}")
                else:
                    if record:
                        # Nếu bản ghi tồn tại, cập nhật các thuộc tính
                        record.column_info = data.column_info
                        record.status = data.status
                        logger.info(f"Record updated for username: {data.username}, table_name: {data.table_name}")
                    else:
                        # Nếu không tồn tại, thêm bản ghi mới
                        session.add(data)
                        logger.info(f"New record added for username: {data.username}, table_name: {data.table_name}")

                # Commit thay đổi
                session.commit()
                break  # Thoát khỏi vòng lặp nếu thành công
            except (OperationalError, TimeoutError) as e:
                session.rollback()
                attempt += 1
                logger.error(f"Attempt {attempt}: Temporary error encountered: {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying after {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached, re-raising exception.")
                    raise e  # Đã hết số lần thử, ném lại ngoại lệ
            except Exception as e:
                session.rollback()
                logger.error(f"Unexpected error: {e}")
                raise e
            finally:
                session.close()
