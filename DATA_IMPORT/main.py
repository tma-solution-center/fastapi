
from fastapi import FastAPI,UploadFile,File, APIRouter
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import logging
from .model import DataImportRequest
from .helper import *

logger = logging.getLogger("main")
logging.basicConfig()
logger.setLevel(logging.INFO)

router = APIRouter()

@router.post("/data_import/upload_file/", tags=["DATA_IMPORT"])
def upload_file(file:UploadFile=File(...)):
    logger.info(f"Input filename: {file.filename}")    
    if file.content_type not in ['text/csv']:
        return JSONResponse(status_code=200,content={'message':f"Importing data currently does not support the content type '{file.content_type}'"})
    try:
        result=upload_file_to_minio(file.filename,file.file,file.content_type)
        logger.info(f"Uploaded successfully: {result}")
        return JSONResponse(status_code=200,content=result)
    except Exception as e:
        logger.error(f"Uploading failed due to: {str(e)}")
        return JSONResponse(status_code=400,content={"message":"Uploading failed"})

@router.post("/data_import/import/", tags=["DATA_IMPORT"])
def import_data(request: DataImportRequest):
    clear_resource:List[TableInfor]=[]
    try:
        raw_result=create_raw_table(request)
        if isinstance(raw_result,ResultModel) and raw_result.status==0:
            return JSONResponse(status_code=400,content={"message":"Importing data failed because the external table for raw data could not be created"})
        else: 
            clear_resource.append(raw_result)

        converted_result = create_converted_type_table(request,raw_result.table)
        if isinstance(converted_result,ResultModel) and converted_result.status==0:
            return JSONResponse(status_code=400,content={"message":"Importing data failed due to an error in converting data types."})
        else:
            clear_resource.append(converted_result)

        import_data_result = None
        if request.option=="insert":
            import_data_result = insert(request,converted_result.table)
        elif request.option=="update":
            import_data_result = update(request,converted_result.table)
        elif request.option=="upsert":
            import_data_result=upsert(request,converted_result.table)

        if isinstance(import_data_result,ResultModel) and import_data_result.status==-1:
                return JSONResponse(status_code=400,content={"message":import_data_result.message})
        else: return JSONResponse(status_code=200,content={"Effected Rows":str(import_data_result.get("Number_of_row"))})        

    except Exception as e:
        logger.error(f"Importing failed due to: {str(e)}")
        return JSONResponse(status_code=400,content={"message":"Importing failed"})
    finally:
        try:
            if clear_resource:
                drop_tables(clear_resource)
        except Exception as e:
            logger.error(f"Clearing resource failed due to: {str(e)}")
    