import logging
from sqlalchemy import CursorResult

from constants import TRINO_CONNECTION_STRING, TEMP_CATALOG, TEMP_SCHEMA, DEFAULT_CATALOG, DEFAULT_SCHEMA
from DATAFLOW.SqlAlchemyUtil import SqlAlchemyUtil
from DATAFLOW.model import *

logger = logging.getLogger("helper")
logging.basicConfig()
logger.setLevel(logging.INFO)


def create_table_as_select(table_name, param: Param, username, flow_name, step_name, formatted_time):
    # Get selected columns from param.list_1 field
    selected_columns = ',\n'.join([col.get('column') for col in param.list_1])
    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {iceberg_table_name}
    WITH(
        format = 'PARQUET',
        location = 's3a://temp/{flow_name}/{iceberg_table_name}'
    ) 
    AS SELECT {selected_columns} FROM {table_name}
    """
    logger.info(f"Select query: {create_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(create_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_rename_column(table_name, param: Param, username, flow_name, step_name, formatted_time):
    # Get columns need rename from param.list_1
    columns_mapping = param.list_1
    # Get selected columns from param.list_2 field
    selected_columns = param.list_2

    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    create_query = f"""
        CREATE TABLE IF NOT EXISTS {iceberg_table_name}
        WITH(
            format = 'PARQUET',
            location = 's3a://temp/{flow_name}/{iceberg_table_name}'
        ) 
        AS SELECT {', '.join([f"{column['column']} AS {column['column_new']}" for column in columns_mapping])},
        {', '.join([f"{column['column']}" for column in selected_columns])}
        FROM {table_name}
        """
    logger.info(f"Select query: {create_query}")
    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(create_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        drop_tables(iceberg_table_name)
        raise e


def create_table_as_add_columns(table_name, param: Param, username, flow_name, step_name, formatted_time):
    # Get info new columns from param.list_1 field
    columns_and_types = param.list_1

    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    create_query = f"""
        CREATE TABLE IF NOT EXISTS {iceberg_table_name}
        WITH(
            format = 'PARQUET',
            location = 's3a://temp/{flow_name}/{iceberg_table_name}'
        ) 
        AS SELECT * FROM {table_name}
        """
    logger.info(f"Select query: {create_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(create_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")

            # Creating the final ALTER TABLE ADD COLUMNS query
            add_columns_query = [
                f"ALTER TABLE {iceberg_table_name} " \
                f"ADD COLUMN IF NOT EXISTS {column['column']} " \
                f"{'VARCHAR' if column['type'] == 'string' else column['type']}" for column in columns_and_types]

            sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
            sql_alchemy_util.execute_multiple_queries(add_columns_query)

            # Tạo chuỗi SET cho câu truy vấn UPDATE
            set_clauses = []
            for column in columns_and_types:
                column_name = column['column']
                column_value = column['value']

                # Kiểm tra kiểu dữ liệu để xử lý chuỗi đúng cách
                if column['type'] == 'string':
                    set_clauses.append(f"{column_name} = '{column_value}'")
                elif column['type'] == 'timestamp':
                    if column_value == 'CURRENT_TIMESTAMP':
                        set_clauses.append(f"{column_name} = CURRENT_TIMESTAMP")
                    else:
                        set_clauses.append(f"{column_name} = TIMESTAMP '{column_value}'")
                else:
                    set_clauses.append(f"{column_name} = {column_value}")

            # Sử dụng join để kết hợp các mệnh đề SET
            set_clause = ', '.join(set_clauses)

            add_value_query = f"""
               UPDATE {iceberg_table_name}
               SET {set_clause}
            """
            sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
            sql_alchemy_util.execute_query(add_value_query)
            return ResultModel(1, "Success"), iceberg_table_name

        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_case(table_name, param: Param, username, flow_name, step_name, formatted_time):
    # Get columns need using case when from param.list_1
    columns_case = param.list_1
    # get selected columns from param.list_2
    columns_select = param.list_2

    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"

    # generate case query
    for col_case in columns_case:
        col = col_case['column']
        type_col = col_case['type']

        # get condition from child_list_1, child_list_2
        cases = col_case.get("child_list_1", [])
        if type_col == 'string' or type_col == 'timestamp':
            case_part = ' '.join([
                f"WHEN {col} {case['where']} '{case['child_value_1']}' THEN '{case['child_value_2']}'" if (
                        case['where'] != '' and case[
                    'child_value_1'] != '') else f"ELSE {case['child_value_2']}" for case in
                cases]) + f" END AS {col},"
        else:
            case_part = ' '.join([
                f"WHEN {col} {case['where']} {case['child_value_1']} THEN {case['child_value_2']}" if (
                        case['where'] != '' and case[
                    'child_value_1'] != '') else f"ELSE {case['child_value_2']}" for case in
                cases]) + f" END AS {col},"

    select_part = f"CASE {case_part}"
    select_part = select_part.rstrip(', ')

    create_query = f"""
    CREATE TABLE IF NOT EXISTS {iceberg_table_name}
    WITH(
        format = 'PARQUET',
        location = 's3a://temp/{flow_name}/{iceberg_table_name}'
    ) 
    AS SELECT {', '.join([f"{column['column']}" for column in columns_select])}, {select_part} 
    FROM {table_name}
    """
    logger.info(f"Select query: {create_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(create_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_replace_value(table_name, param: Param, username, flow_name, step_name, formatted_time):
    # Get columns need replace value
    columns_replace = param.list_1

    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    create_query = f"""
            CREATE TABLE IF NOT EXISTS {iceberg_table_name}
            WITH(
                format = 'PARQUET',
                location = 's3a://temp/{flow_name}/{iceberg_table_name}'
            ) 
            AS SELECT *
            FROM {table_name}
            
            """
    logger.info(f"Select query: {create_query}")
    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(create_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")

            # generate query to replace value
            for columns_to_replace in columns_replace:
                column_name_replace = columns_to_replace['column']
                type_column_replace = columns_to_replace['type']
                new_value = columns_to_replace['value']
                wheres = columns_to_replace.get("child_list_1", [])

                # Xử lý phần replace
                if type_column_replace == 'string':
                    replace_part = f"{column_name_replace} = '{new_value}'"
                elif type_column_replace == 'timestamp':
                    replace_part = f"{column_name_replace} = CAST('{new_value}' AS TIMESTAMP)"
                else:
                    replace_part = f"{column_name_replace} = {new_value}"

                where_part = ""
                # Xử lý phần where
                for where in wheres:
                    if where['type'] == 'string':
                        where_part = where_part + f"{where['column']} = '{where['child_value']}' {where['aggregation']} "
                    elif where['type'] == 'timestamp':
                        where_part = where_part + f"{where['column']} = CAST('{where['child_value']}' AS TIMESTAMP) {where['aggregation']} "
                    else:
                        where_part = where_part + f"{where['column']} = {where['child_value']} {where['aggregation']} "

            where_part = where_part.rstrip(' OR')
            where_part = where_part.rstrip(' AND')

            replace_value_query = f"""
                UPDATE {iceberg_table_name}
                SET {replace_part}
                WHERE {where_part}
                """

            sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
            # execute query replace value
            sql_alchemy_util.execute_query(replace_value_query)
            logger.info(f"Table {iceberg_table_name} was replaced value for {columns_replace} columns successfully")

            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_change_type(table_name, param: Param, username, flow_name, step_name, formatted_time):
    # get info columns need change type
    columns_and_types = param.list_1

    value = ""
    for column_type in columns_and_types:
        column_name = column_type['column']
        type_columns = column_type['type']
        cast_type = 'VARCHAR' if type_columns == 'string' else ('DOUBLE PRECISION' if type_columns == 'float' else (
            'timestamp(6)' if type_columns == 'timestamp' else 'INTEGER'))
        # Chọn loại chuyển đổi tùy thuộc vào kiểu cột
        value = value + f"CAST({column_name} AS {cast_type}) AS {column_name}, "

    value = value.rstrip(', ')

    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {iceberg_table_name}
    WITH(
        format = 'PARQUET',
        location = 's3a://temp/{flow_name}/{iceberg_table_name}'
    ) 
    AS SELECT {value} FROM {table_name}
    """
    logger.info(f"Select query: {create_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(create_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_join(table_left, table_right, param: Param, username,
                         flow_name, step_name, formatted_time):
    # Join option: ["inner", "left", "right", "full", "outer", "cross"]
    option = param.option
    # Get columns selected
    list1_columns = param.list_1
    # join column of table_left
    left_columns = param.list_2
    # join column of table_right
    right_columns = param.list_3

    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {iceberg_table_name}
    WITH(
        format = 'PARQUET',
        location = 's3a://temp/{flow_name}/{iceberg_table_name}'
    ) 
    AS 
    SELECT {', '.join([f"table_left.{col['column']} AS {col['column']}" for col in left_columns])}, 
           {', '.join([f"table_right.{col['column']} AS {col['column']}" for col in right_columns])}
    FROM {table_left} AS table_left
    {option} JOIN {table_right} AS table_right
    ON {' AND '.join([f"table_left.{key['left_key']} = table_right.{key['right_key']}" for key in list1_columns])}
    """
    logger.info(f"Select query: {create_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(create_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_sample_data(table_name, param: Param, username, flow_name, step_name, formatted_time):
    # get info column sample data
    columns_and_types = param.columns_and_types

    selected_clause = ', '.join(
        [f"CAST({col['column']} AS {col['type'] if col['type'] != 'string' else 'varchar'}) AS {col['column']}" for
         col in columns_and_types])
    values_queries_list = []
    for values in param.values:
        values_queries_list.append(f"""({', '.join([f"'{v}'" for v in values['value']])})""")

    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {iceberg_table_name}
    WITH(
        format = 'PARQUET',
        location = 's3a://temp/{flow_name}/{iceberg_table_name}'
    )
    AS SELECT {selected_clause} 
    FROM (VALUES {', '.join(values_queries_list)}) AS temp_table({', '.join([col['column'] for col in columns_and_types])})
    """
    logger.info(f"Select query: {create_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(create_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_fill_null(table_name, param: Param, username, flow_name, step_name, formatted_time):
    # get column need replace value null
    column_fill_null = param.list_1

    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {iceberg_table_name}
    WITH(
        format = 'PARQUET',
        location = 's3a://temp/{flow_name}/{iceberg_table_name}'
    ) 
    AS SELECT * FROM {table_name}
    """
    logger.info(f"Select query: {create_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(create_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")

            # generate queries replace fill null
            fill_null_queries = []
            number_ope_list = ['sum', 'avg', 'min', 'max']
            string_ope_list = ['min', 'max']

            for info in column_fill_null:
                query = ''
                if (info.get('ope') in number_ope_list and info.get('type') == 'int') \
                        or (info.get('ope') in string_ope_list and info.get('type') in ['string', 'date', 'timestamp']):
                    query = f"""
                                UPDATE {iceberg_table_name} 
                                SET {info.get('column')} = (SELECT CAST({info.get('ope')}({info.get('column')}) 
                                AS {info.get('type') if info.get('type') != 'string' else 'varchar'}) 
                                FROM {iceberg_table_name} WHERE {info.get('column')} IS NOT NULL) 
                                WHERE {info.get('column')} IS NULL"""
                else:
                    query = f"""
                                UPDATE {iceberg_table_name} 
                                SET {info.get('column')} = (CAST('{info.get('value')}' 
                                AS {info.get('type') if info.get('type') != 'string' else 'varchar'} ))
                                WHERE {info.get('column')} IS NULL"""
                if query != '':
                    fill_null_queries.append(query)

            # execute run query update value for fill null
            sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
            sql_alchemy_util.execute_multiple_queries(fill_null_queries)
            logger.info("Update value for fill null successfully")

            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def process_data_model_destination(input_table_name, param: Param):
    output_table_name = param.table_name
    option = param.option
    merge_keys = ' AND '.join(
        [f"source.{key.source_key}=destination.{key.destination_key}" for key in param.key_columns])
    merge_update_columns = ', '.join(
        [f"{key.column_destination}=source.{key.column_source}" for key in param.mapping_columns])
    merge_insert_columns = ', '.join([f"{key.column_destination}" for key in param.mapping_columns])
    merge_insert_values = ', '.join([f"source.{key.column_source}" for key in param.mapping_columns])

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)

    if option == "upsert" or option == "":
        query = f"""
        MERGE INTO {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{output_table_name} AS destination 
        USING {input_table_name} as source
        ON {merge_keys}
        WHEN MATCHED THEN UPDATE SET
        {merge_update_columns}
        WHEN NOT MATCHED THEN INSERT
        ({merge_insert_columns})
        VALUES
        ({merge_insert_values})
        """

        logger.info(f"Merge query: {query}")
        result = sql_alchemy_util.execute_query(query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            return ResultModel(1, f"Number of rows was effected: {number_of_row}")
        else:
            return result

    if option == "insert":
        query = f"""
        INSERT INTO {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{output_table_name} ({merge_insert_columns})
        SELECT {merge_insert_values} FROM {input_table_name} source
        """

        logger.info(f"Insert query: {query}")
        result = sql_alchemy_util.execute_query(query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            return ResultModel(1, f"Number of rows was inserted: {number_of_row}")
        else:
            return result

    if option == "update":
        query = f"""
        MERGE INTO {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{output_table_name} AS destination 
        USING {input_table_name} as source
        ON {merge_keys}
        WHEN MATCHED THEN UPDATE SET
        {merge_update_columns}
        """

        logger.info(f"Update query : {query}")
        result = sql_alchemy_util.execute_query(query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            return ResultModel(1, f"Number of rows was updated: {number_of_row}")
        else:
            return result


def drop_tables(node_dict: dict, pop_list):
    drop_tables = [table for table in node_dict.values() if table not in pop_list]

    results = []
    for table in drop_tables:
        sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
        result = sql_alchemy_util.execute_query(f"DROP TABLE {table}")
        if isinstance(result, CursorResult) == False:
            logger.error(f"Dropping table {table} failed due to {result.message}")
            results.append(result)
        else:
            logger.info(f"table {table} was dropped successfully")
            results.append(ResultModel(1, f"table {table} was dropped successfully"))

    return results


def create_table_as_drop_duplicates(table_name, param, username, flow_name, step_name, formatted_time):
    # list_1 contains the selected columns
    selected_columns = ','.join([col.get('column') for col in param.list_1])
    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    # if not have selected columns, select distinct * from table
    if not param.list_1:
        drop_duplicates_query = f"""
           CREATE TABLE IF NOT EXISTS {iceberg_table_name}
           WITH(
               format = 'PARQUET',
               location = 's3a://temp/{flow_name}/{iceberg_table_name}'
           ) 
           AS SELECT DISTINCT * FROM {table_name} 
           """
    # if having selected columns, select distinct base on these selected columns
    else:
        drop_duplicates_query = f"""
           CREATE TABLE IF NOT EXISTS {iceberg_table_name}
           WITH(
               format = 'PARQUET',
               location = 's3a://temp/{flow_name}/{iceberg_table_name}'
           ) 
           AS SELECT DISTINCT {selected_columns} FROM {table_name} 
           """
    logger.info(f"Select query: {drop_duplicates_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(drop_duplicates_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_drop_null_records(table_name, param, username, flow_name, step_name, formatted_time):
    # list_2 contains selected columns
    selected_columns = ','.join([col.get('column') for col in param.list_2])
    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    # list_1 contains the columns is not null
    where_part = 'AND '.join([f"{column['column']} IS NOT NULL " for column in param.list_1])
    # create table with columns in list_2 and value of the columns in list_1 is not null
    drop_null_records_query = f"""
          CREATE TABLE IF NOT EXISTS {iceberg_table_name}
          WITH(
              format = 'PARQUET',
              location = 's3a://temp/{flow_name}/{iceberg_table_name}'
          ) 
          AS SELECT {selected_columns} FROM {table_name} 
          WHERE ({where_part})
          """
    logger.info(f"Select query: {drop_null_records_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(drop_null_records_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_group_by(table_name, param, username, flow_name, step_name, formatted_time):
    # list_2 are the selected columns to group by
    group_by_part = ','.join([col.get('column') for col in param.list_2])
    # list_1 are the selected columns to compute aggregations [like count, avg, max, min...]
    aggregations = param.list_1
    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    select_part = ', '.join(
        [f"{aggregation['ope']}({aggregation['column']}) AS {aggregation['column']}_{aggregation['ope']}"
         for aggregation in aggregations]
    )
    # create table with columns in list_2 and [{aggregation['column']}_{aggregation['ope']] in list_1
    group_by_query = f"""
              CREATE TABLE IF NOT EXISTS {iceberg_table_name}
              WITH(
                  format = 'PARQUET',
                  location = 's3a://temp/{flow_name}/{iceberg_table_name}'
              ) 
              AS SELECT {select_part}, {group_by_part} FROM {table_name} 
              GROUP BY {group_by_part}
              """
    logger.info(f"Select query: {group_by_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(group_by_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_filter(table_name, param, username, flow_name, step_name, formatted_time):
    # list_2 contains selected columns
    selected_columns = ','.join([col.get('column') for col in param.list_2])
    # list_1: filter and condition
    conditions = param.list_1
    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"

    where_part = ''
    for condition in conditions:
        values = condition.get("child_list_1", [])
        # create manual SQL
        if condition['type'] == 'string' or condition['type'] == 'timestamp':
            values_str = ', '.join([f"'{value['child_value']}'" for value in values])
        else:
            values_str = ', '.join([f"{value['child_value']}" for value in values])

        where_part = (where_part + f" {condition['column']} {condition['ope']} ({values_str})"
                      + f" {condition['aggregation']}") if condition['aggregation'] != '' else " "
    # remove aggregation from the string (position: end)
    where_part = where_part.rstrip(conditions[-1]['aggregation'])

    # create table with selected columns in list_2 to meet condition in list_1
    filter_query = f"""
                  CREATE TABLE IF NOT EXISTS {iceberg_table_name}
                  WITH(
                      format = 'PARQUET',
                      location = 's3a://temp/{flow_name}/{iceberg_table_name}'
                  ) 
                  AS SELECT {selected_columns} FROM {table_name} 
                  WHERE {where_part}
                  """
    logger.info(f"Select query: {filter_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(filter_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


# combine the records on table_left and table_right that not have duplicate rows
def create_table_as_union(table_left, table_right, param: Param, username, flow_name, step_name, formatted_time):
    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"
    # list_1: selected columns in table_left [data_model_name]
    # list_2: selected columns in table_right [data_model_name_2]
    union_query = f"""
    CREATE TABLE IF NOT EXISTS {iceberg_table_name}
    WITH(
        format = 'PARQUET',
        location = 's3a://temp/{flow_name}/{iceberg_table_name}'
    ) 
    AS 
    SELECT {', '.join([f"A.{col['column']}" for col in param.list_1])}
    FROM {table_left} AS A
    
    {param.option}
    
    SELECT {', '.join([f"B.{col['column']}" for col in param.list_2])}
    FROM {table_right} AS B
    """
    logger.info(f"Select query: {union_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(union_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e


def create_table_as_change_schema(table_name, param, username, flow_name, step_name, formatted_time):
    # list_1: selected columns will be change name and change its type
    columns_mapping = param.list_1

    value = ""
    for column in columns_mapping:
        old_column_name = column['column']
        new_column_name = column['column_new']
        type_columns = column['type']

        # choose convert type base on column type
        cast_type = 'VARCHAR' if type_columns == 'string' else ('DOUBLE PRECISION' if type_columns == 'float' else (
            'timestamp(6)' if type_columns == 'timestamp' else 'INTEGER'))
        value = value + f"CAST({old_column_name} AS {cast_type}) AS {new_column_name}, "

    value = value.rstrip(', ')

    iceberg_table_name = f"{TEMP_CATALOG}.{TEMP_SCHEMA}.{username}_{step_name}_iceberg{formatted_time}"

    change_schema_query = f"""
              CREATE TABLE IF NOT EXISTS {iceberg_table_name}
              WITH(
                  format = 'PARQUET',
                  location = 's3a://temp/{flow_name}/{iceberg_table_name}'
              ) 
              AS SELECT {value} FROM {table_name} 
              """
    logger.info(f"Select query: {change_schema_query}")

    sql_alchemy_util = SqlAlchemyUtil(TRINO_CONNECTION_STRING)
    try:
        result = sql_alchemy_util.execute_query(change_schema_query)
        if isinstance(result, CursorResult):
            number_of_row = result.rowcount if result.rowcount > 0 else 0
            logger.info(f"Table {iceberg_table_name} was created successfully with {str(number_of_row)} rows")
            return ResultModel(1, "Success"), iceberg_table_name
        else:
            result, None
    except Exception as e:
        raise e

