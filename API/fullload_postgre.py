from fastapi import FastAPI, Form, HTTPException, APIRouter
import httpx, asyncio, json,requests
import random  # Import the random module
import uuid  # Import the uuid module

from common.utils import APIUtils
from common.utils.CommonUtils import CommonUtils

# Initialize the FastAPI router
router = APIRouter()

LOCAL_FILE_DIRECTORY = "./template"  # Replace with your local directory path
FILENAME = "full-load-postgres.json"  # Replace with the name of the file you want to use


# Asynchronous function to create a processor group in NiFi
async def create_processor_group(id: str, groupName: str):
    token = await CommonUtils.get_nifi_token()  # Lấy token từ NiFi
    if not token:
        raise HTTPException(status_code=401, detail="Failed to get NiFi token")

    async with httpx.AsyncClient(verify=False) as client:
        url = f"{APIUtils.NIFI_URL}/process-groups/{id}/process-groups"  # Construct the NiFi API URL
        
        # Generate random X and Y positions between 0 and 500
        positionX = random.uniform(0, 500)
        positionY = random.uniform(0, 500)

        # Generate a random UUID for clientId
        clientId = str(uuid.uuid4())

        payload = {
            "component": {
                "name": groupName,  # Set the name of the processor group
                "position": {
                    "x": positionX,  # Set the random X position
                    "y": positionY   # Set the random Y position
                }
            },
            "revision": {
                "version": 0,  # Default version number
                "clientId": clientId  # Set the random clientId
            },
            "disconnectedNodeAcknowledged": "True"  # Acknowledge if the node is disconnected
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"  # Add the token to the headers
        }
        response = await client.post(url, json=payload, headers=headers)  # Make the POST request to NiFi

        if response.status_code == 201:  # Check if the response status is 'Created'
            return {
                "clientId": (response.json())['revision']['clientId'],  # Return the client ID
                "version_processor_group": (response.json())['revision']['version'],  # Return the version of the processor group
                "id_new_processor_group": (response.json())['id'],  # Return the ID of the processor group
                "positionX": positionX,  # Return the randomly generated X position
                "positionY": positionY  # Return the randomly generated Y position
            }
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)  # Raise an HTTP exception if the request fails


# FastAPI endpoint to create a processor group
@router.post("/create_processor_group/", tags=["API FULL LOAD POSTGRES"])
async def create_processor_group_endpoint(
    id: str,
    groupName: str = Form(...),
):
    # Call the function to create a processor group and return the result
    result = await create_processor_group(
        id, groupName
    )
    return result


@router.post("/create-fullload-postgre/{id}", tags=["API FULL LOAD POSTGRES"])
async def create_fullload_postgre(
    id: str,
    groupName: str = Form(...),
    Database_Driver_Class_Name: str = Form(...),
    Database_Connection_URL: str = Form(...),
    Database_User: str = Form(...),
    Password: str = Form(...),
    table_name: str = Form(...),
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


@router.post("/start-job/{id}", tags=["API FULL LOAD POSTGRES"])
async def start_job(id: str):
    token = await CommonUtils.get_nifi_token()
    # Construct the URL for the NiFi API endpoint to start the process group
    status_url = f"{APIUtils.NIFI_URL}/flow/process-groups/{id}"
    
    # Payload to set the state of the process group to 'RUNNING'
    payload = {"id": id, "state": "RUNNING"}
    
    # Make an asynchronous PUT request to NiFi to start the process group
    async with httpx.AsyncClient(verify=False) as client:
        headers = {"Authorization": f"Bearer {token}"}  # Add the token to the headers
        status_response = await client.put(
            status_url,
            headers=headers,
            json=payload
        )
    
    # Return the status code and the response JSON from NiFi
    return {
        "status_code": status_response.status_code,  # HTTP status code from NiFi
        "response": status_response.json()  # JSON response from NiFi
    }


@router.post("/stop-job/{id}", tags=["API FULL LOAD POSTGRES"])
async def stop_job(id: str):
    token = await CommonUtils.get_nifi_token()
    # Construct the URL for the NiFi API endpoint to stop the process group
    status_url = f"{APIUtils.NIFI_URL}/flow/process-groups/{id}"
    
    # Payload to set the state of the process group to 'STOPPED'
    payload = {"id": id, "state": "STOPPED"}
    
    # Make an asynchronous PUT request to NiFi to stop the process group
    async with httpx.AsyncClient(verify=False) as client:
        headers = {"Authorization": f"Bearer {token}"}  # Add the token to the headers
        status_response = await client.put(
            status_url,
            headers=headers,
            json=payload
        )
    
    # Return the status code and the response JSON from NiFi
    return {
        "status_code": status_response.status_code,  # HTTP status code from NiFi
        "response": status_response.json()  # JSON response from NiFi
    }


@router.put("/enable-dbcp-connection-pool/{id}", tags=["API FULL LOAD POSTGRES"])
async def enable_dbcp_connection_pool(id: str):
    # Get the token
    token = await CommonUtils.get_nifi_token()

    async with httpx.AsyncClient(verify=False) as client:
        headers = {"Authorization": f"Bearer {token}"}  # Add the token to the headers
        # Fetch the current state and revision of the DBCPConnectionPool
        service_response = await client.get(f"{APIUtils.NIFI_URL}/controller-services/{id}", headers=headers)
        if service_response.status_code != 200:
            return {"status_code": service_response.status_code, "error": service_response.text}
        
        # Enable the DBCPConnectionPool using the retrieved revision
        payload = {"revision": service_response.json()['revision'], "state": "ENABLED"}
        enable_response = await client.put(f"{APIUtils.NIFI_URL}/controller-services/{id}/run-status", json=payload, headers=headers)
        
        if enable_response.status_code == 200:
            return {
                "status_code": enable_response.status_code,
                "response": {
                    "id": (enable_response.json()).get('id'),
                    "message": "Operation was successful."  # Thông báo thành công
                }
            }
        else:
            return {
                "status_code": enable_response.status_code,
                "response": enable_response.text,
                "message": "Operation failed."  # Thông báo lỗi
            }


@router.put("/disable-dbcp-connection-pool/{id}", tags=["API FULL LOAD POSTGRES"])
async def disable_dbcp_connection_pool(id: str):
    # Get the token
    token = await CommonUtils.get_nifi_token()
    async with httpx.AsyncClient(verify=False) as client:
        headers = {"Authorization": f"Bearer {token}"}  # Add the token to the headers
        # Fetch the current state and revision of the DBCPConnectionPool
        service_response = await client.get(f"{APIUtils.NIFI_URL}/controller-services/{id}", headers=headers)
        if service_response.status_code != 200:
            return {"status_code": service_response.status_code, "error": service_response.text}
        
        # Disable the DBCPConnectionPool using the retrieved revision
        payload = {"revision": service_response.json()['revision'], "state": "DISABLED"}
        disable_response = await client.put(f"{APIUtils.NIFI_URL}/controller-services/{id}/run-status", json=payload, headers=headers)
        
        if disable_response.status_code == 200:
            return {
                "status_code": disable_response.status_code,
                "response": {
                    "id": (disable_response.json()).get('id'),
                    "message": "Operation was successful."  
                }
            }
        else:
            return {
                "status_code": disable_response.status_code,
                "response": disable_response.text,
                "message": "Operation failed." 
            }


@router.post("/process-groups/{id}/empty-all-connections-requests", tags=["API FULL LOAD POSTGRES"])
async def create_empty_all_connections_request(id: str):
    token = await CommonUtils.get_nifi_token()
    
    # Construct the URL to create a request to empty all connections for the specified process group
    url = f"{APIUtils.NIFI_URL}/process-groups/{id}/empty-all-connections-requests"
    
    async with httpx.AsyncClient(verify=False) as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Send a POST request to initiate the empty connections process
        response = await client.post(url, headers=headers)
        
        # Check if the request was accepted
        if response.status_code == 202:  # 202 Accepted indicates the request has been accepted but not yet processed
            response_json = response.json()
            drop_request_id = response_json['dropRequest']['id']
            
            # Construct the URL to check the status of the empty connections request
            status_url = f"{APIUtils.NIFI_URL}/process-groups/{id}/empty-all-connections-requests/{drop_request_id}"
            
            while True:
                # Poll the status URL to check if the empty connections request has been completed
                status_response = await client.get(status_url, headers=headers)
                status_data = status_response.json()
                
                if status_data['dropRequest']['finished']:
                    # Return a success message once the request has finished processing
                    return {"message": "All connections have been emptied successfully.", "details": status_data}
                
                # Wait before checking the status again
                await asyncio.sleep(5)  # Adjust the sleep duration as needed
                
        else:
            # Raise an HTTPException if the initial request to empty connections failed
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to create empty all connections request: {response.text}"
            )


@router.delete("/delete-process-group/{id}", tags=["API FULL LOAD POSTGRES"])
async def delete_process_group(id: str):

    token = await CommonUtils.get_nifi_token()

    # Generate a random UUID for clientId
    clientId = str(uuid.uuid4())

    # Construct the request URL to get the process group details
    get_url = f"{APIUtils.NIFI_URL}/process-groups/{id}"
    
    async with httpx.AsyncClient(verify=False) as client:
        headers = {"Authorization": f"Bearer {token}"}
        # Fetch the process group details to get the latest version
        get_response = await client.get(get_url, headers=headers)

        if get_response.status_code == 200:
            process_group_data = get_response.json()
            version = process_group_data['revision']['version']
        else:
            raise HTTPException(
                status_code=get_response.status_code,
                detail=f"Failed to retrieve process group details: {get_response.text}"
            )

        # Construct the DELETE request URL
        delete_url = f"{APIUtils.NIFI_URL}/process-groups/{id}"
        
        # Set up query parameters for DELETE request
        params = {
            "version": version,
            "clientId": clientId,
            "disconnectedNodeAcknowledged": "False"
        }

        # Send the DELETE request to the NiFi API
        delete_response = await client.delete(delete_url, params=params, headers=headers)

        # Check if the DELETE request was successful
        if delete_response.status_code == 200:
            return {"message": f"Process group {id} deleted successfully."}
        else:
            raise HTTPException(
                status_code=delete_response.status_code,
                detail=f"Failed to delete process group: {delete_response.text}"
            )