from pydantic import BaseModel
from typing import List,Literal,Optional,Union
from decimal import Decimal
from datetime import date,time,datetime
from constants import DEFAULT_CATALOG as CATALOG
from constants import DEFAULT_SCHEMA as SCHEMA


TRINO_DATA_TYPE_MAPPING = {
    "int": "INTEGER",
    "float": "DOUBLE",
    "decimal": "DECIMAL",
    "str": "VARCHAR",
    "date": "DATE",
    "time": "TIME",
    "datetime": "TIMESTAMP",
    "bool": "BOOLEAN"
}

class Column(BaseModel):
    name_column: str
    type: Literal["int","bool","float","decimal",
                  "str","bytes","date","time","datetime",
                  "list","dict","tuple"
                  ]
    value: Optional[Union[int,bool,float,Decimal,str,bytes,
                          date,time,datetime,list,dict,tuple]] = None

class InsertColumns(BaseModel):
    column_name: str
    column_value: Optional[Union[int,bool,float,Decimal,str,bytes,
                          date,time,datetime,list,dict,tuple]] = None
    column_type: Literal["int","bool","float","decimal",
                  "str","bytes","date","time","datetime",
                  "list","dict","tuple"
                  ]


class UpdateColumns(BaseModel):
    update_column: str
    update_value: Optional[Union[int,bool,float,Decimal,str,bytes,
                          date,time,datetime,list,dict,tuple]] = None
    update_type: Literal["int","bool","float","decimal",
                  "str","bytes","date","time","datetime",
                  "list","dict","tuple"
                  ] 

class WhereUpdateColumns(BaseModel):
    column: str
    value: Optional[Union[int,bool,float,Decimal,str,bytes,
                          date,time,datetime,list,dict,tuple]] = None
    op: str
    type: Optional[str]
    column_type: Literal["int","bool","float","decimal",
                  "str","bytes","date","time","datetime",
                  "list","dict","tuple"
                  ] 

class WhereUpdateMulti(BaseModel):
    column_name: str
    column_value: Optional[Union[int,bool,float,Decimal,str,bytes,
                          date,time,datetime,list,dict,tuple]] = None
    op: Optional[str]
    column_type: Literal["int","bool","float","decimal",
                  "str","bytes","date","time","datetime",
                  "list","dict","tuple"
                  ]

class SetNan(BaseModel):
    column_name: str
    column_value: Optional[Union[int,bool,float,Decimal,str,bytes,
                          date,time,datetime,list,dict,tuple]] = None
    column_type: Literal["int","bool","float","decimal",
                  "str","bytes","date","time","datetime",
                  "list","dict","tuple"
                  ]
# <---------------------------------------------------------------->

class IcebergTable(BaseModel):
    table_name: str
    username: str
    option: Literal["create_table","add_columns"]
    values: List[Column]

class RenameColumn(BaseModel):
    table_name: str
    username: str
    option: Literal["rename_column"]
    old_column: str
    old_type: Literal["int","bool","float","decimal",
                  "str","bytes","date","time","datetime",
                  "list","dict","tuple"
                  ]
    new_column: str

class DropTable(BaseModel):
    table_name: str
    username: str
    option: Literal["drop_table"]

class RemoveColumns(BaseModel):
    table_name: str
    username: str
    option: Literal["remove_columns"]
    drop_column_name: str

class DropAllRow(BaseModel):
    table_name: str
    option: Literal["drop_all_row"]
    username: str

class Insert(BaseModel):
    table_name:str
    option: Literal["insert"]
    username: str
    values: List[InsertColumns]

class ReplaceAndEdit(BaseModel):
    table_name:str
    option: Literal["replace_and_edit_row"]
    username: str
    set: List[UpdateColumns]
    where: List[WhereUpdateColumns]


class SnapshotRetention(BaseModel):
    table_name:str
    username: str
    option: Literal["snapshot_retention"]
    seconds: int

class UpdateValuesMultiCondition(BaseModel):
    table_name:str
    option: Literal["filter"]
    username: str
    set: List[UpdateColumns]
    where: List[WhereUpdateMulti]

class UpdateNanValue(BaseModel):
    table_name:str
    option: Literal["update_nan_value"]
    username: str
    set_nan: List[SetNan]

# <---------------------------------------------------------------->

def generate_sql_create_table(schema: IcebergTable)-> str:
    column_list = [f"{column.name_column} {TRINO_DATA_TYPE_MAPPING[column.type]}" for column in schema.values] 
    columns_str = ',\n'.join(column_list)

    sql_str=f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.{schema.table_name} (
        {columns_str}
    ) 
    WITH(
            format = 'PARQUET'
    )
    """
    return sql_str


def generate_sql_add_column(schema: IcebergTable)-> str:
    sql_add_columns=[]
    for column in schema.values:
        sql_add_columns.append(f"ALTER TABLE {CATALOG}.{SCHEMA}.{schema.table_name} ADD COLUMN {column.name_column} {TRINO_DATA_TYPE_MAPPING[column.type]}")
    return sql_add_columns


def generate_sql_rename_column(rename_column:RenameColumn):
    return f"ALTER TABLE {CATALOG}.{SCHEMA}.{rename_column.table_name} RENAME COLUMN {rename_column.old_column} TO {rename_column.new_column}"
        

def generate_sql_drop_table(drop_table: DropTable):
    return f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.{drop_table.table_name}"


def generate_sql_remove_columns(remove_columns: RemoveColumns):
    return f"ALTER TABLE {CATALOG}.{SCHEMA}.{remove_columns.table_name} DROP COLUMN {remove_columns.drop_column_name}"


def generate_sql_drop_all_row(drop_all_row: DropAllRow):
    return f"DELETE FROM {CATALOG}.{SCHEMA}.{drop_all_row.table_name}"

def insert_row_query_builder(insert: Insert) -> str:
    column_names = [f"{column.column_name}" for column in insert.values]
    column_values = [f"{column.column_value}" for column in insert.values]
    column_types = [f"{TRINO_DATA_TYPE_MAPPING[column.column_type]}" for column in insert.values]

    formatted_column_values = []
    for value, column_type in zip(column_values, column_types):
        if column_type != "VARCHAR":
            formatted_column_values.append(str(value))
        else:
            formatted_column_values.append(f"'{value}'")

    column_names_str = ", ".join(column_names)
    column_values_str = ", ".join(formatted_column_values)

    if column_types == "VARCHAR":
        insert_row_query = f"""
        INSERT INTO {CATALOG}.{SCHEMA}.{insert.table_name} ({column_names_str}) VALUES ('{column_values_str}')
        """
    else:
        insert_row_query = f"""
        INSERT INTO {CATALOG}.{SCHEMA}.{insert.table_name} ({column_names_str}) VALUES ({column_values_str})
        """

    return insert_row_query

def replace_and_edit_row_query_builder(replace:ReplaceAndEdit) -> str:
    # SET
    set_conditions_str = ''
    count = 0
    for set_condition in replace.set:
        if count > 0:
            set_conditions_str = set_conditions_str + ', '
            
        update_column = set_condition.update_column
        update_value = set_condition.update_value
        update_type = f"{TRINO_DATA_TYPE_MAPPING[set_condition.update_type]}"
        
        if update_type != "VARCHAR":
            set_conditions_str += f" {update_column} = {update_value}"
            count = count + 1
        else:
            set_conditions_str += f" {update_column} = '{update_value}'"
            count = count + 1
    
    # WHERE
    where_conditions = ''
    for condition in replace.where:

        column = condition.column
        op = condition.op
        value = condition.value
        type = condition.type
        column_type = f"{TRINO_DATA_TYPE_MAPPING[condition.column_type]}"
        
        if column_type != "VARCHAR":
            where_conditions += f" {column} {op} {value} {type}"
        else:
            where_conditions += f" {column} {op} '{value}' {type}"

    update_query = f"UPDATE {CATALOG}.{SCHEMA}.{replace.table_name} SET {set_conditions_str} WHERE {where_conditions}"
    
    return update_query


def snapshot_retention_query_builder(snapshot_retention: SnapshotRetention):
  seconds = max(snapshot_retention.seconds, 604800)

  snapshot_retention_query = f"""
    ALTER TABLE {CATALOG}.{SCHEMA}.{snapshot_retention.table_name} SET PROPERTIES (
        'vacuum_max_snapshot_age_seconds'='{seconds}')
    """

  return snapshot_retention_query
 
def update_values_multi_condition(update_values_multi_condition:UpdateValuesMultiCondition):
    # SET
    set_conditions_str = ''
    count = 0
    for set_condition in update_values_multi_condition.set:
        if count > 0:
            set_conditions_str = set_conditions_str + ', '
            
        update_column = set_condition.update_column
        update_value = set_condition.update_value
        update_type = f"{TRINO_DATA_TYPE_MAPPING[set_condition.update_type]}"
        
        if update_type != "VARCHAR":
            set_conditions_str += f" {update_column} = {update_value}"
            count = count + 1
        else:
            set_conditions_str += f" {update_column} = '{update_value}'"
            count = count + 1

    #WHERE    
    where_conditions = ''
    for condition in update_values_multi_condition.where:

        column = condition.column_name
        op = condition.op
        value = condition.column_value
        column_type = f"{TRINO_DATA_TYPE_MAPPING[condition.column_type]}"
        
        if column_type != "VARCHAR":
            where_conditions += f" {column} = {value} {op} "
        else:
            where_conditions += f" {column} = '{value}' {op} "
    
    query = f"""UPDATE {CATALOG}.{SCHEMA}.{update_values_multi_condition.table_name} SET {set_conditions_str} WHERE {where_conditions}"""
    
    
    return query


def update_nan_value(update_nan_value:UpdateNanValue):
    column_names = [f"{column.column_name}" for column in update_nan_value.set_nan]

    column_names_str = ", ".join(column_names)

    set_conditions = ''
    for condition in update_nan_value.set_nan:
        column = condition.column_name
        value = condition.column_value
        column_type = f"{TRINO_DATA_TYPE_MAPPING[condition.column_type]}"
        
        if column_type != "VARCHAR":
            set_conditions += f" {column} = {value}"
        else:
            set_conditions += f" {column} ='{value}'"

    sql_query = f"UPDATE {CATALOG}.{SCHEMA}.{update_nan_value.table_name} SET\n  {set_conditions} \nWHERE {column_names_str} is NULL"

    return sql_query
