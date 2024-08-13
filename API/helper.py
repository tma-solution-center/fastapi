from pydantic import BaseModel
from typing import List, Literal, Optional
from decimal import Decimal
from datetime import date, time, datetime
from dateutil.parser import isoparse
from dateutil.tz import tzutc
from typing import List,Literal,Optional,Union,Any
from DATA_MODEL.helper import *
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


class Value(BaseModel):
    value: List[str]

class Column(BaseModel):
    column_name: str
    column_type: Literal["int", "bool", "float", "decimal",
                         "str", "bytes", "date", "time", "datetime",
                         "list", "dict", "tuple"
                         ]

class UpdateColumns(BaseModel):
    table_name_destination: str
    type: str
    key_columns: Optional[str] = None
    columns: List[Column]
    values: List[Value]

#------

class InsertColumns(BaseModel):
    column_name: str
    column_value: Optional[Union[int,bool,float,Decimal,str,bytes,
                          date,time,datetime,list,dict,tuple]] = None
    column_type: Literal["int","bool","float","decimal",
                  "str","bytes","date","time","datetime",
                  "list","dict","tuple"
                  ]


class UpdateColumnMappings(BaseModel):
    update_column: str
    update_value: Optional[Union[int,bool,float,Decimal,str,bytes,
                          date,time,datetime,list,dict,tuple]] = None
    update_type: Literal["int","bool","float","decimal",
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

class Insert(BaseModel):
    table_name:str
    option: Literal["insert"]
    username: str
    values: List[InsertColumns]


class UpdateValuesMultiCondition(BaseModel):
    table_name:str
    option: Literal["filter"]
    username: str
    set: List[UpdateColumnMappings]
    where: List[WhereUpdateMulti]

class InputDetails(BaseModel):
    column: str

class OutputDetails(BaseModel):
    column: str
    type: str

class ColumnMapping(BaseModel):
    input: InputDetails
    output: OutputDetails

class Value(BaseModel):
    value: List[Any]

class MappingData(BaseModel):
    table_name_destination: str
    type: str
    mappings: List[ColumnMapping]
    values: List[Value]

def convert_value(val, column_type):
    try:
        if column_type == "int":
            return str(int(val))
        elif column_type == "float":
            return str(float(val))
        elif column_type == "decimal":
            return str(Decimal(val))
        elif column_type == "bool":
            return str(val).lower()
        elif column_type == "date":
            return f"DATE '{date.fromisoformat(val)}'"
        elif column_type == "time":
            return f"TIME '{time.fromisoformat(val)}'"
        elif column_type == "datetime":
            dt = isoparse(val).astimezone(tzutc()).replace(tzinfo=None)
            return f"TIMESTAMP '{dt.strftime('%Y-%m-%d %H:%M:%S')}'"
        else:
            return f"'{str(val)}'"
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert value '{val}' to {column_type}: {e}")

def insert_table_destination(insert: UpdateColumns) -> str:
    column_names = ", ".join([col.column_name for col in insert.columns])

    formatted_values = []

    for val in insert.values:
        formatted_row = []
        for col, v in zip(insert.columns, val.value):
            converted_value = convert_value(v, col.column_type)
            formatted_row.append(converted_value)
        formatted_values.append(f"({', '.join(formatted_row)})")

    formatted_values_str = ", ".join(formatted_values)

    query = f"""INSERT INTO {CATALOG}.{SCHEMA}.{insert.table_name_destination} ({column_names}) VALUES {formatted_values_str}"""

    return query

def update_table_destination(update_values: UpdateColumns):
    key_columns = update_values.key_columns.split(",") if update_values.key_columns else []

    column_names = ", ".join([col.column_name for col in update_values.columns])

    formatted_values = []

    for val in update_values.values:
        formatted_row = []
        for col, v in zip(update_values.columns, val.value):
            converted_value = convert_value(v, col.column_type)
            formatted_row.append(converted_value)
        formatted_values.append(f"({', '.join(formatted_row)})")

    formatted_values_str = ", ".join(formatted_values)

    set_clauses = ", ".join([f"{col.column_name} = s.{col.column_name}" for col in update_values.columns])

    # Constructing the ON condition for the merge statement
    on_condition = " AND ".join([f"t.{col} = s.{col}" for col in key_columns])

    query = f"""
    MERGE INTO {CATALOG}.{SCHEMA}.{update_values.table_name_destination} t
    USING (VALUES {formatted_values_str}) AS s({column_names})
    ON {on_condition}
    WHEN MATCHED THEN UPDATE SET {set_clauses}"""

    return query

def upsert_table_destination(upsert:UpdateColumns):
    key_columns = upsert.key_columns.split(",") if upsert.key_columns else []

    column_names = ", ".join([col.column_name for col in upsert.columns])

    formatted_values = []

    for val in upsert.values:
        formatted_row = []
        for col, v in zip(upsert.columns, val.value):
            converted_value = convert_value(v, col.column_type)
            formatted_row.append(converted_value)
        formatted_values.append(f"({', '.join(formatted_row)})")

    formatted_values_str = ", ".join(formatted_values)

    set_clauses = ", ".join([f"{col.column_name} = s.{col.column_name}" for col in upsert.columns])

    # Constructing the ON condition for the merge statement
    on_condition = " AND ".join([f"t.{col} = s.{col}" for col in key_columns])

    query = f"""
    MERGE INTO {CATALOG}.{SCHEMA}.{upsert.table_name_destination} t
    USING (VALUES {formatted_values_str}) AS s({column_names})
    ON {on_condition}
    WHEN MATCHED THEN UPDATE SET {set_clauses}
    WHEN NOT MATCHED
        THEN INSERT ({column_names}) VALUES ({', '.join(['s.' + col.column_name for col in upsert.columns])})
    """

    return query

#-------

def mapping_data_insert(mapping_value):
    source_mapping = {columns.input.column : (columns.output.column, columns.output.type) for columns in mapping_value.mappings}
    print(source_mapping)
    output = []
    for item in mapping_value.values:
        entry = [
            {
                'column_name': source_mapping[key][0],
                'column_value': value,
                'column_type': source_mapping[key][1]
            }
            for key, value in zip(source_mapping.keys(), item.value)
        ]
        output.append(entry)
    query = []
    for value in output:
        columns = [InsertColumns(**val) for val in value]
        insert_operation = Insert(
            table_name=mapping_value.table_name_destination,
            option="insert",
            username="admin",
            values=columns
        )
        query.append(insert_row_query_builder(insert_operation))
    return query

def mapping_data_update(mapping_value):
    source_mapping = {columns.input.column : (columns.output.column, columns.output.type) for columns in mapping_value.mappings}
    print(source_mapping)
    output = []
    for item in mapping_value.values:
        entry = [
            {
                'update_column': source_mapping[key][0],
                'update_value': value,
                'update_type': source_mapping[key][1]
            }
            for key, value in zip(source_mapping.keys(), item.value)
        ]
        output.append(entry)
    query = []

    for value in output:
        columns = [UpdateColumnMappings(**val) for val in value]

        where = {
            'column_name': value[0]['update_column'],
            'column_value': value[0]['update_value'],
            'op': '',
            'column_type': value[0]['update_type']
        }   
        conditions = [WhereUpdateMulti(**where)]
        update_operation = UpdateValuesMultiCondition(
            table_name=mapping_value.table_name_destination,
            option="filter",
            username="admin",
            set=columns,
            where= conditions
        )
        query.append(update_values_multi_condition(update_operation))
    return query

def mapping_data_upsert(mapping_value):
    source_mapping = {columns.input.column : (columns.output.column, columns.output.type) for columns in mapping_value.mappings}
    print(source_mapping)
    output = []
    for item in mapping_value.values:
        output.append(item.value)
    keys =  list(source_mapping.keys())
    output_columns = [source_mapping[key][0] for key in keys]
    column_type_source = [source_mapping[key][1] for key in keys]
    column_types = [f"{TRINO_DATA_TYPE_MAPPING[column]}" for column in column_type_source]

    set_values = []
    for d, s in zip(output_columns, keys):
        set_values.append(f"{d} = s.{s}")
    
    values_formatted = []
    for column_values in output:
        formatted_column_values = []
        for value, column_type in zip(column_values, column_types):
            if column_type != "VARCHAR":
                formatted_column_values.append(str(value))
            else:
                formatted_column_values.append(f"'{value}'")
        values_formatted.append(f'({", ".join(formatted_column_values)})')
    VALUES = ",\n\t\t".join(values_formatted)
    values_name = [f"s.{name}" for name in keys]
    query = f"""MERGE INTO {CATALOG}.{SCHEMA}.{mapping_value.table_name_destination} t 
            USING (
                VALUES {VALUES}
                ) AS s({', '.join(keys)})
                ON (t.{output_columns[0]} = s.{keys[0]})
                WHEN MATCHED
                    THEN UPDATE SET {', '.join(set_values)}
                WHEN NOT MATCHED
                    THEN INSERT ({', '.join(output_columns)})
                        VALUES({', '.join(values_name)})"""
    print(query)
    

    return query