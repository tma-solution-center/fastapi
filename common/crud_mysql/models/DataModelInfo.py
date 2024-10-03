from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from datetime import datetime

from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DataModelInfo(Base):
    __tablename__ = 'data_model_info'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255))
    table_name = Column(String(255))
    type_table = Column(String(255))
    column_info = Column(JSON)
    status = Column(Boolean)
    created_date = Column(DateTime, default=datetime.utcnow)
    modified_date = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
