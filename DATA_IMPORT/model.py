
from typing import Literal,Optional,List
from pydantic import BaseModel

class ResultModel:
    def __init__(self, status: Literal[-1,0, 1], message: str):
        self.status = status
        self.message = message
class TableInfor:
    def __init__(self, catalog: str, schema: str,table: str):
        self.catalog=catalog
        self.schema=schema
        self.table=table

class KeyColumn(BaseModel):
    input_key: str
    output_key: str

class Column(BaseModel):
    column: str
    type:Optional[Literal["INT","VARCHAR","DOUBLE","TIMESTAMP","BOOLEAN"]]=None

class ColumnInOut(BaseModel):
    input: Column
    output: Column

class DataImportRequest(BaseModel):
    username:str
    type:Literal['CSV','JSON','EXCEL']
    option:Literal['insert','update','upsert']
    table_name:str
    input_file_name: str
    delimiter: Literal["|",","]
    key_columns:List[KeyColumn]
    columns:List[ColumnInOut]