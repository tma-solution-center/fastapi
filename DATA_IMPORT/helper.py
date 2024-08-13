from .MinioUtil import MinioUtil
from typing import BinaryIO
from datetime import datetime,timezone
import unicodedata
from typing import List,Optional
from .model import DataImportRequest,ResultModel,TableInfor
import logging
from .SqlAlchemyUtil import SqlAlchemyUtil,CursorResult
from sqlalchemy.exc import ProgrammingError
from trino.exceptions import TrinoUserError
from constants import *
# from VaultUtil import VaultUtil

# VAULT_ADDRESS='http://localhost:8200'
# VAULT_KEY='hvs.sV8GgIzHlxpznnHhbbFhPttX'
# UNSEAL_KEY='cb90c15e7246fe9a535223b13fe50a1dcaa08833f5970763dae3e4bc96268003'
# ENGINE_NAME='kv'
# SECRET_PATH='CDP-OnPremise-Secret'

# vault = VaultUtil(VAULT_ADDRESS,VAULT_KEY,UNSEAL_KEY)
# secrets=vault.get_secret(ENGINE_NAME,SECRET_PATH)

# TRINO_CONECTION_STRING=secrets['TRINO_CONECTION_STRING']
# BUCKET_NAME=secrets['BUCKET_NAME'] 
# RAW_LAYER='secrets['RAW_LAYER'] #RAW'
# ICEBERG_CATALOG=secrets['ICEBERG_CATALOG'] #iceberg
# TEMP_SCHEMA=secrets['TEMP_SCHEMA'] #temp
# DATALAKE_SCHEMA=secrets['DATALAKE_SCHEMA'] #datalake

# HIVE_CATALOG=secrets['HIVE_CATALOG']    #default
# DEFAULT_SCHEMA=secrets['DEFAULT_SCHEMA'] #default

RAW_LAYER = 'RAW'
BUCKET_NAME='datalake'
ICEBERG_CATALOG=TEMP_CATALOG
# TEMP_CHEMA
DATALAKE_SCHEMA=DEFAULT_SCHEMA
# DEFAULT_SCHEMA


logger = logging.getLogger("helper")
logging.basicConfig()
logger.setLevel(logging.INFO)

def remove_accents_and_replace(input_str):
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        result_str = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
        
        result_str = result_str.replace('ă', 'a')\
            .replace('â', 'a').replace('đ', 'd')\
            .replace('ê', 'e').replace('ô', 'o')\
            .replace('ơ', 'o').replace('ư', 'u').replace(' ','_')

        return result_str

def upload_file_to_minio(file_name:str,file_data:BinaryIO,content_type):

    file_name = remove_accents_and_replace(file_name)
    extention=''
    if content_type == 'text/csv':
        dataset_name = file_name.replace('.csv','')
        extention='.csv'
    else: 
        dataset_name=file_name
    utc_now = datetime.now(timezone.utc)
    datetime_suffix = utc_now.strftime("%Y%m%d%H%M%S")
    datatime_as_path=utc_now.strftime("%Y/%m/%d")
    object_name = f"{RAW_LAYER}/{dataset_name}/{datatime_as_path}/{dataset_name}_{datetime_suffix}{extention}"

    minio_util = MinioUtil().get_instance()
    result = minio_util.put_object(BUCKET_NAME,object_name,file_data)
    return {
        "bucket_name":result.bucket_name,
        "object_name":result.object_name,
        "version_id":result.version_id,
        "last_modified":result.last_modified
    }


def create_table_builder(columns:list,table_name:str,external_location:str,file_format:str,delimiter:Optional[str]=None):

    columns_str = ',\n'.join([f"{col} VARCHAR" for col in columns])
    property_expression = ""
    if file_format =="CSV":
         property_expression=f"csv_separator= '{delimiter}',\n skip_header_line_count=1,\n csv_quote='\"',"
    query=f"""
    CREATE TABLE IF NOT EXISTS {HIVE_CATALOG}.{DEFAULT_SCHEMA}.{table_name}(
         {columns_str}
    )
    WITH(
        format = '{file_format}',
        {property_expression}
        external_location='{external_location}'
    )
    """  
    return query


def create_converted_type_table(request:DataImportRequest,raw_table_name:str):
    columns_str=',\n'.join([col.output.column for col in request.columns])
    value_str=',\n'.join([f"TRY_CAST({col.input.column} as {col.output.type}) as {col.input.column}" 
                          if col.output.type.lower()!='varchar' 
                          else col.input.column for col in request.columns])
    utc_now = datetime.now(timezone.utc)
    datetime_suffix = utc_now.strftime("%Y%m%d%H%M%S")
    converted_type_table=f"{request.table_name}_temp_{datetime_suffix}"
    query=f"""
    CREATE TABLE {ICEBERG_CATALOG}.{TEMP_SCHEMA}.{converted_type_table}(
        {columns_str}
    )WITH(
        format='parquet',
        location='s3a://temp/{converted_type_table}/'
    )AS
    SELECT {value_str} from {HIVE_CATALOG}.{DEFAULT_SCHEMA}.{raw_table_name}
    """

    logger.info(f"Create query: {query}")

    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    result = sqlAlchemyUtil.execute_query(query)
    if isinstance(result,CursorResult):
         logger.info(f"{converted_type_table} table was created successfully: {str(result.rowcount)}(effected rows)")
         return TableInfor(ICEBERG_CATALOG,TEMP_SCHEMA,converted_type_table)
    else: 
         return result  

def create_raw_table(request:DataImportRequest):
    columns=[col.input.column for col in request.columns]
    utc_now = datetime.now(timezone.utc)
    datetime_suffix = utc_now.strftime("%Y%m%d%H%M%S")
    source_table_name=f"raw_{request.table_name}_{datetime_suffix}"
    query = create_table_builder(columns,source_table_name,request.input_file_name,
                                 request.type,request.delimiter)
    logger.info(f"Create external table query: {query}")
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    create_result = sqlAlchemyUtil.execute_query(query)
    if isinstance(create_result,ResultModel) and create_result.status==0:
         return create_result
    else:
         logger.info(f"Table {source_table_name} was created successfully")
         return TableInfor(HIVE_CATALOG,DEFAULT_SCHEMA,source_table_name)

def insert(request:DataImportRequest,converted_type_table:str):
    insert_column=', '.join([col.output.column for col in request.columns])
    insert_value=', '.join([col.input.column for col in request.columns])
    utc_now = datetime.now(timezone.utc)
    query=f"""
    INSERT INTO {ICEBERG_CATALOG}.{DATALAKE_SCHEMA}.{request.table_name} 
    (
        {insert_column}
    ) 
    SELECT 
        {insert_value}
    FROM {ICEBERG_CATALOG}.{TEMP_SCHEMA}.{converted_type_table}  
    """


    logger.info(f"Insert query: {query}")

    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sqlAlchemyUtil.execute_query(query)
    except ProgrammingError as e:
        if isinstance(e.orig,TrinoUserError) and e.orig.error_name=="TYPE_MISMATCH":
            logger.error(f"Trino excute failed due to: {str(e)}")
            return ResultModel(-1,"Data import failed due to mismatched column types")
        else: raise e
    if isinstance(result,CursorResult):
        logger.info(f"{request.table_name} table was inserted {str(result.rowcount)} rows")
        return {
            "Number_of_row":result.rowcount
        }
    else: 
        return result
    
def update(request:DataImportRequest,converted_type_table:str):
    key_condition=" AND ".join([f"t.{key.output_key} = s.{key.input_key}" for key in request.key_columns])
    update_set=", ".join([f"{col.output.column} = s.{col.input.column}" for col in request.columns])
    utc_now = datetime.now(timezone.utc)
    updated_at_str=str(utc_now)
    update_query=f"""
    MERGE INTO {ICEBERG_CATALOG}.{DATALAKE_SCHEMA}.{request.table_name} t
    USING {ICEBERG_CATALOG}.{TEMP_SCHEMA}.{converted_type_table} s
    ON {key_condition}
    WHEN MATCHED
    THEN UPDATE SET {update_set}, updatedAt=CAST('{updated_at_str}' as TIMESTAMP)
"""
    logger.info(f"Update query: {update_query}")

    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sqlAlchemyUtil.execute_query(update_query)
    except ProgrammingError as e:
        if isinstance(e.orig,TrinoUserError) and e.orig.error_name=="TYPE_MISMATCH":
            logger.error(f"Trino excute failed due to: {str(e)}")
            return ResultModel(-1,"Data import failed due to mismatched column types")
        else: raise e
    if isinstance(result,CursorResult):
        logger.info(f"{request.table_name} table was updated {str(result.rowcount)} rows")
        return {
            "Number_of_row":result.rowcount
        }
    else: 
        return result
    
def upsert(request: DataImportRequest,converted_type_table:str):
    key_condition=" AND ".join([f"t.{key.output_key} = s.{key.input_key}" for key in request.key_columns])
    update_set=", ".join([f"{col.output.column} = s.{col.input.column}" for col in request.columns])
    insert_column=", ".join([col.output.column for col in request.columns])
    insert_value=", ".join([f"s.{col.input.column}" for col in request.columns])
    utc_now = datetime.now(timezone.utc)
    updated_at_str=str(utc_now)
    datekey = utc_now.strftime("%Y%m%d")

    upsert_query=f"""
    MERGE INTO {ICEBERG_CATALOG}.{DATALAKE_SCHEMA}.{request.table_name} t
    USING {ICEBERG_CATALOG}.{TEMP_SCHEMA}.{converted_type_table} s
    ON {key_condition}
    WHEN MATCHED
        THEN UPDATE SET {update_set}, updatedAt=CAST('{updated_at_str}' as TIMESTAMP)
    WHEN NOT MATCHED
        THEN INSERT (
            {insert_column}
        ) 
        VALUES (
            {insert_value}
        )
"""
    logger.info(f"Upsert query: {upsert_query}")

    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sqlAlchemyUtil.execute_query(upsert_query)
    except ProgrammingError as e:
        if isinstance(e.orig,TrinoUserError) and e.orig.error_name=="TYPE_MISMATCH":
            logger.error(f"Trino excute failed due to: {str(e)}")
            return ResultModel(-1,"Data import failed due to mismatched column types")
        else: raise e
    if isinstance(result,CursorResult):
        logger.info(f"{request.table_name} table was updated {str(result.rowcount)} rows")
        return {
            "Number_of_row":result.rowcount
        }
    else:
        return result

def drop_tables(tables:List[TableInfor]):
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    for table in tables:
        result = sqlAlchemyUtil.execute_query(f"DROP TABLE {table.catalog}.{table.schema}.{table.table}")
        if isinstance(result,CursorResult):
            logger.info(f"{table.catalog}.{table.schema}.{table.table} was dropped scuccessfully")
    