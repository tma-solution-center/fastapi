from pydantic import BaseModel
from typing import Optional, Literal, List


class KeyColumn(BaseModel):
    source_key: str
    destination_key: str


class MappingColumn(BaseModel):
    column_source: str
    column_destination: str


class Param(BaseModel):
    table_name: Optional[str] = None
    input: Optional[str] = None
    left_input: Optional[str] = None
    right_input: Optional[str] = None
    list_1: Optional[list] = None
    list_2: Optional[list] = None
    list_3: Optional[list] = None
    columns_and_types: Optional[list] = None
    values: Optional[list] = None
    option: Optional[Literal["update", "insert", "upsert", "inner", "left", "right", "full", "outer", "cross", "union"]] = None
    key_columns: Optional[List[KeyColumn]] = None
    mapping_columns: Optional[List[MappingColumn]] = None


class Box(BaseModel):
    box_name: Literal[
        "DATA_MODEL", "SELECT_COLUMNS", "RENAME_COLUMNS", "DROP_COLUMNS", "ADD_COLUMNS", "DROP_DUPLICATES", "CASE",
        "DROP_NULL_RECORDS", "REPLACE_VALUE", "GROUP_BY", "CHANGE_TYPE", "FILTER", "JOIN", "SAMPLE_DATA",
        "UNION", "CHANGE_SCHEMA", "FILL_NULL", "DATA_MODEL_DESTINATION"]
    step_name: Literal[
        "data_model_name", "data_model_name_2", "select_columns_name", "rename_columns_step", "drop_column_name",
        "drop_duplicates_name", "add_columns_name", "case_name", "drop_null_records_name", "replace_value_step",
        "group_by_step", "change_type_name", "filter_name", "join_name", "sample_data_name", "union_name",
        "change_schema_step", "fill_null_step", "data_model_destination_name"]
    param: Param


class Dataflow(BaseModel):
    username: str
    action: str
    flow_name: str
    current_time: str
    boxes: List[Box]


class ResultModel:
    def __init__(self, status: Literal[0, 1], message: str):
        self.status = status
        self.message = message
