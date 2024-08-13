from sqlalchemy import create_engine,Connection,CursorResult
from sqlalchemy.schema import Table, MetaData
from sqlalchemy.sql.expression import select, text
from typing import Literal
from sqlalchemy.exc import OperationalError
from .model import ResultModel
import logging

logger = logging.getLogger("SqlAlchemyUtil")
logging.basicConfig()
logger.setLevel(logging.INFO)

class SqlAlchemyUtil:
    def __init__(
            self,
            connection_string: Literal["{diver}://{user}@{host}:{port}/{catalog}"],

    ) -> None:
        self.conection_string=connection_string
        self.engine = None
        self.__connection:Connection = None

    def connect(self):
        try:
            if self.__connection is None:
                self.engine = create_engine(self.conection_string)
                self.__connection=self.engine.connect()
        except OperationalError as e:
            logger.warning("[SQLAlchemy] Connection failed: %s. Retry connection!", e)
            try:
                self.engine=create_engine(self.conection_string)
                self.__connection=self.engine.connect()
            except OperationalError as e:
                raise e
            
    def execute_query(self, query:str):
        self.connect()
        try:
            result: CursorResult = self.__connection.execute(text(query))
            return result
        except OperationalError as e:
            logger.error(f"[SQLAlchemy] Execute failed due to: {str(e)}")
            return ResultModel(0,str(e))
        except Exception as e:
            raise e
        finally:
            self.__connection.close()


