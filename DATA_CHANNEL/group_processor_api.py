from fastapi import Form, HTTPException, APIRouter
import httpx, asyncio, json, random, uuid
from pydantic import BaseModel
from common.utils import APIUtils
from common.utils.CommonUtils import CommonUtils

# Initialize the FastAPI router
router = APIRouter()

# Define the request model for JSON input
class CreateProcessorGroupRequest(BaseModel):
    Group_Name: str
    Username: str

# Asynchronous function to create a processor group in NiFi
async def create_processor_group(request: CreateProcessorGroupRequest):
    token = await CommonUtils.get_nifi_token()  # Lấy token từ NiFi
    if not token:
        raise HTTPException(status_code=401, detail="Failed to get NiFi token")

    # Retrieve the NiFi root id
    id = APIUtils.IDROOT

    async with httpx.AsyncClient(verify=False) as client:
        url = f"{APIUtils.NIFI_URL}/process-groups/{id}/process-groups"  # Construct the NiFi API URL

        # Generate random X and Y positions between 0 and 500
        positionX = random.uniform(0, 500)
        positionY = random.uniform(0, 500)

        # Generate a random UUID for clientId
        clientId = str(uuid.uuid4())

        payload = {
            "component": {
                "name": request.Group_Name,  # Set the name of the processor group from the request
                "position": {
                    "x": positionX,  # Set the random X position
                    "y": positionY  # Set the random Y position
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

        # Make the POST request to NiFi
        response = await client.post(url, json=payload, headers=headers)

        # Check if the response status is 'Created'
        if response.status_code == 201:
            return {
                "Client id": (response.json())['revision']['clientId'],  # Return the client ID
                "Version processor group": (response.json())['revision']['version'],  # Return the version
                "Id new processor_group": (response.json())['id'],  # Return the ID of the processor group
                "Position X": positionX,  # Return the randomly generated X position
                "PositionY": positionY, # Return the randomly generated Y position
                "Group name": request.Group_Name,
                "Username": request.Username
            }
        else:
            raise HTTPException(status_code=response.status_code,
                                detail=response.text)  # Raise an HTTP exception if the request fails

# FastAPI endpoint to create a processor group
@router.post("/create_processor_group/", tags=["DATA_CHANNEL"])
async def create_processor_group_endpoint(request: CreateProcessorGroupRequest):
    # Call the function to create a processor group and return the result
    result = await create_processor_group(request)
    return result

@router.post("/start-job/{id}", tags=["DATA_CHANNEL"])
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


@router.post("/stop-job/{id}", tags=["DATA_CHANNEL"])
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


@router.put("/enable-dbcp-connection-pool/{id}", tags=["DATA_CHANNEL"])
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
        enable_response = await client.put(f"{APIUtils.NIFI_URL}/controller-services/{id}/run-status", json=payload,
                                           headers=headers)

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


@router.put("/disable-dbcp-connection-pool/{id}", tags=["DATA_CHANNEL"])
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
        disable_response = await client.put(f"{APIUtils.NIFI_URL}/controller-services/{id}/run-status", json=payload,
                                            headers=headers)

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


@router.post("/process-groups/{id}/empty-all-connections-requests", tags=["DATA_CHANNEL"])
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


@router.delete("/delete-process-group/{id}", tags=["DATA_CHANNEL"])
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