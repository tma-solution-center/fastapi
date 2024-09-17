import logging.config
import math
from http.client import BAD_REQUEST, OK, INTERNAL_SERVER_ERROR
from io import BytesIO
from typing import Dict
import pandas as pd
from DATA_MODEL.DataModelEnum import DataModelEnum
from DATA_MODEL.query_builder import *
from common.utils.FileUtils import FileUtils
from common.utils.SqlAlchemyUtil import SqlAlchemyUtil
from DATA_MODEL.model import *
from common.config.setting_logger import LOGGING
from common.utils.MinioUtil import MinioUtil
from common.utils.VaultUtils import VaultUtils
from constants import TRINO_CONNECTION_STRING, MINIO_BUCKET_NAME, MINIO_SERVICE_NAME, MINIO_URL_STR, ACCESS_KEY_STR, \
    SECRET_KEY_STR, BUCKET_NAME_STR
from constants import DEFAULT_SCHEMA as SCHEMA
from common.utils.CommonUtils import CommonUtils

logging.config.dictConfig(LOGGING)
logger = logging.getLogger()

TOTAL_ITEMS = "totalItems"
TOTAL_PAGES = "totalPages"
SEARCH_OR_FILTER = "searchOrFilter"
START_INDEX = "startIndex"
vault_utils = VaultUtils()

def get_schema_info(username):
    object_name = f'{username}/schema.JSON'
    minio_client = MinioUtil.get_instance_default()
    if not minio_client.check_file_name_exists(MINIO_BUCKET_NAME, object_name):
        return None
    schema_json = minio_client.get_object(MINIO_BUCKET_NAME, object_name)
    schema_obj = SchemaInfo(**schema_json)
    return schema_obj


def case_update_filed_data_model_table_dtos(request: DataModelRequest[FieldDto], tables: list[TableDto]):
    try:
        table_name_format = CommonUtils.convert_title_case_to_underscored_string(request.table_name)
        if DataModelEnum.CREATE_TABLE.get_value() == request.option:
            column_dtos = []
            for item in request.values:
                column_dtos.append(
                    ColumnDto(name=CommonUtils.convert_title_case_to_underscored_string(item.name_column),
                              type=item.type, status=True))

            add_value_init(column_dtos)
            dto = TableDto(table=table_name_format, columns=column_dtos, status=True)
            tables.append(dto)

            for data in request.values:
                data.name_column = CommonUtils.convert_title_case_to_underscored_string(data.name_column)
                data.type = data.type

        if DataModelEnum.ADD_COLUMNS.get_value() == request.option:
            for table_dto in tables:
                if table_dto.table == table_name_format:
                    column_dtos_for_add_columns = table_dto.columns
                    for item in request.values:
                        exists = any(column.name == item.name_column for column in column_dtos_for_add_columns)
                        if not exists:
                            column_dtos_for_add_columns.append(
                                ColumnDto(
                                    name=CommonUtils.convert_title_case_to_underscored_string(item.name_column),
                                    type=item.type, status=True))
                    table_dto.columns = column_dtos_for_add_columns
                    break

            for data in request.values:
                data.name_column = CommonUtils.convert_title_case_to_underscored_string(data.name_column)
                data.type = data.type

        if DataModelEnum.REMOVE_COLUMNS.get_value() == request.option:
            for table_dto in tables:
                if table_dto.table == table_name_format:
                    column_dtos_for_remove_columns = table_dto.columns
                    remove_column_name = CommonUtils.convert_title_case_to_underscored_string(
                        request.drop_column_name)
                    column_dtos_for_remove_columns = [data for data in column_dtos_for_remove_columns if
                                                      data.name != remove_column_name]

                    table_dto.columns = column_dtos_for_remove_columns
                    break
            request.drop_column_name = CommonUtils.convert_title_case_to_underscored_string(
                request.drop_column_name)

        if DataModelEnum.RENAME_TABLE.get_value() == request.option:
            for table_dto in tables:
                if table_dto.table == table_name_format:
                    table_dto.table = CommonUtils.convert_title_case_to_underscored_string(request.new_table_name)
                    break

            request.table_name = table_name_format
            request.new_table_name = CommonUtils.convert_title_case_to_underscored_string(request.new_table_name)

        if DataModelEnum.DROP_TABLE.get_value() == request.option:
            tables = [table_dto for table_dto in tables if table_dto.table != table_name_format]
            request.table_name = table_name_format

        if DataModelEnum.RENAME_COLUMN.get_value() == request.option:
            old_column = CommonUtils.convert_title_case_to_underscored_string(request.old_column)
            for table_dto in tables:
                if table_dto.table == table_name_format:
                    columns_for_rename_column = table_dto.columns
                    for column_dto in columns_for_rename_column:
                        if old_column == column_dto.name:
                            column_dto.name = CommonUtils.convert_title_case_to_underscored_string(request.new_column)
                            request.old_column = old_column
                            request.new_column = CommonUtils.convert_title_case_to_underscored_string(
                                request.new_column)
                            request.old_type = CommonUtils.convert_title_case_to_underscored_string(request.old_type)
                    break
        return tables
    except Exception as e:
        logger.error(f"Occur error when {request.option}: {e} ")
        raise e


def handle_add_update_delete(request: DataModelRequest):
    query = ""
    message = ""
    # Create new table
    if DataModelEnum.CREATE_TABLE.get_value() == request.option:
        iceberg_obj = IcebergTable(**{
            "table_name": request.table_name,
            "username": request.username,
            "option": request.option,
            "values": [Column(name_column=column.name_column, type=column.type) for column in
                       request.values]
        })
        query = generate_sql_create_table(iceberg_obj)
        message = "Table was created successfully"
    # Add new column
    if DataModelEnum.ADD_COLUMNS.get_value() == request.option:
        iceberg_obj = IcebergTable(**{
            "table_name": request.table_name,
            "username": request.username,
            "option": request.option,
            "values": [Column(name_column=column.name_column, type=column.type) for column in
                       request.values]
        })
        query = generate_sql_add_column(iceberg_obj)
        message = "New column was added successfully"
    # Remove column
    if DataModelEnum.REMOVE_COLUMNS.get_value() == request.option:
        remove_column_obj = RemoveColumns(
            table_name=request.table_name,
            username=request.username,
            option=request.option,
            drop_column_name=request.drop_column_name)
        query = generate_sql_remove_columns(remove_column_obj)
        message = "Column was removed successfully"
    if DataModelEnum.DROP_TABLE.get_value() == request.option:
        drop_table_obj = DropTable(table_name=request.table_name,
                                   username=request.username,
                                   option=request.option)
        query = generate_sql_drop_table(drop_table_obj)
        message = "Table was dropped successfully"
    # Rename column
    if DataModelEnum.RENAME_COLUMN.get_value() == request.option:
        rename_column_obj = RenameColumn(table_name=request.table_name,
                                         username=request.username,
                                         option=request.option,
                                         old_column=request.old_column,
                                         old_type=request.old_type,
                                         new_column=request.new_column)
        query = generate_sql_rename_column(rename_column_obj)
        message = "Column was renamed successfully"
    # Insert row
    if DataModelEnum.INSERT_ROW.get_value() == request.option:
        list_rows = [
            InsertColumns(column_name=item.column_name, column_value=item.column_value, column_type=item.column_type)
            for item in request.values]
        insert_object = Insert(table_name=request.table_name,
                               username=request.username,
                               option=request.option,
                               values=list_rows)
        query = insert_row_query_builder(insert_object)
        message = "Insert rows successfully"

    # Replace and edit
    if DataModelEnum.REPLACE_AND_EDIT_ROW.get_value() == request.option:
        list_set = [
            UpdateColumns(update_column=item.update_column, update_value=item.update_value,
                          update_type=item.update_type)
            for item in request.set]
        list_where = [
            WhereUpdateColumns(column=item.column, value=item.value,
                               type=item.type, column_type=item.column_type, op=item.op)
            for item in request.where]
        replace_values_obj = ReplaceAndEdit(table_name=request.table_name,
                                            username=request.username,
                                            option=request.option,
                                            set=list_set,
                                            where=list_where)
        query = replace_and_edit_row_query_builder(replace_values_obj)
        message = "Replace values successfully"

    # Drop all rows
    if DataModelEnum.DROP_ALL_ROW.get_value() == request.option:
        drop_all_rows_obj = DropAllRow(table_name=request.table_name,
                                       username=request.username,
                                       option=request.option)
        query = generate_sql_drop_all_row(drop_all_rows_obj)
        message = "Drop all rows successfully"

    # execute query
    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        if query == "" or (isinstance(query, list) and len(query) == 0):
            message = "Query is empty"
            status_code = BAD_REQUEST
            return message, status_code

        if isinstance(query, list):
            sql_alchemy_util.execute_multiple_queries(query)
        else:
            sql_alchemy_util.execute_query(query)

        logger.info(message)
        status_code = OK
        return message, status_code
    except Exception as e:
        logger.error(e)
        status_code = INTERNAL_SERVER_ERROR
        return str(e), status_code


def process_update_status_column(table_name: str, fields: list[str], schema_obj: SchemaInfo) -> bool:
    table_dto_optional = next((table_dto for table_dto in schema_obj.schema.tables if table_dto.table == table_name),
                              None)
    if table_dto_optional:
        for column_dto in table_dto_optional.columns:
            if column_dto.name in fields:
                column_dto.status = not column_dto.status

    return True


def process_update_status_table(table_name: str, schema_obj: SchemaInfo) -> bool:
    table_dto_optional = next((table_dto for table_dto in schema_obj.schema.tables if table_dto.table == table_name),
                              None)
    if table_dto_optional:
        table_dto_optional.status = not table_dto_optional.status
    return True


def get_header_table_to_filter(table_name: str, username: str) -> list[str]:
    schema_obj = get_schema_info(username)
    table_dto = next((t for t in schema_obj.schema.tables if t.table == table_name), TableDto())

    if not table_dto.columns:
        return []

    data = [
        column.name for column in table_dto.columns
        if column.status
    ]
    return data


def get_total_items(database: str, table_name: str, filter_str: str):
    query_builder = generate_get_total_items(table_name, filter_str)

    # execute query
    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        return sql_alchemy_util.execute_count_query(query_builder)
    except Exception as e:
        logger.error(e)
        raise e


def get_value_for_pagination(request_paging: RequestPaging[DetailsTableDto], database: str, count: bool) -> Dict[
    str, Any]:
    search_or_filter = ""
    id_old_version = request_paging.filters.idOldVersion
    table = request_paging.filters.tableName
    if request_paging.filters.filter and request_paging.filters.filter.strip():
        search_or_filter = request_paging.filters.filter

    if request_paging.filters.search and request_paging.filters.search.strip():
        search_or_filter = request_paging.filters.search

    if id_old_version and id_old_version.strip():
        table += f" FOR VERSION AS OF {id_old_version}"

    start_index = request_paging.page * request_paging.size
    if count:
        total_items = get_total_items(database, table, search_or_filter)
        total_pages = math.ceil(total_items / request_paging.size)
        return {
            SEARCH_OR_FILTER: search_or_filter,
            TOTAL_ITEMS: total_items,
            TOTAL_PAGES: total_pages,
            START_INDEX: start_index
        }

    return {
        SEARCH_OR_FILTER: search_or_filter,
        START_INDEX: start_index
    }


def view_total_item_and_page(request_paging: RequestPaging[DetailsTableDto]) -> PaginationResponse:
    try:
        username = request_paging.username
        database = SCHEMA
        value_for_pagination = get_value_for_pagination(request_paging, database, True)
        total_items = value_for_pagination.get(TOTAL_ITEMS, 0)
        total_pages = value_for_pagination.get(TOTAL_PAGES, 0)

        return PaginationResponse(
            totalItems=total_items,
            totalPages=total_pages
        )
    except Exception as e:
        logger.error(str(e))
        raise e


def get_all_data_table(request_paging: RequestPaging[DetailsTableDto]) -> PaginationResponse:
    try:
        username = request_paging.username
        database = SCHEMA
        value_for_pagination = get_value_for_pagination(request_paging, database, True)
        search_or_filter = value_for_pagination.get(SEARCH_OR_FILTER, "")
        start_index = value_for_pagination.get(START_INDEX, 0)
        schema_obj = get_schema_info(username)

        data = get_data_from_table(database, request_paging.filters.tableName, request_paging.size, start_index,
                                   search_or_filter)

        result = map_data_according_to_schema(schema_obj, request_paging.filters.tableName, data)
        data_just_have_key = get_key_from_list_map(result)
        if data_just_have_key:
            return PaginationResponse(
                content=[],
                page=request_paging.page,
                size=request_paging.size,
                keys=data_just_have_key
            )

        return PaginationResponse(
            content=result,
            page=request_paging.page,
            size=request_paging.size,
            keys=get_key_set(result)
        )
    except Exception as e:
        logger.error(str(e))
        raise e


def get_all_data_table_old_version(request_paging: RequestPaging[DetailsTableDto]) -> PaginationResponse:
    try:
        username = request_paging.username
        database = SCHEMA
        value_for_pagination = get_value_for_pagination(request_paging, database, True)
        search_or_filter = value_for_pagination.get(SEARCH_OR_FILTER, "")
        start_index = value_for_pagination.get(START_INDEX, 0)

        table_old_version = f"{request_paging.filters.tableName}  FOR VERSION AS OF {request_paging.filters.idOldVersion}"

        data = get_data_from_table(database, table_old_version, request_paging.size, start_index,
                                   search_or_filter)
        result = []
        for item in data:
            result.append(CommonUtils.convert_value_in_dict_to_str(item, "%Y-%m-%d %H:%M:%S"))
        data_just_have_key = get_key_from_list_map(result)
        if data_just_have_key:
            return PaginationResponse(
                content=[],
                page=request_paging.page,
                size=request_paging.size,
                keys=data_just_have_key
            )

        return PaginationResponse(
            content=result,
            page=request_paging.page,
            size=request_paging.size,
            keys=get_key_set(result)
        )
    except Exception as e:
        logger.error(str(e))
        raise e


def get_data_from_table(database: str, table: str, limit: int, offset: int, filter_str: str):
    query_builder = generate_get_data_from_table(table, limit, offset, filter_str)
    # execute query
    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        data = sql_alchemy_util.execute_query_to_get_data(query_builder)
        return data

    except Exception as e:
        logger.error(str(e))
        raise e


def get_version(table: str, user_info: UserInfo):
    username = user_info.username
    database = SCHEMA
    table_version = f"\"{table}$history\""
    data = get_data_from_table(database, table_version, -1, 0, "")
    result = []
    for item in data:
        item['committed_at'] = item.pop('made_current_at')
        result.append(CommonUtils.convert_value_in_dict_to_str(item, "%Y-%m-%d %H:%M:%S"))

    return result


def restore(request: RestoreDto):
    username = request.username
    database = SCHEMA
    schema_obj = get_schema_info(username)
    columns_list = get_columns_table(schema_obj, request.table_name)
    common_elements = list(set(columns_list).intersection(request.shorter_list))
    request.shorter_list = common_elements
    restore_query = generate_restore_query(database, request)

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        sql_alchemy_util.execute_query(restore_query)
        return
    except Exception as e:
        logger.error((str(e)))
        raise e


def process_snapshot_retention(request: DataModelRequest[FieldDto]):
    username = request.username
    database = SCHEMA
    sql_str = snapshot_retention_query_builder(
        SnapshotRetention(table_name=request.table_name, username=request.username, option=request.option,
                          seconds=request.seconds))

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        sql_alchemy_util.execute_query(sql_str)
        return
    except Exception as e:
        logger.error(str(e))
        raise e


def process_download_data(request: DownloadDataDto):
    # Generate query get list file name
    query = generate_get_list_parquet_file_path_query(request.table)
    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        list_file_path = sql_alchemy_util.execute_query_to_get_data(query)
        list_object_key = []

        if not list_file_path or len(list_file_path) == 0:
            return None

        for file_path in list_file_path:
            parts = file_path['file_path'].split('/')
            list_object_key.append('/'.join(parts[3:]))

        dataframes = []
        bucket_name = "cdp"
        minio_client = MinioUtil.get_instance_default()
        # get parquet file from minio
        for file_path in list_object_key:
            df = minio_client.fetch_parquet_file(bucket_name, file_path)
            if not df.empty:
                dataframes.append(df)

        if dataframes:
            final_df = pd.concat(dataframes, ignore_index=True)

            csv_buffer = BytesIO()
            final_df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            return csv_buffer
        else:
            logger.info("Table no data")
            return BytesIO().seek(0)

    except Exception as e:
        logger.error(str(e))
        raise e


def process_download_data_for_page(request: List[Dict[str, str]]):
    results_converted = convert_list_map_to_dict(request)
    file_utils = FileUtils("output.csv")
    datas = results_converted.get("data", [])
    headers = results_converted.get("header", [])
    return file_utils.csv_parser(headers, datas)


def map_data_according_to_schema(schema_obj, table, datas):
    columns_list = get_columns_table(schema_obj, table)
    results = []

    if not columns_list:
        return []

    if not datas:
        for column in columns_list:
            new_results = {column: None}
            results.append(new_results)
        return results

    for entry in datas:
        new_results = {column: str(entry.get(column, "")) for column in columns_list}
        results.append(new_results)

    return results


def get_columns_table(schema_obj, table):
    get_table = next(
        (table_dto for table_dto in schema_obj.schema.tables if table_dto.table == table),
        TableDto(table="", columns=[], status=True)
    )

    return [column_dto.name for column_dto in get_table.columns if column_dto.status]


def get_key_from_list_map(data: List[Dict[str, str]]) -> List[str]:
    return [
        key
        for map_ in data
        if all(value is None for value in map_.values())
        for key in map_.keys()
    ]


def get_key_set(results: List[Dict[str, str]]) -> List[str]:
    keys_list = []
    if results:
        keys_list = list(results[0].keys())
    return keys_list


def add_value_init(column_dtos: list):
    column_dtos.append(ColumnDto(name="cdp_id", type="string", status=True))
    column_dtos.append(ColumnDto(name="customer_unified_key", type="int", status=True))
    column_dtos.append(ColumnDto(name="datekey", type="int", status=True))


def convert_list_map_to_dict(maps: List[Dict[str, str]]) -> Dict[str, Any]:
    datas = []
    header = [key for key in maps[0].keys()]

    for map_item in maps:
        data = list(map_item.values())
        datas.append(data)

    return {"data": datas, "header": header}


def check_connection_for_data_storage_info(request: DataStorageInfo):
    minio_client = MinioUtil.get_instance(request.minio_url, request.access_key, request.secret_key)
    try:
        if request.type == MINIO_SERVICE_NAME:
            is_connected, bucket_is_exists = minio_client.check_connect_and_check_bucket_exists(request.bucket_name)
            if is_connected:
                if bucket_is_exists:
                    return True, True, f"Bucket '{request.bucket_name}' exists. Connection successful!"
                return True, False, f"Bucket '{request.bucket_name}' not exists. Connection successful!"

        if request.type == 's3':
            # todo: implement check connection for s3
            return False, False, "Failed to connect Minio"

        return False, False, "Failed to connect Minio"
    except Exception as e:
        return False, False, f"Failed to connect Minio: {str(e)}"


def add_update_data_storage_info(request: DataStorageInfo):
    is_connected, bucket_is_exists, message = check_connection_for_data_storage_info(request)
    # Add or update data storage info to Vault
    try:
        if is_connected and bucket_is_exists:
            vault_data = {
                ACCESS_KEY_STR: request.access_key,
                SECRET_KEY_STR: request.secret_key,
                BUCKET_NAME_STR: request.bucket_name
            }

            if request.type == MINIO_SERVICE_NAME:
                vault_data[MINIO_URL_STR] = request.minio_url

            path = f'{request.username}/{request.type}'
            vault_utils.create_or_update_secret_to_vault(path, vault_data)
            return True
        return False
    except Exception as e:
        logger.error(f"Add or Update data storage info successfully failed: {str(e)}")
        raise e
