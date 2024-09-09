from enum import Enum


class DataModelEnum(Enum):
    CREATE_TABLE = "create_table"
    ADD_COLUMNS = "add_columns"
    REMOVE_COLUMNS = "remove_columns"
    RENAME_TABLE = "rename_table"
    DROP_TABLE = "drop_table"
    RENAME_COLUMN = "rename_column"
    INSERT_ROW = "insert"
    REPLACE_AND_EDIT_ROW = "replace_and_edit_row"
    DROP_ALL_ROW = "drop_all_row"


    def get_key(self):
        return self.name

    def get_value(self):
        return self.value
