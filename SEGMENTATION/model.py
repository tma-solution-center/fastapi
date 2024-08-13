from typing import Optional,Literal,List
from pydantic import BaseModel

class WhereCondition(BaseModel):
    data_attribute:str
    type_attribute:Literal["string","int"]
    operator:Literal["!=",">="]
    value:List[str]
    option:Literal["and","or",""]

class HavingCondition(WhereCondition):
    aggregate:Literal["sum"]

class Group(BaseModel):
    username:str
    segment_name:str
    group_name:str
    select_columns:Optional[List[str]]=None
    type:Literal["customer_unified_key"]
    action:Literal["calculator_group","save_group"]
    table_name:str
    where:Optional[List[WhereCondition]]=None
    option_with_having:Optional[Literal["and"]]=""
    edit_group:Optional[str]=""
    having:Optional[List[HavingCondition]]=None



class SegmentOrGroup(BaseModel):
    name:str
    option:Literal["excluded","intersected"]
    select_columns:Optional[List[str]]=None


class Segment(BaseModel):
    username:str
    segment_name:str
    action:Literal["calculator_segment","save_segment"]
    type:Literal["customer_unified_key"]
    segment_or_group:List[SegmentOrGroup]
    edit_segment:Optional[str]=""



class ResultModel:
    def __init__(self, status: Literal[0, 1], message: str):
        self.status = status
        self.message = message
