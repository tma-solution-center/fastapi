from fastapi import Form, HTTPException, APIRouter
import httpx, json, random, uuid

from common.utils import APIUtils
from common.utils.CommonUtils import CommonUtils

# Initialize the FastAPI router
router = APIRouter()

LOCAL_FILE_DIRECTORY = "./API/template"  # Replace with your local directory path
FILENAME = "cdc-postgre.json"  # Replace with the name of the file you want to use


@router.post("/create-cdc-postgre/{id}", tags=["DATA_CHANNEL_CDC_POSTGRES"])
async def create_cdc_postgre(
    id: str,
    groupName: str = Form(...),
    Database_Driver_Class_Name: str = Form(...),
    Database_Connection_URL: str = Form(...),
    Database_User: str = Form(...),
    Password: str = Form(...),
    table_name: str = Form(...),
    col_name: str = Form(...),
    Max_Rows_Per_Flow_File: int = Form(...),
    Output_Batch_Size: int = Form(...)
):
    try:
        # Generate random positions for X and Y between 0 and 500
        positionX = random.uniform(0, 500)
        positionY = random.uniform(0, 500)

        # Generate a random UUID for clientId
        clientId = str(uuid.uuid4())

        # File handling: constructing the file name and path
        # file_name = f"{source_name}.json"
        file_path = f"{LOCAL_FILE_DIRECTORY}/{FILENAME}"

        # Read file data from the local directory
        with open(file_path, "rb") as file:
            file_data = file.read().decode("utf-8")  # Decode bytes to string
            file_data = json.loads(file_data)  # Parse the string as JSON

        # Update the properties in file_data
        file_data['flowContents']['controllerServices'][0]['properties'].update({
            'Database Driver Class Name': Database_Driver_Class_Name,
            'Database Connection URL': Database_Connection_URL,
            'Database User': Database_User,
            'Password': Password
        })
                
        file_data['flowContents']['processors'][0]['properties'].update({
            'Table Name': table_name,
            'Maximum-value Columns': col_name,
            'qdbt-max-rows': Max_Rows_Per_Flow_File,
            'qdbt-output-batch-size': Output_Batch_Size
        })

        # Update the properties in file_data for minio      
        file_data['flowContents']['processors'][2]['properties'].update({
            'Endpoint Override URL': APIUtils.ENDPOINT_URL,
            'Bucket': APIUtils.BUCKET_NAME_POSTGRES,
            'Access Key': APIUtils.ACCESS_KEY,
            'Secret Key': APIUtils.SECRET_KEY
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
                files={"file": (FILENAME, file_data, "application/json")},
                data={
                    "groupName": groupName,
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
            if i < len(processors) and "Database Connection Pooling Service" in processors[i].get('config', {}).get('properties', {}):
                id_Database_Connection_Pooling_Service = processors[i]['config']['properties']["Database Connection Pooling Service"]
                break
        
        # Extract processors details
        processors = upload_response.json().get('component', {}).get('contents', {}).get('processors', [])

        processors_info = []
        for i, processor in enumerate(processors):
            processor_id = processor.get('id')
            processor_name = processor.get('name')
            processors_info.append({
                f"id_processor_{i+1}": processor_id,
                f"name_processor_{i+1}": processor_name
            })

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
