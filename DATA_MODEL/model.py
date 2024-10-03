from decimal import Decimal
from datetime import date, time, datetime
from typing import Optional, Generic, TypeVar, Any, List, Literal, Union
from pydantic import BaseModel, model_validator, Field, ConfigDict

T = TypeVar('T')


class UserInfo(BaseModel):
    username: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class UpdateColumnStatus(BaseModel):
    fields: List[str] = []
    username: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class Column(BaseModel):
    name_column: str
    type: Literal["int", "bool", "float", "decimal",
    "string", "str", "bytes", "date", "time", "datetime",
    "list", "dict", "tuple"
    ]
    value: Optional[Union[int, bool, float, Decimal, str, bytes,
    date, time, datetime, list, dict, tuple]] = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class InsertColumns(BaseModel):
    column_name: str
    column_value: Optional[Union[int, bool, float, Decimal, str, bytes,
    date, time, datetime, list, dict, tuple]] = None
    column_type: Literal["int", "bool", "float", "decimal",
    "str", "string", "bytes", "date", "time", "datetime",
    "list", "dict", "tuple"
    ]
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class UpdateColumns(BaseModel):
    update_column: str
    update_value: Optional[Union[int, bool, float, Decimal, str, bytes,
    date, time, datetime, list, dict, tuple]] = None
    update_type: Literal["int", "bool", "float", "decimal",
    "str","string", "bytes", "date", "time", "datetime",
    "list", "dict", "tuple"
    ]
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class WhereUpdateColumns(BaseModel):
    column: str
    value: Optional[Union[int, bool, float, Decimal, str, bytes,
    date, time, datetime, list, dict, tuple]] = None
    op: str
    type: Optional[str] = None
    column_type: Literal["int", "bool", "float", "decimal",
    "str", "string", "bytes", "date", "time", "datetime",
    "list", "dict", "tuple"
    ] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class WhereUpdateMulti(BaseModel):
    column_name: str
    column_value: Optional[Union[int, bool, float, Decimal, str, bytes,
    date, time, datetime, list, dict, tuple]] = None
    op: Optional[str]
    column_type: Literal["int", "bool", "float", "decimal",
    "str", "bytes", "date", "time", "datetime",
    "list", "dict", "tuple"
    ]
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class SetNan(BaseModel):
    column_name: str
    column_value: Optional[Union[int, bool, float, Decimal, str, bytes,
    datetime.date, datetime.time, datetime, list, dict, tuple]] = None
    column_type: Literal["int", "bool", "float", "decimal",
    "str", "bytes", "date", "time", "datetime",
    "list", "dict", "tuple"
    ]
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


# <---------------------------------------------------------------->

class IcebergTable(BaseModel):
    table_name: str
    username: str
    option: Literal["create_table", "add_columns"]
    values: List[Column]
    model_config = ConfigDict(populate_by_name=True)


class RenameColumn(BaseModel):
    table_name: str
    username: str
    option: Literal["rename_column"]
    old_column: str
    old_type: Literal["int", "bool", "float", "decimal",
    "str", "string", "bytes", "date", "time", "datetime",
    "list", "dict", "tuple"
    ]
    new_column: str
    model_config = ConfigDict(populate_by_name=True)


class DropTable(BaseModel):
    table_name: str
    username: str
    option: Literal["drop_table"]
    model_config = ConfigDict(populate_by_name=True)


class RemoveColumns(BaseModel):
    table_name: str
    username: str
    option: Literal["remove_columns"]
    drop_column_name: str
    model_config = ConfigDict(populate_by_name=True)


class DropAllRow(BaseModel):
    table_name: str
    option: Literal["drop_all_row"]
    username: str

    model_config = ConfigDict(populate_by_name=True)


class Insert(BaseModel):
    table_name: str
    option: Literal["insert"]
    username: str
    values: List[InsertColumns]

    model_config = ConfigDict(populate_by_name=True)


class ReplaceAndEdit(BaseModel):
    table_name: str
    option: Literal["replace_and_edit_row"]
    username: str
    set: List[UpdateColumns]
    where: List[WhereUpdateColumns]

    model_config = ConfigDict(populate_by_name=True)


class SnapshotRetention(BaseModel):
    table_name: str
    username: str
    option: Literal["snapshot_retention"]
    seconds: int

    model_config = ConfigDict(populate_by_name=True)


class UpdateValuesMultiCondition(BaseModel):
    table_name: str
    option: Literal["filter"]
    username: str
    set: List[UpdateColumns]
    where: List[WhereUpdateMulti]

    model_config = ConfigDict(populate_by_name=True)


class UpdateNanValue(BaseModel):
    table_name: str
    option: Literal["update_nan_value"]
    username: str
    set_nan: List[SetNan]

    model_config = ConfigDict(populate_by_name=True)


class ColumnDto(BaseModel):
    name: str = None
    type: str = None
    status: bool

    model_config = ConfigDict(populate_by_name=True)


class TableDto(BaseModel):
    table: str = None
    columns: list[ColumnDto] = None
    status: bool = False

    model_config = ConfigDict(populate_by_name=True)


class SchemaDto(BaseModel):
    tables: list[TableDto] = []

    model_config = ConfigDict(populate_by_name=True)

    # @model_validator(mode='before')
    # def auto_cast_param(cls, values):
    #     tables = []
    #     if values.get("tables") is not None and isinstance(values.get("tables"), list):
    #         for table in values.get("tables"):
    #             tables.append(TableDto(**table))
    #     values['tables'] = tables
    #     return values


class SchemaInfo(BaseModel):
    id: Optional[str] = None
    schema: SchemaDto = None
    lastModified: str = None

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode='before')
    def auto_cast_param(cls, values):
        if values is None:
            return SchemaInfo()
        if values.get("schema") is not None and isinstance(values.get("schema"), dict):
            values['schema'] = SchemaDto(**values.get("schema"))
        return values


# Define Pydantic models
class ResponseJson(BaseModel, Generic[T]):
    data: Optional[T]
    status: int
    message: Optional[str]

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class SetDto(BaseModel):
    update_column: Optional[str] = None
    update_value: Optional[str] = None
    update_type: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class InfoColumnDto(BaseModel):
    column_name: Optional[str] = None
    column_value: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class WhereDto(BaseModel):
    original_column: Optional[str] = None
    original_value: Optional[str] = None
    original_type: Optional[str] = None
    column_name: Optional[str] = None
    column_value: Optional[str] = None
    column_type: Optional[str] = None
    column: Optional[str] = ""
    op: Optional[str] = ""
    value: Optional[str] = ""
    type: Optional[str] = ""

    model_config = ConfigDict(populate_by_name=True)


class IdDto(BaseModel):
    id_column: Optional[str] = None
    idValue: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ConditionDto(BaseModel):
    column: Optional[str] = ""
    op: Optional[str] = ""
    value: Optional[str] = ""
    type: Optional[str] = ""

    model_config = ConfigDict(populate_by_name=True)


class FieldDto(BaseModel):
    name_column: Optional[str] = None
    type: Optional[Literal["int", "bool", "float", "decimal",
    "str", "string", "bytes", "date", "time", "datetime",
    "list", "dict", "tuple"
    ]] = None
    column_name: Optional[str] = None
    column_value: Optional[Union[int, bool, float, Decimal, str, bytes,
    date, time, datetime, list, dict, tuple]] = None
    column_type: Optional[Literal["int", "bool", "float", "decimal",
    "str", "string", "bytes", "date", "time", "datetime",
    "list", "dict", "tuple"
    ]] = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class DataModelRequest(BaseModel, Generic[T]):
    table_name: Optional[str] = None
    option: Optional[str] = None
    values: Optional[list[T]] = None
    set: Optional[list[SetDto]] = None
    set_nan: Optional[list[InfoColumnDto]] = None
    set_values: Optional[list[InfoColumnDto]] = None
    where_values: Optional[list[InfoColumnDto]] = None
    where: Optional[list[WhereDto]] = None
    id: Optional[IdDto] = None
    conditions: Optional[list[ConditionDto]] = None
    username: str = ""
    drop_column_name: Optional[str] = ""
    new_table_name: Optional[str] = ""
    old_column: Optional[str] = ""
    old_type: Optional[str] = ""
    new_column: Optional[str] = ""
    seconds: Optional[str] = ""

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode='before')
    def auto_cast_param(cls, values):
        print(values)
        if values is None:
            return SchemaInfo()
        if values.get("set") is not None and isinstance(values.get("set"), list):
            list_temp = []
            for item in values.get("set"):
                list_temp.append(SetDto(**item))
            values['set'] = list_temp

        if values.get("set_nan") is not None and isinstance(values.get("set_nan"), list):
            list_temp = []
            for item in values.get("set_nan"):
                list_temp.append(InfoColumnDto(**item))
            values['set_nan'] = list_temp

        if values.get("set_values") is not None and isinstance(values.get("set_values"), list):
            list_temp = []
            for item in values.get("set_values"):
                list_temp.append(InfoColumnDto(**item))
            values['set_values'] = list_temp

        if values.get("where_values") is not None and isinstance(values.get("where_values"), list):
            list_temp = []
            for item in values.get("where_values"):
                list_temp.append(InfoColumnDto(**item))
            values['where_values'] = list_temp

        if values.get("where") is not None and isinstance(values.get("where"), list):
            list_temp = []
            for item in values.get("where"):
                list_temp.append(WhereDto(**item))
            values['where'] = list_temp

        if values.get("id") is not None and isinstance(values.get("id"), dict):
            values['id'] = IdDto(**values.get("id"))

        if values.get("conditions") is not None and isinstance(values.get("conditions"), list):
            list_temp = []
            for item in values.get("conditions"):
                list_temp.append(ConditionDto(**item))
            values['conditions'] = list_temp
        return values


class RequestPaging(BaseModel, Generic[T]):
    sortField: Optional[str] = None
    filters: Optional[T] = None
    sortBy: Optional[str] = None
    page: int = 0
    size: int = 0
    username: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class DetailsTableDto(BaseModel):
    database: Optional[str] = None
    tableName: Optional[str] = None
    filter: Optional[str] = None
    search: Optional[str] = None
    idOldVersion: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class DateRange(BaseModel):
    startDate: Optional[str] = Field(default=None)
    endDate: Optional[str] = Field(default=None)

    model_config = ConfigDict(populate_by_name=True)

    def get_start_date(self) -> str:
        return self.default_if_empty(self.startDate)

    def get_end_date(self) -> str:
        return self.default_if_empty(self.endDate)

    @staticmethod
    def default_if_empty(value: Optional[str]) -> str:
        return value or ""


class PaginationResponse(BaseModel):
    content: Optional[List[Any]] = None
    page: int = 0
    size: int = 0
    totalPages: Optional[int] = None
    totalItems: Optional[int] = None
    sorter: Optional[str] = None
    dateRangeDefault: Optional[DateRange] = None
    numberPhone: Optional[int] = None
    numberEmail: Optional[int] = None
    numberCustomerId: Optional[int] = None
    keys: Optional[List[Any]] = None
    fileName: Optional[List[Any]] = None
    url: Optional[str] = None
    urlToFile: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class RestoreDto(BaseModel):
    username: Optional[str] = None
    table_name: Optional[str] = None
    action: Optional[str] = None
    snapshots_id: Optional[str] = None
    shorter_list: Optional[List[str]] = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DateDto(BaseModel):
    year: str = None
    month: str = None
    day: str = None

    model_config = ConfigDict(populate_by_name=True)


class DownloadDataDto(BaseModel):
    username: Optional[str] = None
    bucket: Optional[str] = None
    key: Optional[str] = None
    table: Optional[str] = None
    date: Optional[DateDto] = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DataStorageInfo(BaseModel):
    type: Literal["minio", "s3"] = None
    access_key: str = None
    secret_key: str = None
    bucket_name: str = None
    minio_url: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)
