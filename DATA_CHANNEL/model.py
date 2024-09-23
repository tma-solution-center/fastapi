from typing import Optional

from pydantic import BaseModel


class ConnectionDetails(BaseModel):
    Group_Name: str
    Host: str
    Port: int
    Database_User: str
    Password: str
    Database_Name: str
    Table_Name: str = None
    Col_Name: Optional[str] = None
    Max_Rows_Per_Flow_File: Optional[int] = None
    Output_Batch_Size: Optional[int] = None