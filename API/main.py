from trino.dbapi import connect

from .helper import *
from pydantic import BaseModel
from io import BytesIO
from fastapi import File, UploadFile,FastAPI, Path, HTTPException, APIRouter
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import uvicorn
from .SqlAlchemyUtil import *
from fastapi.responses import JSONResponse
from constants import TRINO_CONNECTION_STRING

router = APIRouter()

@router.post("/api/v1/public-api/", tags=["API"])
def update_values(request:UpdateColumns):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    
    if request.type not in ["update", "insert", "upsert"]:
        raise HTTPException(status_code=400, detail="Invalid action type. Must be 'update' , 'insert' or 'upsert' ")

    try:
        if (request.type  == "update"):
            sql_str = update_table_destination(request)

        if (request.type  == "insert"):
            sql_str = insert_table_destination(request)

        if (request.type  == "upsert"):
            sql_str = upsert_table_destination(request)
    
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Data processed successfully"})

    except ValueError as ve:
        return JSONResponse(status_code=400, content={"message": str(ve)})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})

@router.post("api/v1/third-party-api/", tags=["API"])
def mapping(request:MappingData):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    
    if request.type not in ["update", "insert", "upsert"]:
        raise HTTPException(status_code=400, detail="Invalid action type. Must be 'update' , 'insert' or 'upsert' ")

    try:
        if (request.type  == "update"):
            sql_str = mapping_data_update(request)

        elif (request.type  == "insert"):
            sql_str = mapping_data_insert(request)

        elif (request.type  == "upsert"):
            sql_str = mapping_data_upsert(request)
        
        if isinstance(sql_str, list):
            for q in sql_str:
                sqlAlchemyUtil.execute_query(q)
        else:
            sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200,content={"message":"Data processed successfully"})

    except ValueError as ve:
        return JSONResponse(status_code=400, content={"message": str(ve)})
    except Exception as e:
        return JSONResponse(status_code=400,content={"message":str(e)})

