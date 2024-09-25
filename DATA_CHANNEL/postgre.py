from fastapi import FastAPI, HTTPException, APIRouter
import httpx, asyncio, json, requests
import random  # Import the random module
import uuid  # Import the uuid module
from pydantic import BaseModel
import mysql.connector
from common.utils.CommonUtils import CommonUtils
from typing import Optional
from common.utils import APIUtils
from common.utils.APIUtils import mysql_connection_string
from common.utils.SqlAlchemyUtil import SqlAlchemyUtil

# Initialize the FastAPI router
router = APIRouter()

LOCAL_FILE_DIRECTORY = "./DATA_CHANNEL/template"  # Replace with your local directory path
FILENAME1 = "full-load-postgres.json"  # Replace with the name of the file you want to use
FILENAME2 = "cdc-postgre.json"

class PostgreRequest(BaseModel):
    Group_Name: str
    Host: str
    Database_User: str
    Password: str
    Database_Name: str
    Table_Name: str
    Col_Name: Optional[str] = None
    Max_Rows_Per_Flow_File: int
    Output_Batch_Size: int

@router.post("/create-fullload-postgre/{id}", tags=["DATA_CHANNEL_DATABASE"])
async def create_fullload_postgre(id: str, request: PostgreRequest):
    try:
        # Generate random positions for X and Y
        positionX = random.uniform(0, 500)
        positionY = random.uniform(0, 500)

        # Generate a random UUID for clientId
        clientId = str(uuid.uuid4())

        # File handling
        file_path = f"{LOCAL_FILE_DIRECTORY}/{FILENAME1}"

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
                files={"file": (FILENAME1, json.dumps(file_data), "application/json")},
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

        if upload_response.status_code == 201:
            insert_query = f"""
                INSERT INTO {APIUtils.catalog}.data_channel (`pipe_id`, `pipeline_name`, `source_name`, `created_at`, `group_id`)
                VALUES ('{(upload_response.json())['id']}', '{request.Group_Name}', 'Fullload Postgre', NOW(), '{id}');
            """
            # execute query
            sqlalchemy = SqlAlchemyUtil(connection_string=mysql_connection_string)
            sqlalchemy.execute_query(insert_query)

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


@router.post("/create-cdc-postgre/{id}", tags=["DATA_CHANNEL_DATABASE"])
async def create_cdc_postgre(id: str, request: PostgreRequest):
    try:
        # Generate random positions for X and Y between 0 and 500
        positionX = random.uniform(0, 500)
        positionY = random.uniform(0, 500)

        # Generate a random UUID for clientId
        clientId = str(uuid.uuid4())

        # File handling: constructing the file name and path
        # file_name = f"{source_name}.json"
        file_path = f"{LOCAL_FILE_DIRECTORY}/{FILENAME2}"

        # Read file data from the local directory
        with open(file_path, "rb") as file:
            file_data = file.read().decode("utf-8")  # Decode bytes to string
            file_data = json.loads(file_data)  # Parse the string as JSON
        # Construct the Database Connection URL
        Database_Connection_URL = f"jdbc:postgresql://{request.Host}/{request.Database_Name}"
        Database_Driver_Class_Name = f"org.postgresql.Driver"

        # Update the properties in file_data
        file_data['flowContents']['controllerServices'][0]['properties'].update({
            'Database Driver Class Name': Database_Driver_Class_Name,
            'Database Connection URL': Database_Connection_URL,
            'Database User': request.Database_User,
            'Password': request.Password
        })

        file_data['flowContents']['processors'][0]['properties'].update({
            'Table Name': request.Table_Name,
            'Maximum-value Columns': request.Col_Name,
            'qdbt-max-rows': request.Max_Rows_Per_Flow_File,
            'qdbt-output-batch-size': request.Output_Batch_Size
        })

        # Update the properties in file_data for minio
        file_data['flowContents']['processors'][2]['properties'].update({
            'Endpoint Override URL': APIUtils.ENDPOINT_URL,
            'Bucket': APIUtils.BUCKET_NAME_POSTGRES,
            'Access Key': APIUtils.ACCESS_KEY,
            'Secret Key': APIUtils.SECRET_KEY,
            'Object Key': f"{request.Table_Name}/${{now():format('yyyy-MM-dd','Asia/Ho_Chi_Minh')}}/${{now():toDate('yyyy-MM-dd HH:mm:ss.SSS','UTC'):format('yyyy-MM-dd-HH-mm-ss-SSS','Asia/Ho_Chi_Minh')}}.snappy.parquet"
        })

        # Convert file_data back to JSON string before sending it in the request
        file_data = json.dumps(file_data)

        # Prepare the NiFi API upload URL
        token = await CommonUtils.get_nifi_token()
        upload_url = f"{APIUtils.NIFI_URL}/process-groups/{id}/process-groups/upload"

        # Make an asynchronous POST request to NiFi to upload the file
        async with httpx.AsyncClient(verify=False) as client:
            upload_response = await client.post(
                upload_url,
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (FILENAME2, file_data, "application/json")},
                data={
                    "groupName": request.Group_Name,
                    "positionX": positionX,  # Use the randomly generated X position
                    "positionY": positionY,  # Use the randomly generated Y position
                    "clientId": clientId,  # Use the randomly generated UUID
                    "disconnectedNodeAcknowledged": "True"
                }
            )

        # Extract the Database Connection Pooling Service ID if it exists
        id_Database_Connection_Pooling_Service = None  # Initialize with None
        for i in range(0, 10):
            processors = upload_response.json().get('component', {}).get('contents', {}).get('processors', [])
            if i < len(processors) and "Database Connection Pooling Service" in processors[i].get('config', {}).get(
                    'properties', {}):
                id_Database_Connection_Pooling_Service = processors[i]['config']['properties'][
                    "Database Connection Pooling Service"]
                break

        # Extract processors details
        processors = upload_response.json().get('component', {}).get('contents', {}).get('processors', [])

        processors_info = []
        for i, processor in enumerate(processors):
            processor_id = processor.get('id')
            processor_name = processor.get('name')
            processors_info.append({
                f"id_processor_{i + 1}": processor_id,
                f"name_processor_{i + 1}": processor_name
            })

        if upload_response.status_code == 201:
            insert_query = f"""
                INSERT INTO {APIUtils.catalog}.data_channel (`pipe_id`, `pipeline_name`, `source_name`, `created_at`, `group_id`)
                VALUES ('{(upload_response.json())['id']}', '{request.Group_Name}', 'CDC Postgre', NOW(), '{id}');
            """
            # execute query
            sqlalchemy = SqlAlchemyUtil(connection_string=mysql_connection_string)
            sqlalchemy.execute_query(insert_query)

        # Return the relevant details including clientId and positions
        return {
            "status_code": upload_response.status_code,
            "clientId": clientId,  # Return the randomly generated clientId
            "version_processor_group": upload_response.json().get('revision', {}).get('version'),
            "id_processor_group": upload_response.json().get('id'),
            "positionX": positionX,  # Return the randomly generated X position
            "positionY": positionY,  # Return the randomly generated Y position
            "id_Database_Connection_Pooling_Service": id_Database_Connection_Pooling_Service,
            "processors_info": processors_info
        }
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors from NiFi API
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.RequestError as e:
        # Handle general request errors
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # Handle any other unforeseen errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


