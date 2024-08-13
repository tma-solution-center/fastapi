from pydantic import BaseModel, model_validator
from typing import Optional, Literal, List, Union


# class DagConfig(BaseModel):
#     dag_id: str
#     schedule_interval: str
#     start_date: str
#     catchup: bool
#     tags: List[str]

class ParamDataModelBox(BaseModel):
    schema: str
    table_name: str
    select_columns: list
    where: Optional[list] = None


class ParamWaitUntilBox(BaseModel):
    input: Optional[str] = None
    wait_time: Optional[int] = None
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    hour: Optional[int] = None
    minute: Optional[int] = None
    second: Optional[int] = None


class ParamBirthDayBox(BaseModel):
    schema: str
    table_name: str
    column_name: str
    select_columns: list
    time: int


class ParamSegmentBox(BaseModel):
    schema: str
    segment_name: str
    columns: list


class ParamSendSmsBox(BaseModel):
    input: str
    column_name: str
    apiKey: str
    secretKey: str
    templateName: str
    params: list
    provider: str
    input_id: str
    link_tracking: str


class ParamABTestBox(BaseModel):
    input: str
    group_a_percent: float
    group_b_percent: float

    @model_validator(mode='before')
    def check_percentages(cls, values):
        if not isinstance(values, ParamABTestBox):
            return values

        group_a_percent = values.get('group_a_percent', 0)
        group_b_percent = values.get('group_b_percent', 0)

        if group_a_percent + group_b_percent != 1:
            raise ValueError('The sum of value_percent_a and value_percent_b must be equal 1.')
        return values


class Box(BaseModel):
    box_name: Literal[
        "data_model", "birthday", "segment", "wait_until", "ab_test", "send_sms"]
    step_name: Literal[
        "data_model_name", "birthday_name", "segment_name", "wait_until_name", "AB_test_name", "send_sms"]
    param: Union[
        ParamDataModelBox, ParamWaitUntilBox, ParamBirthDayBox,
        ParamSegmentBox, ParamABTestBox, ParamSendSmsBox]

    @model_validator(mode='before')
    def auto_cast_param(cls, values):
        box_name = values.get("box_name")
        param = values.get("param")

        if box_name == "data_model" and isinstance(param, dict):
            values["param"] = ParamDataModelBox(**param)

        elif box_name == "wait_until" and isinstance(param, dict):
            values["param"] = ParamWaitUntilBox(**param)

        elif box_name == "birthday" and isinstance(param, dict):
            values["param"] = ParamBirthDayBox(**param)

        elif box_name == "segment" and isinstance(param, dict):
            values["param"] = ParamSegmentBox(**param)

        elif box_name == "send_sms" and isinstance(param, dict):
            values["param"] = ParamSendSmsBox(**param)

        elif box_name == "ab_test" and isinstance(param, dict):
            values["param"] = ParamABTestBox(**param)

        return values


class Request(BaseModel):
    job_name: str
    username: str
    work_flow_id: str
    dag_config: dict
    boxes: List[Box]
