from .model import Group,ResultModel,Segment
import logging
from .SqlAlchemyUtil import SqlAlchemyUtil,CursorResult
from minio import Minio
from constants import *
import io
import unicodedata

logger = logging.getLogger("helper")
logging.basicConfig()
logger.setLevel(logging.INFO)

MINIO_URL='localhost:9000'
ACCESS_KEY='minio_access_key'
SECRET_KEY='minio_secret_key'


def remove_accents_and_replace(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    result_str = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    result_str = result_str.replace('ă', 'a').replace('â', 'a').replace('đ', 'd').replace('ê', 'e').replace('ô', 'o').replace('ơ', 'o').replace('ư', 'u').replace(' ', '_')
    
    return result_str

def calculator_group(group:Group):
    group_name = group.group_name
    table_name = group.table_name
    where_conditions = group.where
    having_conditions = group.having
    option_with_having = group.option_with_having

    query=f"""
    SELECT 
        COUNT(DISTINCT customer_unified_key) as customer_unified_key, 
        COUNT(DISTINCT phone) as phone, 
        COUNT(DISTINCT email) as email 
    FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{table_name}
"""
    if where_conditions:
        query += ' WHERE'

        # Thêm điều kiện từ phần WHERE của JSON
        for condition in where_conditions:
            data_attribute = condition.data_attribute
            type_attribute = condition.type_attribute
            operator = condition.operator
            values = condition.value
            option = condition.option
    
            value_str = ', '.join([str(value) for value in values])
            
            if type_attribute == 'string':
                query += f" {data_attribute} {operator} '{value_str}' {option}"
            else:
                query += f' {data_attribute} {operator} {value_str} {option}'
        
        
        if query.endswith("and") or query.endswith("or"):
            query = query[:query.rfind(" ")]

    if having_conditions:  
        if not where_conditions:
            query += ' WHERE'
        
        # Thêm điều kiện từ phần HAVING của JSON
        query += f" {option_with_having} customer_unified_key IN (SELECT customer_unified_key FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{table_name} GROUP BY customer_unified_key HAVING"
    
        for condition in having_conditions:
            aggregate = condition.aggregate
            data_attribute = condition.data_attribute
            type_attribute = condition.type_attribute
            operator = condition.operator
            values = condition.value
            option = condition.option
    
            value_str = ', '.join([str(value) for value in values])
            
            if type_attribute == 'string':
                query += f" {aggregate}({data_attribute}) {operator} '{value_str}' {option}"
            else:
                query += f' {aggregate}({data_attribute}) {operator} {value_str} {option}'
    
    
    
        # Kiểm tra nếu câu truy vấn kết thúc bằng "and" hoặc "or" thì loại bỏ nó
        if query.endswith("and") or query.endswith("or"):
            query = query[:query.rfind(" ")]  # Loại bỏ từ "and" hoặc "or" cuối cùng
        query += ')'
    
    logger.info(f"Create group query: {query}")

    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    result=sqlAlchemyUtil.execute_query(query)
    if isinstance(result,CursorResult):
        logger.info(f"Number of rows: {result.rowcount if result.rowcount >0 else 0}")
        return ResultModel(1,""),result.mappings().all()
    else: 
        return ResultModel(result),None
    

def save_group(group:Group):
    username = group.username
    segment_name = group.segment_name
    group_name = group.group_name
    type_sm = group.type
    table_name = group.table_name
    where_conditions = group.where
    having_conditions = group.having
    option_with_having = group.option_with_having
    edit_group = group.edit_group
    bucket_name = 'cdp-segment-builder'

    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)

    if edit_group != "":
        query = f'''DROP TABLE IF EXISTS {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{group_name}'''
        logger.info(f"Create Group Query: {query}")
        sqlAlchemyUtil.execute_query(query)
    
    query = f"""
    CREATE TABLE IF NOT EXISTS {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{group_name}
        WITH(
        format = 'PARQUET',
        location = 's3a://{bucket_name}/{username}/{segment_name}/groups/{group_name}/'
    ) AS
    """

    if type_sm == 'phone':
        # Tạo phần SELECT
        query += f'SELECT MAX(customer_unified_key) as customer_unified_key, phone, MAX(email) as email FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{table_name}'
        tail_query = ' GROUP BY phone'
    elif type_sm == 'email':
        # Tạo phần SELECT
        query += f'SELECT MAX(customer_unified_key) as customer_unified_key, MAX(phone) as phone, email FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{table_name}'
        tail_query = ' GROUP BY email'
    else:
        # Tạo phần SELECT
        query += f'SELECT customer_unified_key, MAX(phone) as phone, MAX(email) as email FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{table_name}'
        tail_query = ' GROUP BY customer_unified_key'
    
    if where_conditions:
        query += ' WHERE'

        # Thêm điều kiện từ phần WHERE của JSON
        for condition in where_conditions:
            data_attribute = condition.data_attribute
            type_attribute = condition.type_attribute
            operator = condition.operator
            values = condition.value
            option = condition.option
    
            value_str = ', '.join([str(value) for value in values])
            
            if type_attribute == 'string':
                query += f" {data_attribute} {operator} '{value_str}' {option}"
            else:
                query += f' {data_attribute} {operator} {value_str} {option}'
        
        
        # Kiểm tra nếu câu truy vấn kết thúc bằng "and" hoặc "or" thì loại bỏ nó
        if query.endswith("and") or query.endswith("or"):
            query = query[:query.rfind(" ")]  # Loại bỏ từ "and" hoặc "or" cuối cùng

    if having_conditions:   
        if not where_conditions:
            query += ' WHERE'
            
        # Thêm điều kiện từ phần HAVING của JSON
        query += f" {option_with_having} customer_unified_key IN (SELECT customer_unified_key FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{table_name} GROUP BY customer_unified_key HAVING"
    
        for condition in having_conditions:
            aggregate = condition.aggregate
            data_attribute = condition.data_attribute
            type_attribute = condition.type_attribute
            operator = condition.operator
            values = condition.value
            option = condition.option
    
            value_str = ', '.join([str(value) for value in values])
            
            if type_attribute == 'string':
                query += f" {aggregate}({data_attribute}) {operator} '{value_str}' {option}"
            else:
                query += f' {aggregate}({data_attribute}) {operator} {value_str} {option}'
    
    
    
        # Kiểm tra nếu câu truy vấn kết thúc bằng "and" hoặc "or" thì loại bỏ nó
        if query.endswith("and") or query.endswith("or"):
            query = query[:query.rfind(" ")]  # Loại bỏ từ "and" hoặc "or" cuối cùng
        query += ')'
        
    query += tail_query

    logger.info(f"Create Group Query {query}")
    result=sqlAlchemyUtil.execute_query(query)
    if isinstance(result,CursorResult):
        logger.info(f"Number of rows was processed: {result.rowcount}")

    object_key = f'{username}/{segment_name}/query_string/{segment_name}/query.sql'
    minio_client=Minio(endpoint=MINIO_URL,access_key=ACCESS_KEY,secret_key=SECRET_KEY,secure=False)
    query_as_bytes=query.encode("utf-8")
    query_as_a_stream=io.BytesIO(query_as_bytes)
    try:
        put_result=minio_client.put_object(
            bucket_name=bucket_name,
            object_name=object_key,
            data=query_as_a_stream,
            length=len(query_as_bytes),

        )

        logger.info(f"Created {put_result.object_name} object; etag: {put_result.etag}, version-id: {put_result.version_id}")
    except Exception as e:
        logger.error(f"Putting '{object_key}' failed due to: {str(e)}")
    

    query_string = f"SELECT * FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{group_name}"

    return query_string,result if isinstance(result,ResultModel) else ResultModel(1,"")


def calculator_segment(segment:Segment):
    segment_type =segment.type
    first_segment_name = segment.segment_or_group[0].name
    join_type = segment.segment_or_group[0].option

    query = f'''
    SELECT
        COUNT(DISTINCT {first_segment_name}.customer_unified_key) as customer_unified_key, 
        COUNT(DISTINCT {first_segment_name}.phone) as phone, 
        COUNT(DISTINCT {first_segment_name}.email) as email
    FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{first_segment_name} as {first_segment_name}
    '''
    
    
    for condition in segment.segment_or_group[1:]:  # Start from the second element
            
        if join_type == 'included' or join_type == 'or':
            join_type = 'OUTER'
        elif join_type == 'excluded':
            join_type = 'LEFT'
        elif join_type == 'intersected' or join_type == 'and':
            join_type = 'INNER'
            
        segment = condition.name
        query += f'''{join_type} JOIN {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{segment} AS {segment}
        ON {first_segment_name}.{segment_type} = {segment}.{segment_type}
        '''
        
        join_type = condition.option
    

    logger.info(f"Create Segment Query: {query}")

    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)

    response_create = sqlAlchemyUtil.execute_query(query)

    if isinstance(response_create,CursorResult):
        return ResultModel(1,""),response_create.mappings().all()
    else:
        return response_create,None
    

def save_segment(segment:Segment):
    username = segment.username
    segment_name = segment.segment_name
    first_segment_name = segment.segment_or_group[0].name
    join_type = segment.segment_or_group[0].option
    edit_segment = segment.edit_segment
    bucket_name = 'cdp-segment-builder'
    
    sqlAlchemyUtil = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    if edit_segment != "":
        query = f'''DROP TABLE IF EXISTS {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{segment_name}'''
        logger.info(f"Drop Table Query: {query}")
        response_create = sqlAlchemyUtil.execute_query(query)
    
    query =  f'''CREATE TABLE IF NOT EXISTS {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{segment_name}
                WITH (
                    format = 'PARQUET',
                    location='s3a://{bucket_name}/{username}/{segment_name}/segment/{segment_name}/'
                ) AS SELECT 
                    {first_segment_name}.customer_unified_key as customer_unified_key, 
                    {first_segment_name}.phone as phone, 
                    {first_segment_name}.email as email
                FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{first_segment_name} as {first_segment_name}
                '''
    
    for condition in segment.segment_or_group[1:]:  # Start from the second element
            
        if join_type == 'included' or join_type == 'or':
            join_type = 'FULL'
        elif join_type == 'excluded':
            join_type = 'LEFT'
        elif join_type == 'intersected' or join_type == 'and':
            join_type = 'INNER'
            
        segment = condition.name
        query += f'''{join_type} JOIN {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{segment} as {segment}
        ON {first_segment_name}.customer_unified_key = {segment}.customer_unified_key
        '''
        
        join_type = condition.option

    logger.info(f"Create Segment Query: {query}")
    response_create=sqlAlchemyUtil.execute_query(query)

    
    object_key = f'{username}/{segment_name}/query_string/{segment_name}/query.sql'
    minio_client=Minio(endpoint=MINIO_URL,access_key=ACCESS_KEY,secret_key=SECRET_KEY,secure=False)
    query_as_bytes=query.encode("utf-8")
    query_as_a_stream=io.BytesIO(query_as_bytes)
    try:
        put_result=minio_client.put_object(
            bucket_name=bucket_name,
            object_name=object_key,
            data=query_as_a_stream,
            length=len(query_as_bytes)
        )
        logger.info(f"Created {put_result.object_name} object; etag: {put_result.etag}, version-id: {put_result.version_id}")
    except Exception as e:
        logger.error(f"Putting '{object_key}' failed due to: {str(e)}")
    
    query_string = f"SELECT * FROM {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{segment_name}"

    return query_string,response_create if isinstance(response_create,ResultModel) else ResultModel(1,"")


