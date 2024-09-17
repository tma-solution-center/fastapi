import io
import json
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Path, Request
from starlette.responses import JSONResponse
from DATA_MODEL.helper import *
from DATA_MODEL.model import SchemaInfo, DataModelRequest, SchemaDto, RequestPaging, DetailsTableDto, \
    PaginationResponse, \
    ResponseJson, IcebergTable, RenameColumn, DropAllRow, DropTable, RemoveColumns, Insert, ReplaceAndEdit, \
    UpdateValuesMultiCondition, UpdateNanValue, FieldDto, RestoreDto, DownloadDataDto
from common.utils.MinioUtil import MinioUtil

logging.config.dictConfig(LOGGING)
logger = logging.getLogger()

router = APIRouter()
minio_client = MinioUtil.get_instance_default()


@router.post('/trino/schema/', tags=["DATA_MODEL"])
def get_schema(user_info: UserInfo):
    schema_obj = get_schema_info(user_info.username)
    if schema_obj is None:
        return CommonUtils.handle_response(None, status=200, message='success', status_code=200)

    return CommonUtils.handle_response(schema_obj.model_dump(), status=200, message='success', status_code=200)


@router.post('/trino/add-update-delete/', tags=["DATA_MODEL"])
def add_update_delete(request: DataModelRequest[FieldDto]):
    try:
        schema_obj = get_schema_info(request.username)
        if schema_obj is None:
            schema_obj = SchemaInfo(id=None, schema=SchemaDto(), lastModified="")

        schema_dto = schema_obj.schema
        tables = schema_dto.tables

        schema_dto.tables = case_update_filed_data_model_table_dtos(request, tables)
        schema_obj.schema = schema_dto
        schema_obj.lastModified = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # add, update, delete for table or column
        message, status_code = handle_add_update_delete(request)

        if status_code == OK:
            username = request.username
            object_name = f'{username}/schema.JSON'
            json_str = json.dumps(schema_obj.model_dump())
            minio_client.put_object(MINIO_BUCKET_NAME, object_name, CommonUtils.convert_string_to_binary_io(json_str))

        return CommonUtils.handle_response(None, status=status_code, message=message, status_code=status_code)
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Add/Update/Delete Failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.put('/trino/update-status/{table}', tags=["DATA_MODEL"])
async def update_status_column(table: str = Path(...), request: UpdateColumnStatus = None):
    try:
        username = request.username
        schema_obj = get_schema_info(username)
        status_updated = process_update_status_column(table, request.fields, schema_obj)
        message = "Column status was updated successfully"

        object_name = f'{username}/schema.JSON'
        json_str = json.dumps(schema_obj.model_dump())
        minio_client.put_object(MINIO_BUCKET_NAME, object_name, CommonUtils.convert_string_to_binary_io(json_str))

        return CommonUtils.handle_response(status_updated, status=OK, message=message, status_code=OK)
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Update status column failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.put('/trino/update-status-table/{table}', tags=["DATA_MODEL"])
async def update_status_table(table: str = Path(...), user_info: UserInfo = None):
    try:
        username = user_info.username
        schema_obj = get_schema_info(username)
        status_updated = process_update_status_table(table, schema_obj)
        message = "Table status was updated successfully"

        object_name = f'{username}/schema.JSON'
        json_str = json.dumps(schema_obj.model_dump())
        minio_client.put_object(MINIO_BUCKET_NAME, object_name, CommonUtils.convert_string_to_binary_io(json_str))

        return CommonUtils.handle_response(status_updated, status=OK, message=message, status_code=OK)
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Update status table failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post('/trino/header-table-to-filter/{table}', tags=["DATA_MODEL"])
async def header_table_to_filter(table: str = Path(...), user_info: UserInfo = None):
    try:
        return CommonUtils.handle_response(get_header_table_to_filter(table, user_info.username), status=OK,
                                           message="Success",
                                           status_code=OK)
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Get header filter failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post("/trino/view-total-item-and-page", response_model=ResponseJson[PaginationResponse])
async def view_total_item_and_page_table(request_paging: RequestPaging[DetailsTableDto]):
    try:
        pagination_response = view_total_item_and_page(request_paging)
        response = CommonUtils.handle_response(data=pagination_response, status=OK, message="Success", status_code=OK)
        return response
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Get total record failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post("/trino/view-total-item-and-page-table-old-version", response_model=ResponseJson[PaginationResponse])
async def view_total_item_and_page_old_version(request_paging: RequestPaging[DetailsTableDto]):
    try:
        pagination_response = view_total_item_and_page(request_paging)
        response = CommonUtils.handle_response(data=pagination_response, status=OK, message="Success", status_code=OK)
        return response
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Get total record failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post("/trino/get-data-from-table", response_model=ResponseJson[PaginationResponse])
async def get_data(request_paging: RequestPaging[DetailsTableDto]):
    try:
        pagination_response = get_all_data_table(request_paging)
        response = CommonUtils.handle_response(data=pagination_response, status=OK, message="Success", status_code=OK)
        return response
    except Exception as e:
        logger.error(str(e))
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Get data failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post("/trino/get-data-from-table-old-version", response_model=ResponseJson[PaginationResponse])
async def get_data_old_version(request_paging: RequestPaging[DetailsTableDto]):
    try:
        pagination_response = get_all_data_table_old_version(request_paging)
        response = CommonUtils.handle_response(data=pagination_response, status=OK, message="Success", status_code=OK)
        return response
    except Exception as e:
        logger.error(str(e))
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Get data failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post('/trino/get-version-from-table/{table}', tags=["DATA_MODEL"])
async def get_version_from_table(table: str = Path(...), user_info: UserInfo = None):
    try:
        return CommonUtils.handle_response(get_version(table, user_info), status=OK, message="Success",
                                           status_code=OK)
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Get version of table failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post("/trino/restore-version")
async def restore_version(request: RestoreDto):
    try:
        restore(request)
        return CommonUtils.handle_response(None, status=OK, message="Success",
                                           status_code=OK)
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Restore version failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post('/trino/create_table/', tags=["DATA_MODEL"])
def create_table(request: IcebergTable):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = generate_sql_create_table(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200, content={"message": "Table was created successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


@router.post('/trino/add_columns/', tags=["DATA_MODEL"])
def add_columns(request: IcebergTable):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    query_arr = generate_sql_add_column(request)
    try:
        for query in query_arr:
            sqlAlchemyUtil.execute_query(query)
        return JSONResponse(status_code=200, content={"message": "Columns was added successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


@router.post('/trino/rename_column/', tags=["DATA_MODEL"])
def rename_column(request: RenameColumn):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    query = generate_sql_rename_column(request)
    try:
        sqlAlchemyUtil.execute_query(query)
        return JSONResponse(status_code=200, content={"message": "Column was renamed successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


# drop all row
@router.post("/trino/drop_all_row/", tags=["DATA_MODEL"])
def drop_all_row(request: DropAllRow):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = generate_sql_drop_all_row(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200, content={"message": "Drop all row columns successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


# drop table
@router.delete("/trino/drop_table/", tags=["DATA_MODEL"])
def drop_table(request: DropTable):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = generate_sql_drop_table(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200, content={"message": "Drop table successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


# remove columns
@router.post("/trino/remove_columns/", tags=["DATA_MODEL"])
def remove_columns(request: RemoveColumns):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = generate_sql_remove_columns(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200, content={"message": "Remove columns successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


@router.post("/trino/insert/", tags=["DATA_MODEL"])
def insert(request: Insert):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = insert_row_query_builder(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200, content={"message": "Insert successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


@router.post("/trino/replace_edit_row/", tags=["DATA_MODEL"])
def replace_edit_row(request: ReplaceAndEdit):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = replace_and_edit_row_query_builder(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200, content={"message": "Replace and edit row successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


@router.post("/trino/snapshot_retention/", tags=["DATA_MODEL"])
def snapshot_retention(request: DataModelRequest[FieldDto]):
    try:
        process_snapshot_retention(request)
        return CommonUtils.handle_response(None, status=OK, message="Snapshot retention successfully",
                                           status_code=OK)
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Restore version failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post("/trino/update_values/", tags=["DATA_MODEL"])
def update_values(request: UpdateValuesMultiCondition):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = update_values_multi_condition(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200, content={"message": "Update values multi condition successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


@router.post("/trino/update_nan_value/", tags=["DATA_MODEL"])
def update_nan(request: UpdateNanValue):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    sql_str = update_nan_value(request)
    try:
        sqlAlchemyUtil.execute_query(sql_str)
        return JSONResponse(status_code=200, content={"message": "Update nan values successfully"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"message": str(e)})


@router.post("/trino/download-data", tags=["DATA_MODEL"])
async def download_data(request: DownloadDataDto):
    try:
        byte_array_output_stream = process_download_data(request)
        byte_array_io = io.BytesIO(byte_array_output_stream.getvalue())
        headers = {
            "Content-Disposition": "attachment; filename=output.csv",
            "Content-Type": "application/octet-stream",
        }
        return StreamingResponse(byte_array_io, headers=headers)
    except Exception as e:
        logger.error(e)
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Download data failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post("/trino/download-data-for-page", tags=["DATA_MODEL"])
async def download_data_for_page(request: List[Dict[str, str]]):
    try:
        byte_array_output_stream = process_download_data_for_page(request)
        byte_array_io = io.BytesIO(byte_array_output_stream.getvalue())
        headers = {
            "Content-Disposition": "attachment; filename=output.csv",
            "Content-Type": "application/octet-stream",
        }
        return StreamingResponse(byte_array_io, headers=headers)
    except Exception as e:
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR, message="Download data failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post("/trino/check-connection-data-storage", tags=["DATA_MODEL"])
async def check_connection_data_storage(request: DataStorageInfo):
    try:
        check_connection, check_bucket, message = check_connection_for_data_storage_info(request)
        if not check_connection:
            return CommonUtils.handle_response({'check_connection': check_connection, 'check_bucket': check_bucket},
                                               status=BAD_REQUEST, message=message, status_code=BAD_REQUEST)
        return CommonUtils.handle_response({'check_connection': check_connection, 'check_bucket': check_bucket},
                                           status=OK, message=message, status_code=OK)
    except Exception as e:
        return CommonUtils.handle_response(False, status=INTERNAL_SERVER_ERROR, message="Connect data storage failed",
                                           status_code=INTERNAL_SERVER_ERROR)


@router.post("/trino/add-update-data-storage", tags=["DATA_MODEL"])
async def add_update_data_storage(request: DataStorageInfo):
    try:
        status = add_update_data_storage_info(request)
        if not status:
            return CommonUtils.handle_response(False, status=BAD_REQUEST,
                                               message="Add or Update data storage info failed",
                                               status_code=BAD_REQUEST)

        return CommonUtils.handle_response(True, status=OK,
                                           message="Add or Update data storage info successfully", status_code=OK)
    except Exception as e:
        return CommonUtils.handle_response(None, status=INTERNAL_SERVER_ERROR,
                                           message="Add or Update data storage info failed",
                                           status_code=INTERNAL_SERVER_ERROR)
