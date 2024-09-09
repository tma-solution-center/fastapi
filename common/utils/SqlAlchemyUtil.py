from sqlalchemy import create_engine, CursorResult
from sqlalchemy.sql.expression import select, text
from typing import Literal
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import OperationalError
import logging.config

from common.config.setting_logger import LOGGING

logging.config.dictConfig(LOGGING)
logger = logging.getLogger()


class SqlAlchemyUtil:
    def __init__(
            self,
            connection_string: Literal["{diver}://{user}@{host}:{port}/{catalog}"],

    ) -> None:
        self.conection_string = connection_string
        self.engine = None
        self.__connection: Connection = None

    def connect(self):
        try:
            if self.__connection is None:
                self.engine = create_engine(self.conection_string)
                self.__connection = self.engine.connect()
        except OperationalError as e:
            logging.warning("[SQLAlchemy] Connection failed: %s. Retry connection!", e)
            try:
                self.engine = create_engine(self.conection_string)
                self.__connection = self.engine.connect()
            except OperationalError as e:
                logger.error(str(e))
                raise e

    def execute_query(self, query: str):
        self.connect()
        try:
            self.__connection.execute(text(query))
        except Exception as e:
            logger.error(str(e))
            raise e

    def execute_multiple_queries(self, queries: list):
        self.connect()
        try:
            for query in queries:
                if query.strip():
                    self.__connection.execute(text(query))

        except OperationalError as e:
            logger.error(f"[SQLAlchemy] Execute failed due to: {str(e)}")
            raise e
        except Exception as e:
            raise e
        finally:
            self.__connection.close()

    def execute_count_query(self, query: str):
        self.connect()
        try:
            result = self.__connection.execute(text(query))
            count = result.scalar()
            return count
        except Exception as e:
            logger.error(str(e))
            raise e
        finally:
            self.__connection.close()

    def execute_query_to_get_data(self, query: str):
        self.connect()
        try:
            result: CursorResult = self.__connection.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()

            data = [dict(zip(columns, row)) for row in rows]
            return data
        except Exception as e:
            logger.error(str(e))
            raise e
        finally:
            self.__connection.close()