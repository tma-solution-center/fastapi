from fastapi import APIRouter
from datetime import datetime, timezone
from fastapi.responses import JSONResponse

from MARKETING_AUTOMATION.helper import (generate_template_data_model_box, generate_template_wait_until_box,
                                         generate_template_birthday_box, generate_template_segment_box,
                                         generate_template_ab_test_box, generate_template_send_sms_box)

import logging

from MARKETING_AUTOMATION.models import Request
from MARKETING_AUTOMATION.template_constant import PROCESS_AND_PUSH_TRINO_RESULT
from constants import NFS_PATH

logger = logging.getLogger("main")
logging.basicConfig()
logger.setLevel(logging.INFO)
start_time_execution = datetime.now(timezone.utc)
datetime_format = "%Y%m%d%H%M%S"

router = APIRouter()


@router.post("/airflow/generate-dag-new", tags=["MARKETING_AUTOMATION"])
def create_dag(input_json: Request):
    import_str = "from airflow import DAG \nimport pandas as pd \n"

    try:
        default_args_template = "default_args = {{'owner': '{owner}', 'depends_on_past': False," \
                                " 'start_date': '{start_date}', 'retries': '{retries}'}}" \
            .format(owner=input_json.dag_config['default_args']['owner'],
                    start_date=input_json.dag_config['default_args']['start_date'],
                    retries=input_json.dag_config['default_args']['retries'])

        dag_object_template = \
            "dag = DAG(dag_id='{dag_id}', default_args=default_args, schedule_interval='{schedule_interval}')".format(
                dag_id=input_json.dag_config['dag_id'], schedule_interval=input_json.dag_config['schedule_interval'])

        # Process boxes in json request
        boxes = input_json.boxes
        boxes_template, list_task, operator_import = create_task_airflow_from_boxes(boxes)

        import_str = f'{import_str}{operator_import}'
        dag_code = f"{import_str}\n{default_args_template}\n{dag_object_template}\n" \
                   f"{PROCESS_AND_PUSH_TRINO_RESULT}\n\n" \
                   f"{boxes_template}\n\n{' >> '.join(list_task)}"

        # python file path for airflow
        dag_filepath = f"{NFS_PATH}{input_json.dag_config['dag_id']}.py"

        # Ghi nội dung DAG vào file
        with open(dag_filepath, 'w') as file:
            file.write(dag_code)

        logger.info(f"Creating DAG file successfully.")
        return {"message": f"DAG file '{input_json.dag_config['dag_id']}.py' has been created successfully."}
    except Exception as e:
        logger.error(f"Creating DAG file failed due to: {str(e)}")
        return JSONResponse(status_code=400, content={"message": str(e)})


def create_task_airflow_from_boxes(boxes):
    boxes_template = ''
    list_task = []
    operator_import_list = []
    for box in boxes:
        if box.box_name == 'data_model':
            operator_import_list.append('from airflow.providers.trino.operators.trino import TrinoOperator \n')
            template = generate_template_data_model_box(box)
            # add task aiflow
            list_task.append(box.step_name)
            boxes_template = boxes_template + '\n\n' + template
        elif box.box_name == 'wait_until':
            operator_import_list.append('from airflow.operators.python import PythonOperator \n')
            operator_import_list.append('import time \n')
            operator_import_list.append('from datetime import datetime \n')
            template = generate_template_wait_until_box(box)
            # add task aiflow
            list_task.append(box.step_name)
            boxes_template = boxes_template + '\n\n' + template

        elif box.box_name == 'birthday':
            operator_import_list.append('from airflow.providers.trino.operators.trino import TrinoOperator \n')
            template = generate_template_birthday_box(box)
            # add task aiflow
            list_task.append(box.step_name)
            boxes_template = boxes_template + '\n\n' + template

        elif box.box_name == 'segment':
            operator_import_list.append('from airflow.providers.trino.operators.trino import TrinoOperator \n')
            template = generate_template_segment_box(box)
            # add task aiflow
            list_task.append(box.step_name)
            boxes_template = boxes_template + '\n\n' + template

        elif box.box_name == 'ab_test':
            operator_import_list.append('from airflow.operators.python import PythonOperator \n')
            template = generate_template_ab_test_box(box)
            # add task aiflow
            list_task.append(box.step_name)
            boxes_template = boxes_template + '\n\n' + template

        elif box.box_name == 'send_sms':
            operator_import_list.append('from airflow.operators.python import PythonOperator \n')
            operator_import_list.append('import requests \n')
            template = generate_template_send_sms_box(box)
            # add task aiflow
            list_task.append(box.step_name)
            boxes_template = boxes_template + '\n\n' + template

    operator_import = ''
    # deduplicate import
    if len(operator_import_list) > 0:
        dedup_import_operator_list = list(set(operator_import_list))
        operator_import = ''.join(dedup_import_operator_list)

    return boxes_template, list_task, operator_import
