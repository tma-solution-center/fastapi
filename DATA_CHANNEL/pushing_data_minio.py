import constants
from fastapi import HTTPException, APIRouter, Form, UploadFile, File
import httpx
import random  # Import the random module
import string, re, uuid, json
from common.utils import APIUtils
from common.utils.CommonUtils import CommonUtils
from common.utils.VaultUtils import VaultUtils

router = APIRouter()

LOCAL_FILE_DIRECTORY = "./DATA_CHANNEL/template"  # Replace with your local directory path
FILENAME = "api-minio-1.json"  # Replace with the name of the file you want to use

vault_utils = VaultUtils()

# Helper function to check if a JSON object is one-level deep
def validate_one_level_json(json_data):
    if not isinstance(json_data, dict):
        return False
    for value in json_data.values():
        if isinstance(value, (dict, list)):
            return False
    return True

# Helper function to generate the ValidJson expression based on file JSON content
def generate_valid_json_expression(json_data):
    keys = list(json_data.keys())

    def build_expression(index):
        if index == len(keys) - 1:
            return f"${{{keys[index]}:isEmpty():not()}}"
        else:
            return f"${{{keys[index]}:isEmpty():not():and(\n    {build_expression(index + 1)}\n)}}"

    return build_expression(0)

@router.post("/create-api-nifi-put-minio/{id}", tags=["DATA_CHANNEL_API"])
async def create_api_nifi_put_minio(
    id: str,
    groupName: str = Form(...),
    pathTail: str = Form(...),
    jsonContent: str = Form(...)  # Pass JSON content as a string
):
    try:
        print('Inside upload_job function')

        # Generate random positions for X and Y between 0 and 500
        positionX = random.uniform(0, 500)
        positionY = random.uniform(0, 500)

        # Generate a random UUID for clientId
        clientId = str(uuid.uuid4())

        json_data = json.loads(jsonContent)

        # Validate that the JSON is only one-level deep
        if not validate_one_level_json(json_data):
            raise HTTPException(status_code=400, detail="JSON must be one-level deep")

        # File handling: constructing the file name and path
        file_path = f"{LOCAL_FILE_DIRECTORY}/{FILENAME}"

        # Read flow definition from the local directory
        with open(file_path, "rb") as file:
            file_data = file.read().decode("utf-8")  # Decode bytes to string
            file_data = json.loads(file_data)  # Parse the string as JSON

        # Update processor 3 properties
        file_data['flowContents']['processors'][3]['properties'].update({
            'Allowed Paths': f"/{pathTail}"
        })

        # Update processor 9 properties (example with MinIO access)
        file_data['flowContents']['processors'][9]['properties'].update({
            'Endpoint Override URL': APIUtils.ENDPOINT_URL,
            'Bucket': APIUtils.BUCKET_NAME_POSTGRES,
            'Access Key': APIUtils.ACCESS_KEY,
            'Secret Key': APIUtils.SECRET_KEY
        })

        # Update processor 2 properties based on uploaded JSON file content
        for key, value in json_data.items():
            file_data['flowContents']['processors'][2]['properties'].update({
                key: f"$.{key}"  # Mapping property names from JSON file
            })

        # Generate ValidJson expression and update processor 2 properties
        valid_json_value = generate_valid_json_expression(json_data)
        file_data['flowContents']['processors'][1]['properties'].update({
            'ValidJson': valid_json_value
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

        # Assuming upload_response is the response from the API
        processors = upload_response.json().get('component', {}).get('contents', {}).get('processors', [])

        processors_info = []
        auth_value = None
        allowed_paths = None

        # Function to extract and format the auth token value
        def format_auth_token(auth_value):
            match = re.search(r"Bearer\s*([\w\d]+)", auth_value)
            if match:
                return f"Bearer Token: {match.group(1)}"
            return auth_value

        # Loop through each processor and extract the necessary attributes
        for i, processor in enumerate(processors):
            processor_id = processor.get('id')
            processor_name = processor.get('name')
            properties = processor.get('config', {}).get('properties', {})

            if processor_name == "HandleHttpRequest":
                allowed_paths = properties.get('Allowed Paths')
                if allowed_paths:
                    allowed_paths = f"{constants.HTTP_URL}{allowed_paths}"

            elif processor_name == "RouteOnAttribute1":
                auth_value = properties.get('auth')
                if auth_value:
                    auth_value = format_auth_token(auth_value)

            # Get 'record-reader', 'record-writer', and 'HTTP Context Map' attributes
            record_reader = properties.get('record-reader')
            record_writer = properties.get('record-writer')
            http_context_map = properties.get('HTTP Context Map')

            # Create an object to hold processor information
            processor_info = {
                f"id_processor_{i+1}": processor_id,
                f"name_processor_{i+1}": processor_name
            }

            # Add attributes only if they exist
            if record_reader:
                processor_info[f"record_reader_processor_{i+1}"] = record_reader
            if record_writer:
                processor_info[f"record_writer_processor_{i+1}"] = record_writer
            if http_context_map:
                processor_info[f"http_context_map_processor_{i+1}"] = http_context_map

            # Add processor_info to the list
            processors_info.append(processor_info)

        # Return the result
        return {
            "status_code": upload_response.status_code,
            "clientId": clientId,
            "version_processor_group": upload_response.json().get('revision', {}).get('version'),
            "id_processor_group": upload_response.json().get('id'),
            "positionX": positionX,
            "positionY": positionY,
            "processors_info": processors_info,
            "auth_value": auth_value,
            "allowed_paths": allowed_paths
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        return {"error": str(e)}


@router.put("/update-properties-router-processor", tags=["DATA_CHANNEL_API"])
async def update_processor(
        id_processor: str
):
    token = await CommonUtils.get_nifi_token()  # Lấy token từ NiFi
    if not token:
        raise HTTPException(status_code=401, detail="Failed to get NiFi token")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"  # Add the token to the headers
    }

    # Construct the request URL to get the process group details
    get_url = f"{APIUtils.NIFI_URL}/processors/{id_processor}"

    async with httpx.AsyncClient() as client:
        # Fetch the process group details to get the latest version
        get_response = await client.get(get_url, headers=headers)

        if get_response.status_code == 200:
            processor_data = get_response.json()
            print("json", processor_data)
        else:
            raise HTTPException(
                status_code=get_response.status_code,
                detail=f"Failed to retrieve processor details: {get_response.text}"
            )

        # Construct the PUT request URL
        update_url = f"{APIUtils.NIFI_URL}/processors/{id_processor}"

        # create string with 20 characters
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for _ in range(20))

        original_value = processor_data['component']['config']['properties']['auth']
        new_value = re.sub(r"Bearer \w+'", f"Bearer {random_string}'", original_value)

        processor_data['component']['config']['properties']['auth'] = new_value
        print("nifi", processor_data['component']['config']['properties']['auth'])
        print("new-value", new_value)
        # Set up query parameters for PUT request
        payload = {
            "revision": processor_data["revision"],  # Phiên bản hiện tại của processor
            "component": {
                "id": processor_data["component"]["id"],
                "config": {
                    "properties": processor_data['component']['config']['properties']
                }
            }
        }

        # Send the update request to the NiFi API
        update_response = await client.put(update_url, json=payload, headers=headers)

        # Check if the update request was successful
        if update_response.status_code == 200:
            json = vault_utils.read_secret("minio/api_minio")
            json['tokenForApi'] = new_value
            vault_utils.create_or_update_secret_to_vault("minio/api_minio", json)
            return {"token": f"{random_string}"}
        else:
            raise HTTPException(
                status_code=update_response.status_code,
                detail=f"Failed to update processor: {update_response.text}"
            )


@router.put("/update-puts3object-processor", tags=["DATA_CHANNEL_API"])
async def update_puts3object_processor(
        id_processor: str, access_id: str, secretkey: str, bucket_name: str
):
    token = await CommonUtils.get_nifi_token()  # Lấy token từ NiFi
    if not token:
        raise HTTPException(status_code=401, detail="Failed to get NiFi token")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"  # Add the token to the headers
    }

    # Construct the request URL to get the process group details
    get_url = f"{APIUtils.NIFI_URL}/processors/{id_processor}"

    async with httpx.AsyncClient() as client:
        # Fetch the process group details to get the latest version
        get_response = await client.get(get_url, headers=headers)

        if get_response.status_code == 200:
            processor_data = get_response.json()
            print("json", processor_data)
        else:
            raise HTTPException(
                status_code=get_response.status_code,
                detail=f"Failed to retrieve processor details: {get_response.text}"
            )

        # update properties
        processor_data['component']['config']['properties']['Access Key'] = access_id
        processor_data['component']['config']['properties']['Secret Key'] = secretkey
        processor_data['component']['config']['properties']['Bucket'] = bucket_name

        # Construct the PUT request URL
        update_url = f"{APIUtils.NIFI_URL}/processors/{id_processor}"

        payload = {
            "revision": processor_data["revision"],
            "component": {
                "id": processor_data["component"]["id"],
                "config": {
                    "properties": processor_data['component']['config']['properties']
                }
            }
        }

        # Send the update request to the NiFi API
        update_response = await client.put(update_url, json=payload, headers=headers)

        # Check if the update request was successful
        if update_response.status_code == 200:
            json = vault_utils.read_secret("minio/api_minio")
            json['accessKey'] = access_id
            json['secretKey'] = secretkey
            json['bucketName'] = bucket_name
            vault_utils.create_or_update_secret_to_vault("minio/api_minio", json)
            return {"message": "succeed!"}
        else:
            raise HTTPException(
                # status_code=update_response.status_code,
                detail=f"Failed to update processor: {update_response.text}"
            )