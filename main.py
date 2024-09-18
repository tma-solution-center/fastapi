import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from API.main import router as router_api
from API.pushing_data_minio import router as router_api_json_minio
from API.fullload_postgre import router as router_full_load_postgres
from API.cdc_postgre import router as router_cdc_postgres
from DATA_CHANNEL.main import router as router_data_channel
from DATA_IMPORT.main import router as router_data_import
from DATA_MODEL.main import router as router_data_model
from DATAFLOW.main import router as router_data_flow
from MARKETING_AUTOMATION.main import router as router_marketing_automation
from SEGMENTATION.main import router as router_segmentation

def get_application() -> FastAPI:
    application = FastAPI(
        title='FastAPI with Trino',
        description='Integrate FastAPI with Minio',
        openapi_url="/openapi.json",
        docs_url="/docs"
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return application

app = get_application()

app.include_router(router_api, prefix="/main", tags=["API"])
app.include_router(router_api_json_minio, prefix="/pushing-data-minio", tags=["API"])
app.include_router(router_full_load_postgres, prefix="/full-load-postgres", tags=["API FULL LOAD POSTGRES"])
app.include_router(router_cdc_postgres, prefix="/cdc-postgres", tags=["API CDC POSTGRES"])
app.include_router(router_data_channel, prefix="/main", tags=["DATA_CHANNEL"])
app.include_router(router_data_import, prefix="/main", tags=["DATA_IMPORT"])
app.include_router(router_data_model, prefix="/main", tags=["DATA_MODEL"])
app.include_router(router_data_flow, prefix="/main", tags=["DATA_FLOW"])
app.include_router(router_marketing_automation, prefix="/main", tags=["MARKETING_AUTOMATION"])
app.include_router(router_segmentation, prefix="/main", tags=["SEGMENTATION"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)