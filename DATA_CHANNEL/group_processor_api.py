from fastapi import HTTPException, APIRouter
import httpx, asyncio, random, uuid
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error
import psycopg2
from psycopg2 import OperationalError, sql
from DATA_CHANNEL.model import ConnectionDetails, DataChannel
from common.utils import APIUtils
from common.utils.APIUtils import mysql_connection_string
from common.utils.CommonUtils import CommonUtils
from typing import Optional

from common.utils.SqlAlchemyUtil import SqlAlchemyUtil

# Initialize the FastAPI router
router = APIRouter()

# Define the request model for JSON input
class ProcessorGroupRequest(BaseModel):
    Group_Name: Optional[str] = None
    Username: Optional[str] = None
    id: Optional[str] = None


# @router.post("/test_connection/mysql")
# def test_mysql_connection(details: ConnectionDetails):
#     connection = None
#     try:
#         connection = mysql.connector.connect(
#             host=details.Host,
#             port=details.Port,
#             database=details.Database_Name,
#             user=details.Database_User,
#             password=details.Password
#         )
#         if connection.is_connected():
#             return {"status": 200, "result": True}
#     except Error as e:
#         raise HTTPException(status_code=500, detail=f"Connection failed: {e}")
#     finally:
#         if connection and connection.is_connected():
#             connection.close()

@router.post("/test_connection/mysql")
def test_mysql_connection(details: ConnectionDetails):
    connection = None
    try:
        # Establish connection to the MySQL database
        connection = mysql.connector.connect(
            host=details.Host,
            port=details.Port,
            database=details.Database_Name,
            user=details.Database_User,
            password=details.Password
        )

        # If connection is successful
        if connection.is_connected():
            cursor = connection.cursor()

            # If Col_Name is provided, check if the column exists
            if details.Col_Name:
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name = %s",
                    (details.Database_Name, details.Table_Name, details.Col_Name)
                )
                column_exists = cursor.fetchone()[0]

                # Return True if the column exists, otherwise False
                return {"status": 200, "result": column_exists == 1,
                        "message": f"Column '{details.Col_Name}' exists." if column_exists else f"Column '{details.Col_Name}' not found."}

            # If Col_Name is not provided, check if the table exists
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
                (details.Database_Name, details.Table_Name)
            )
            table_exists = cursor.fetchone()[0]

            # Return True if the table exists, otherwise False
            return {"status": 200, "result": table_exists == 1,
                    "message": f"Table '{details.Table_Name}' exists." if table_exists else f"Table '{details.Table_Name}' not found."}

    except mysql.connector.Error as e:
        return {"status": 500, "result": False, "message": f"Connection failed: {e}"}
    finally:
        if connection and connection.is_connected():
            connection.close()

    # In case connection is never established or fails silently
    return {"status": 500, "result": False, "message": "Connection failed."}

@router.post("/test_connection/postgresql")
def test_postgresql_connection(details: ConnectionDetails):
    connection = None
    try:
        # Establish connection to the PostgreSQL database
        connection = psycopg2.connect(
            host=details.Host,
            port=details.Port,
            dbname=details.Database_Name,
            user=details.Database_User,
            password=details.Password
        )

        # If connection is successful
        if connection:
            cursor = connection.cursor()

            # If Col_Name is provided, check if the column exists
            if details.Col_Name:
                cursor.execute(
                    sql.SQL(
                        "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s AND column_name = %s"
                    ),
                    [details.Table_Name, details.Col_Name]
                )
                column_exists = cursor.fetchone()[0]

                # Return True if the column exists, otherwise False
                return {"status": 200, "result": column_exists == 1,
                        "message": f"Column '{details.Col_Name}' exists." if column_exists else f"Column '{details.Col_Name}' not found."}

            # If Col_Name is not provided, check if the table exists
            cursor.execute(
                sql.SQL(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s"),
                [details.Table_Name]
            )
            table_exists = cursor.fetchone()[0]

            # Return True if the table exists, otherwise False
            return {"status": 200, "result": table_exists == 1,
                    "message": f"Table '{details.Table_Name}' exists." if table_exists else f"Table '{details.Table_Name}' not found."}

    except psycopg2.OperationalError as e:
        return {"status": 500, "result": False, "message": f"Connection failed: {e}"}
    finally:
        if connection:
            connection.close()

    # In case connection is never established or fails silently
    return {"status": 500, "result": False, "message": "Connection failed."}

# Asynchronous function to create a processor group in NiFi
async def create_processor_group(request: ProcessorGroupRequest):
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
            insert_query = f"""
                INSERT INTO {APIUtils.catalog}.parent_group (group_id, group_name, client_name)
                VALUES ('{(response.json())['id']}', '{request.Group_Name}', '{request.Username}');
            """
            # execute query
            sqlalchemy = SqlAlchemyUtil(connection_string=mysql_connection_string)
            sqlalchemy.execute_query(insert_query)

            return {
                "Client_id": (response.json())['revision']['clientId'],  # Return the client ID
                "Version_processor_group": (response.json())['revision']['version'],  # Return the version
                "Id_new_processor_group": (response.json())['id'],  # Return the ID of the processor group
                "Position_X": positionX,  # Return the randomly generated X position
                "Position_Y": positionY, # Return the randomly generated Y position
                "Group_name": request.Group_Name,
                "Username": request.Username
            }
        else:
            raise HTTPException(status_code=response.status_code,
                                detail=response.text)  # Raise an HTTP exception if the request fails

# FastAPI endpoint to create a processor group
@router.post("/create_processor_group/", tags=["DATA_CHANNEL"])
async def create_processor_group_endpoint(request: ProcessorGroupRequest):
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

    # update_query = f"""
    #     INSERT INTO {APIUtils.catalog}.data_channel (pipe_id, pipeline_name, source_name, status_pipeline, json_file
    #     created_at, update_at, group_id)
    #     VALUES ('{(upload_response.json())['id']}', '{request.Group_Name}', 'mysql', 'start', null, null, '{id}');
    # """
    # execute query
    sqlalchemy = SqlAlchemyUtil(connection_string=mysql_connection_string)
    # sqlalchemy.execute_query(update_query)

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

# Function to get processors by name
async def check_processor_by_name(request: ProcessorGroupRequest):
    try:
        # Ensure token is available
        token = await CommonUtils.get_nifi_token()  # Lấy token từ NiFi
        if not token:
            raise HTTPException(status_code=401, detail="Failed to get NiFi token")

        headers = {
            "Authorization": f"Bearer {token}"
        }

        process_group_id = request.id if request.id and request.id != "root" else APIUtils.IDROOT

        async with httpx.AsyncClient(verify=False) as client:
            # Get the root process group details
            response = await client.get(f"{APIUtils.NIFI_URL}/flow/process-groups/{process_group_id}", headers=headers)
            response.raise_for_status()
            root_process_group_flow = response.json()

            # Extract process groups
            process_groups = root_process_group_flow.get('processGroupFlow', {}).get('flow', {}).get('processGroups',
                                                                                                     [])
            # Find processor by name
            # Check if the group exists by name
            for process_group in process_groups:
                if process_group['component']['name'] == request.Group_Name:
                    return {"exists": True, "id": process_group['component']['id']}

            # Return false if not found
            return {"exists": False}

    except httpx.HTTPStatusError as e:
        print(f"HTTP Status Error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to get processor: {e}")
    except httpx.RequestError as e:
        print(f"Request Error: {e}")
        raise HTTPException(status_code=500, detail=f"Request to NiFi failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# API endpoint to get processor ID by name
@router.post("/check-processor-exists/{process_group_id}/{name}", tags=["DATA_CHANNEL"])
async def check_processor_exists(request: ProcessorGroupRequest):
    processor_id = await check_processor_by_name(request)
    if processor_id:
        return {"processor_id": processor_id}
    else:
        raise HTTPException(status_code=404, detail="Processor not found")


@router.get("/data-channel/{id}", tags=["DATA_CHANNEL"])
async def get_data_channel(id: str):
    try:
        insert_query = f"""
                        SELECT * FROM {APIUtils.catalog}.data_channel WHERE `pipe_id` = '{id}'
                    """
        # execute query
        sqlalchemy = SqlAlchemyUtil(connection_string=mysql_connection_string)

        data_list = sqlalchemy.execute_query_to_get_data(insert_query)

        if not data_list:
            raise HTTPException(status_code=404, detail="Data not found.")

        data = data_list[0]
        data_channel = DataChannel(
            pipe_id=data['pipe_id'],
            pipeline_name=data['pipeline_name'],
            source_name=data['source_name'],
            status_pipeline=data.get('status_pipeline'),
            json_file=data.get('json_file'),
            created_at=data['created_at'].isoformat(),
            update_at=data['update_at'].isoformat(),
            group_id=data['group_id']
        )
        return data_channel

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
