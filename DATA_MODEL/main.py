from trino.dbapi import connect

from .helper import *
from pydantic import BaseModel
from io import BytesIO
from fastapi import File, UploadFile,FastAPI, Path, HTTPException,  APIRouter
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import uvicorn
from .SqlAlchemyUtil import *
from fastapi.responses import JSONResponse
from constants import TRINO_CONNECTION_STRING

router = APIRouter()

@router.post('/trino/create_table/', tags=["DATA_MODEL"])
def create_table(request:IcebergTable):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = generate_sql_create_table(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Table was created successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})

@router.post('/trino/add_columns/', tags=["DATA_MODEL"])
def add_columns(request:IcebergTable):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    query_arr = generate_sql_add_column(request)
    try:
        for query in query_arr:
            sqlAlchemyUtil.execute_query(query)
        return JSONResponse(status_code=200,content={"message":"Columns was added successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})

@router.post('/trino/rename_column/', tags=["DATA_MODEL"])
def rename_column(request:RenameColumn):
    sqlAlchemyUtil=SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    query=generate_sql_rename_column(request)
    try:
        sqlAlchemyUtil.execute_query(query)
        return JSONResponse(status_code=200,content={"message":"Column was renamed successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})

# drop all row
@router.post("/trino/drop_all_row/", tags=["DATA_MODEL"])
def drop_all_row(request: DropAllRow):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = generate_sql_drop_all_row(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Drop all row columns successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})

# drop table
@router.delete("/trino/drop_table/", tags=["DATA_MODEL"])
def drop_table(request: DropTable):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = generate_sql_drop_table(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Drop table successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})
     

# remove columns
@router.post("/trino/remove_columns/", tags=["DATA_MODEL"])
def remove_columns(request: RemoveColumns):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = generate_sql_remove_columns(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Remove columns successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})
     

@router.post("/trino/insert/", tags=["DATA_MODEL"])
def insert(request:Insert):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = insert_row_query_builder(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Insert successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})


@router.post("/trino/replace_edit_row/", tags=["DATA_MODEL"])
def replace_edit_row(request:ReplaceAndEdit):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = replace_and_edit_row_query_builder(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Replace and edit row successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})


@router.post("/trino/snapshot_retention/", tags=["DATA_MODEL"])
def snapshot_retention(request:SnapshotRetention):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = snapshot_retention_query_builder(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Snapshot retention successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})

@router.post("/trino/update_values/", tags=["DATA_MODEL"])
def update_values(request:UpdateValuesMultiCondition):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = update_values_multi_condition(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Update values multi condition successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})

@router.post("/trino/update_nan_value/", tags=["DATA_MODEL"])
def update_nan(request:UpdateNanValue):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = update_nan_value(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Update nan values successfully"})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})

