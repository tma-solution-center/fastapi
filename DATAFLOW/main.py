import uvicorn
from datetime import datetime, timezone
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from DATAFLOW.helper import *
from DATAFLOW.model import *
from constants import *

import logging

logger = logging.getLogger("main")
logging.basicConfig()
logger.setLevel(logging.INFO)
start_time_execution = datetime.now(timezone.utc)
datetime_format = "%Y%m%d%H%M%S"

router = APIRouter()


@router.post('/create_dataflow/', tags=["DATA_FLOW"])
def create_dataflow(request: Dataflow):
    try:
        response: ResultModel = handler(request)
        return JSONResponse(status_code=(200 if response.status == 1 else 400), content={"message": response.message})
    except Exception as e:
        logger.error(f"Creating the dataflow failed due to: {str(e)}")
        return JSONResponse(status_code=400, content={"message": "Creating the dataflow failed"})


def handler(request: Dataflow):
    node_dict = {}
    pop_list = []
    boxes = request.boxes
    username = request.username
    flow_name = request.flow_name
    create_result = data_process_result = None

    for box in boxes:
        box_name = box.box_name
        step_name = box.step_name
        param = box.param

        if box_name == 'DATA_MODEL':
            table_name = f'{DEFAULT_CATALOG}.{DEFAULT_SCHEMA}.{param.table_name}'
            node_dict[step_name] = table_name
            pop_list.append(table_name)
            logger.info(f"Data model table name: {table_name}")
        elif box_name == 'SELECT_COLUMNS':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_select(table_name, param, username, flow_name, step_name,
                                                               start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'DROP_COLUMNS':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_select(table_name, param, username, flow_name, step_name,
                                                               start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'RENAME_COLUMNS':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_rename_column(table_name, param, username, flow_name, step_name,
                                                                      start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'ADD_COLUMNS':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_add_columns(table_name, param, username, flow_name, step_name,
                                                                    start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'DROP_DUPLICATES':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_drop_duplicates(table_name, param, username, flow_name,
                                                                        step_name,
                                                                        start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'CASE':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_case(table_name, param, username, flow_name, step_name,
                                                             start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'DROP_NULL_RECORDS':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_drop_null_records(table_name, param, username, flow_name,
                                                                          step_name,
                                                                          start_time_execution.strftime(
                                                                              datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'REPLACE_VALUE':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_replace_value(table_name, param, username, flow_name, step_name,
                                                                      start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'GROUP_BY':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_group_by(table_name, param, username, flow_name, step_name,
                                                                 start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'CHANGE_TYPE':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_change_type(table_name, param, username, flow_name, step_name,
                                                                    start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'FILTER':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_filter(table_name, param, username, flow_name, step_name,
                                                               start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'JOIN':
            table_left = node_dict[param.left_input]
            table_right = node_dict[param.right_input]
            create_result, table_name = create_table_as_join(table_left, table_right, param, username, flow_name,
                                                             step_name, start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'SAMPLE_DATA':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_sample_data(table_name, param, username, flow_name, step_name,
                                                                    start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'UNION':
            table_left = node_dict[param.left_input]
            table_right = node_dict[param.right_input]
            create_result, table_name = create_table_as_union(table_left, table_right, param, username, flow_name,
                                                             step_name, start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'CHANGE_SCHEMA':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_change_schema(table_name, param, username, flow_name, step_name,
                                                               start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")
        elif box_name == 'FILL_NULL':
            table_name = node_dict[param.input]
            create_result, table_name = create_table_as_fill_null(table_name, param, username, flow_name, step_name,
                                                               start_time_execution.strftime(datetime_format))
            node_dict[step_name] = table_name
            logger.info(f"Status of table {table_name}: {create_result.status}")

        elif box_name == 'DATA_MODEL_DESTINATION':
            try:
                table_name = node_dict[param.input]
                data_process_result = process_data_model_destination(table_name, param)
                logger.info(f"Data process status: {data_process_result.status}, message:{data_process_result.message}")
            except Exception as e:
                drop_tables(node_dict, pop_list)
                raise e

    drop_result: List[ResultModel] = drop_tables(node_dict, pop_list)
    failed_drop_results = []
    failed_drop_results = [res for res in drop_result if res.status == 0]

    if create_result.status == 1 and data_process_result.status == 1 and failed_drop_results == []:
        return ResultModel(1, f"Dataflow {flow_name} was created successfully")
    else:
        return ResultModel(0, "Creating the dataflow failed")
