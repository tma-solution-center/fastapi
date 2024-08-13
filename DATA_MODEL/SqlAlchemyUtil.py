from sqlalchemy import create_engine,Connection
from sqlalchemy.schema import Table, MetaData
from sqlalchemy.sql.expression import select, text
from typing import Literal
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
import logging


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
            logging.warning("[SQLAlchemy] Connection failed: %s. Retry connection!", e)
            try:
                self.engine=create_engine(self.conection_string)
                self.__connection=self.engine.connect()
            except OperationalError as e:
                raise e
            
    def execute_query(self, query:str):
        self.connect()
        try:
            self.__connection.execute(text(query))
        except Exception as e:
            raise e


