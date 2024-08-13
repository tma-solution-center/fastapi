# main.py

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from .helper import *
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import uvicorn
import logging

logger = logging.getLogger("main")
logging.basicConfig()
logger.setLevel(logging.INFO)

router = APIRouter()

@router.post("/data_segmentation/group/", tags=["SEGMENTATION"])
def group_handler(request:Group):
    logger.info(f"request: {request}")

    segment_name=remove_accents_and_replace(request.segment_name)
    request.segment_name = segment_name
    logger.info(f"segment_name: {request.segment_name}")
    
    try:
        if request.action=="calculator_group":
            status,result=calculator_group(request)
            if status.status==1 and result is not None:
                json_compatible_item_data = jsonable_encoder(result)
                return JSONResponse(status_code=200,content=json_compatible_item_data)
        elif request.action=="save_group":
            query,result_status=save_group(request)
            if result_status.status == 1:
                response={}
                response["query"]=query
                response["status"]=result_status.status
                json_compatible_item_data = jsonable_encoder(response)
                return JSONResponse(status_code=200,content=json_compatible_item_data)
    except Exception as e:
        logger.error(f"Creating group falied due to: {str(e)}")
        return JSONResponse(status_code=400,content={"message":"Creating group falied"})

@router.post("/data_segmentation/segment/", tags=["SEGMENTATION"])
def segment_handler(request:Segment):
    logger.info(f"request: {request}")

    segment_name=remove_accents_and_replace(request.segment_name)
    request.segment_name = segment_name
    logger.info(f"segment_name: {request.segment_name}")
    
    try:
        if request.action=="calculator_segment":
            status,result=calculator_segment(request)
            if status.status==1 and result is not None:
                json_compatible_item_data = jsonable_encoder(result)
                return JSONResponse(status_code=200,content=json_compatible_item_data)
        elif request.action=="save_segment":
            query,result_status=save_segment(request)
            if result_status.status == 1:
                response={}
                response["query"]=query
                response["status"]=result_status.status
                json_compatible_item_data = jsonable_encoder(response)
                return JSONResponse(status_code=200,content=json_compatible_item_data)
    except Exception as e:
        logger.error(f"Creating group falied due to: {str(e)}")
        return JSONResponse(status_code=400,content={"message":"Creating group falied"})
