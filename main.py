from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from API.main import router as router_api
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
app.include_router(router_data_channel, prefix="/main", tags=["DATA_CHANNEL"])
app.include_router(router_data_import, prefix="/main", tags=["DATA_IMPORT"])
app.include_router(router_data_model, prefix="/main", tags=["DATA_MODEL"])
app.include_router(router_data_flow, prefix="/main", tags=["DATA_FLOW"])
app.include_router(router_marketing_automation, prefix="/main", tags=["MARKETING_AUTOMATION"])
app.include_router(router_segmentation, prefix="/main", tags=["SEGMENTATION"])
