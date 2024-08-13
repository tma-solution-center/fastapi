# from pydantic import BaseModel
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from DATA_CHANNEL.models import *
from fastapi.responses import JSONResponse

import json
import requests as rq

router = APIRouter()

@router.post("/cdc/trigger", tags=["DATA_CHANNEL"])
async def create_cdc_connection(request: DebeziumRequest):
    if request.database_type.lower() == "mysql":
        body = {
            "name": request.connector_name,
            "config": {
                "connector.class": "io.debezium.connector.mysql.MySqlConnector",
                "tasks.max": "1",
                "database.hostname": request.db_hostname,
                "database.port": str(request.port),
                "database.user": request.user,
                "database.password": request.password,
                "database.server.id": "2769394",
                "topic.prefix": request.topic_prefix,
                "database.include.list": request.database,
                # "table.include.list": request.table,
                "schema.history.internal.kafka.bootstrap.servers": request.kafka_url,
                "schema.history.internal.kafka.topic": f"schema-changes.{request.database}"
            }
        }
        
        # headers = CaseInsensitiveDict()
        headers = dict()
        headers["accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        body = json.dumps(body) # covert ' -> "

        try: 
            response = rq.post(f"http://{request.debezium_host}/connectors/", data=body, headers=headers)
            if response.status_code == 201:
                return JSONResponse(status_code=response.status_code, content={"message": "Connection was created successfully.", "topic_name": f"{request.topic_prefix}.{request.database}.{request.table}"})
            else:
                return JSONResponse(status_code=response.status_code, content={"message": response.json()["message"]})
        except Exception as e:
            return JSONResponse(status_code=500, content={"message": str(e)})
        # return response.json()
        # return json.loads(response.text)
    elif request.database_type.lower() in ["postgresql", "postgres"]:
        body = {
            "name": request.connector_name,
            "config": {
                "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
                "tasksMax": 1,
                "database.hostname": request.db_hostname,
                "database.port": 5432,
                "database.user": request.user,
                "database.password": request.password,
                "database.dbname": request.database, 
                "topic.prefix": request.topic_prefix,
                # "table.include.list": request.table,
                "schema.history.internal.kafka.bootstrap.servers": request.kafka_url,
                "schema.history.internal.kafka.topic": f"schema-changes.{request.database}",
                "plugin.name": "pgoutput"
            }
        }

        headers = dict()
        headers["accept"] = "application/json"
        headers["Content-Type"] = "application/json"
        body = json.dumps(body) # covert ' -> "

        try: 
            response = rq.post(f"http://{request.debezium_host}/connectors/", data=body, headers=headers)
            if response.status_code == 201:
                return JSONResponse(status_code=response.status_code, content={"message": "Connection was created successfully.", "topic_name": f"{request.topic_prefix}.{request.schema_name}.{request.table}"})
            else:
                return JSONResponse(status_code=response.status_code, content={"message": response.json()["message"]})
        except Exception as e:
            return JSONResponse(status_code=500, content={"message": str(e)})
    else:
        return JSONResponse(status_code=404, content={"message": "Not found source database."})

    
@router.get("/cdc/listConn", tags=["DATA_CHANNEL"])
async def list_cdc_connections(debezium_host: str = "debezium:8083"):
    try:
        response = rq.get(f"http://{debezium_host}/connectors/")
        return JSONResponse(status_code=response.status_code, content={"current-connections": response.json()})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})


@router.post("/livy/submitJob", tags=["DATA_CHANNEL"])
async def submit_spark_job(request: Session):
    body = {
        "file": f"local://{request.job_path}",
        "name": request.name,
        "executorMemory": request.executor_memory,
        "args": request.args
    }
    
    headers = dict()
    # headers["accept"] = "application/json"
    headers["Content-Type"] = "application/json"
    body = json.dumps(body) # covert ' -> "

    try:
        response = rq.post(f"http://livy:8998/batches", data=body, headers=headers)
        return JSONResponse(status_code=response.status_code, content={"message": response.json()})
    except Exception as e:
        return JSONResponse(content={"message": str(e)})


@router.delete("/livy/terminateJob", tags=["DATA_CHANNEL"])
async def kill_spark_job(sessionID: int):
    response = rq.delete(f"http://livy:8998/batches/{sessionID}")
    return JSONResponse(status_code=response.status_code, content={"message": response.json()})
