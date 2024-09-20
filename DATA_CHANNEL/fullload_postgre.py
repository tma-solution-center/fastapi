from fastapi import FastAPI, HTTPException, APIRouter
import httpx, asyncio, json, requests
import random  # Import the random module
import uuid  # Import the uuid module
from pydantic import BaseModel
from common.utils import APIUtils
from common.utils.CommonUtils import CommonUtils

# Initialize the FastAPI router
router = APIRouter()

LOCAL_FILE_DIRECTORY = "./DATA_CHANNEL/template"  # Replace with your local directory path
FILENAME = "full-load-postgres.json"  # Replace with the name of the file you want to use

class FullLoadPostgreRequest(BaseModel):
    Group_Name: str
    Host: str
    Database_User: str
    Password: str
    Database_Name: str
    Table_Name: str
    Max_Rows_Per_Flow_File: int
    Output_Batch_Size: int

@router.post("/create-fullload-postgre/{id}", tags=["DATA_CHANNEL_FULL_LOAD_POSTGRES"])
async def create_fullload_postgre(id: str, request: FullLoadPostgreRequest):
    try:
        # Generate random positions for X and Y
        positionX = random.uniform(0, 500)
        positionY = random.uniform(0, 500)

        # Generate a random UUID for clientId
        clientId = str(uuid.uuid4())

        # File handling
        file_path = f"{LOCAL_FILE_DIRECTORY}/{FILENAME}"

        # Read file data
        try:
            with open(file_path, "rb") as file:
                file_data = json.load(file)  # Directly load as JSON
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

        # Construct the Database Connection URL
        Database_Connection_URL = f"jdbc:postgresql://{request.Host}/{request.Database_Name}"
        Database_Driver_Class_Name = f"org.postgresql.Driver"

        # Update properties in file_data
        file_data['flowContents']['controllerServices'][0]['properties'].update({
            'Database Driver Class Name': Database_Driver_Class_Name,
            'Database Connection URL': Database_Connection_URL,
            'Database User': request.Database_User,
            'Password': request.Password
        })

        file_data['flowContents']['processors'][0]['properties'].update({
            'Table Name': request.Table_Name,
            'qdbt-max-rows': request.Max_Rows_Per_Flow_File,
            'qdbt-output-batch-size': request.Output_Batch_Size
        })

        # Update properties for MinIO
        file_data['flowContents']['processors'][2]['properties'].update({
            'Endpoint Override URL': APIUtils.ENDPOINT_URL,
            'Bucket': APIUtils.BUCKET_NAME_POSTGRES,
            'Access Key': APIUtils.ACCESS_KEY,
            'Secret Key': APIUtils.SECRET_KEY,
            'Object Key': f"{request.Table_Name}/${{now():format('yyyy-MM-dd','Asia/Ho_Chi_Minh')}}/${{now():toDate('yyyy-MM-dd HH:mm:ss.SSS','UTC'):format('yyyy-MM-dd-HH-mm-ss-SSS','Asia/Ho_Chi_Minh')}}.snappy.parquet"
        })

        # Prepare the NiFi API upload URL
        token = await CommonUtils.get_nifi_token()
        upload_url = f"{APIUtils.NIFI_URL}/process-groups/{id}/process-groups/upload"

        # Make an asynchronous POST request to NiFi
        async with httpx.AsyncClient(verify=False) as client:
            upload_response = await client.post(
                upload_url,
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (FILENAME, json.dumps(file_data), "application/json")},
                data={
                    "groupName": request.Group_Name,
                    "positionX": positionX,
                    "positionY": positionY,
                    "clientId": clientId,
                    "disconnectedNodeAcknowledged": "True"
                }
            )

        # Handle the upload response
        upload_response.raise_for_status()  # Raise an error for bad responses
        processors = upload_response.json().get('component', {}).get('contents', {}).get('processors', [])

        # Extract Database Connection Pooling Service ID
        id_Database_Connection_Pooling_Service = next(
            (proc['config']['properties'].get("Database Connection Pooling Service") for proc in processors if
             "Database Connection Pooling Service" in proc.get('config', {}).get('properties', {})),
            None
        )

        # Collect processor details
        processors_info = [
            {"id_processor": proc.get('id'), "name_processor": proc.get('name')}
            for proc in processors
        ]

        # Return relevant details
        return {
            "status_code": upload_response.status_code,
            "clientId": clientId,
            "version_processor_group": upload_response.json().get('revision', {}).get('version'),
            "id_processor_group": upload_response.json().get('id'),
            "positionX": positionX,
            "positionY": positionY,
            "id_Database_Connection_Pooling_Service": id_Database_Connection_Pooling_Service,
            "processors_info": processors_info
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")