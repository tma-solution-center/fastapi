from fastapi import HTTPException, APIRouter
import httpx
import random  # Import the random module
import string, re
from common.utils import APIUtils
from common.utils.CommonUtils import CommonUtils
from common.utils.VaultUtils import VaultUtils

router = APIRouter()

LOCAL_FILE_DIRECTORY = "./API/template"  # Replace with your local directory path
FILENAME = "api-minio-1.json"  # Replace with the name of the file you want to use

vault_utils = VaultUtils()

# @router.post("/upload-job/{id}")
# async def upload_job(
#         id: str,
#         groupName: str = Form(...)
# ):
#     try:
#         print('da vao function')
#         # Generate random positions for X and Y between 0 and 500
#         positionX = random.uniform(0, 500)
#         positionY = random.uniform(0, 500)
#
#         # Generate a random UUID for clientId
#         clientId = str(uuid.uuid4())
#
#         # File handling: constructing the file name and path
#         # file_name = f"{source_name}.json"
#         file_path = f"{LOCAL_FILE_DIRECTORY}/{FILENAME}"
#
#         # Read file data from the local directory
#         with open(file_path, "rb") as file:
#             file_data = file.read().decode("utf-8")  # Decode bytes to string
#             file_data = json.loads(file_data)  # Parse the string as JSON
#
#         # Update the properties in file_data
#           file_data['flowContents']['processors'][9]['properties'].update({
#             'Endpoint Override URL': endpoint_URL,
#             'Bucket': APIUtils.BUCKET_NAME,
#             'Access Key': APIUtils.ACCESS_KEY,
#             'Secret Key': APIUtils.SECRET_KEY
#         })
#
#         # Convert file_data back to JSON string before sending it in the request
#         file_data = json.dumps(file_data)
#
#         # Prepare the NiFi API upload URL
#         token = await get_nifi_token()
#         upload_url = f"{APIUtils.NIFI_URL}/process-groups/{id}/process-groups/upload"
#
#         # Make an asynchronous POST request to NiFi to upload the file
#         async with httpx.AsyncClient(verify=False) as client:
#             upload_response = await client.post(
#                 upload_url,
#                 headers={"Authorization": f"Bearer {token}"},
#                 files={"file": (FILENAME, file_data, "application/json")},
#                 data={
#                     "groupName": groupName,
#                     "positionX": positionX,  # Use the randomly generated X position
#                     "positionY": positionY,  # Use the randomly generated Y position
#                     "clientId": clientId,  # Use the randomly generated UUID
#                     "disconnectedNodeAcknowledged": "True"
#                 }
#             )
#
#             # print('trang thai:', upload_response.status_code)  # Kiểm tra mã trạng thái phản hồi
#             # print('noi dung:', upload_response.text)  # Kiểm tra nội dung phản hồi
#
#         # Assuming upload_response is the response from the API
#         processors = upload_response.json().get('component', {}).get('contents', {}).get('processors', [])
#
#         processors_info = []
#
#         # Loop through each processor and extract the necessary attributes
#         for i, processor in enumerate(processors):
#             processor_id = processor.get('id')
#             processor_name = processor.get('name')
#
#             # Get 'record-reader', 'record-writer', and 'HTTP Context Map' attributes
#             properties = processor.get('config', {}).get('properties', {})
#             record_reader = properties.get('record-reader')
#             record_writer = properties.get('record-writer')
#             http_context_map = properties.get('HTTP Context Map')
#
#             # Create an object to hold processor information
#             processor_info = {
#                 f"id_processor_{i + 1}": processor_id,
#                 f"name_processor_{i + 1}": processor_name
#             }
#
#             # Add attributes only if they exist
#             if record_reader:
#                 processor_info[f"record_reader_processor_{i + 1}"] = record_reader
#             if record_writer:
#                 processor_info[f"record_writer_processor_{i + 1}"] = record_writer
#             if http_context_map:
#                 processor_info[f"http_context_map_processor_{i + 1}"] = http_context_map
#
#             # Add processor_info to the list
#             processors_info.append(processor_info)
#
#         # After iterating through all processors, return the result
#         return {
#             "status_code": upload_response.status_code,
#             "clientId": clientId,  # Return the randomly generated clientId
#             "version_processor_group": upload_response.json().get('revision', {}).get('version'),
#             "id_processor_group": upload_response.json().get('id'),
#             "positionX": positionX,  # Return the randomly generated X position
#             "positionY": positionY,  # Return the randomly generated Y position
#             "processors_info": processors_info  # Return the complete processors information
#         }
#
#         # return {"status_code": upload_response.status_code, "response": upload_response.json()}
#
#     except httpx.HTTPStatusError as e:
#         # Handle HTTP errors from NiFi API
#         raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
#     except httpx.RequestError as e:
#         # Handle general request errors
#         raise HTTPException(status_code=500, detail=str(e))
#     except Exception as e:
#         # Handle any other unforeseen errors
#         raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


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
            json = vault_utils.read_secret("minio/keys")
            json['tokenToPushingDataMinio'] = new_value
            vault_utils.create_or_update_secret_to_vault("minio/keys", json)
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
            return {"message": "succeed!"}
        else:
            raise HTTPException(
                # status_code=update_response.status_code,
                detail=f"Failed to update processor: {update_response.text}"
            )