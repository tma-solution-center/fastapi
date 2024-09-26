from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ConnectionDetails(BaseModel):
    Group_Name: Optional[str] = None
    Host: str
    Port: int
    Database_User: str
    Password: str
    Database_Name: str
    Table_Name: str = None
    Col_Name: Optional[str] = None
    Max_Rows_Per_Flow_File: Optional[int] = None
    Output_Batch_Size: Optional[int] = None


class DataChannel(BaseModel):
    pipe_id: str
    pipeline_name: str
    source_name: str
    status_pipeline: Optional[str]
    json_file: Optional[str]
    created_at: str
    update_at: str
    group_id: str
    control_service: dict


class RequestDataChannel(BaseModel):
    page: int
    size: int
    sortBy: Optional[str]
    sortField: Optional[str]
    filters: Optional[dict]


class ResponseDataChannel(BaseModel):
    data: dict
