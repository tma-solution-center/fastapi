from airflow import DAG
from datetime import datetime
from string import Template
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.trino.operators.trino import TrinoOperator
import json

# --- Variables ---
operators = dict()
boxes = $boxes
username = "$username"
job_name = "$job_name"
trino_task_ids = []
trino_selected_columns = dict()

# --- Start functions ---
def proccess_data(**kwargs):
    query_results = kwargs['ti'].xcom_pull(task_ids=kwargs['trino_task_ids'])
    print('--- Start proccess data ---')
    # query_results = json.loads(query_results.replace("'", '"'))

    url = "https://dev.cdp-tma.link/api/cdp-data/api/send-message/mailchimp"
    json_obj = {
      "listId": "bf49e1fc4f",
      "workflowId": "$work_flow_id",
      "nodeName": kwargs["nodeName"],
      "apiKey": kwargs["apiKey"],
      "secretKey": kwargs['secretKey'],
      "subject": kwargs['subject'],
      "params": [],
      "templateId": json.dumps(kwargs['templateId'])
    }

    # Thông tin email
    for user in query_results[0]:
        json_obj['params'].append({
            "phones": user[trino_selected_columns["phone"]],
            "email": user[trino_selected_columns["email"]],
            "customerId": user[trino_selected_columns["id"]],
            "tagId": "abbufbu-15454sdf-sfd"
        })
    
    print(f"email_data: {json.dumps(json_obj)}")


def parse_trino_sql(sql_params):
    sql_template = f"""
    select $columns_statement
    from $table
    where $conditions
    """
    mapping = {
        "columns_statement": ", ".join(trino_selected_columns),
        "table": f'{sql_params["schema"]}.{sql_params["table_name"]}',
        "conditions": "1=1" if len(sql_params["where"]) == 0 else " and ".join([f'{con["column_name"]} {con["conditional"]} {con["value"]}' for con in sql_params["where"]])
    }
    trino_sql = Template(sql_template).substitute(mapping)
    return trino_sql

# --- End functions ---


# Step 3: Creating DAG Object
dag = DAG(dag_id="$dag_id",
    default_args=$default_args,
    schedule_interval="$schedule_interval", 
    catchup=$catchup
)


for box in boxes:
    if box["step_type"] == "dummy":
        operators[box["step_name"]] = DummyOperator(task_id = box["step_name"], dag = dag)
    elif box["step_type"] == "bash":
        operators[box["step_name"]] = BashOperator(task_id = box["step_name"], dag = dag, bash_command=box["param"]["command"])
    elif box["step_type"] == "trino":
        trino_selected_columns = {value: index for index, value in enumerate(box["param"]["select_columns"])}
        trino_task_ids.append(box["step_name"])
        trino_sql = parse_trino_sql(box["param"])
        operators[box["step_name"]] = TrinoOperator(task_id = box["step_name"], dag = dag, sql=trino_sql, trino_conn_id='test_trino_conn', handler=list)
    elif box["step_type"] == "python":
        op_kwargs={
            "trino_task_ids": trino_task_ids,
            "nodeName": box["step_name"],
            "apiKey": box['param']['apiKey'],
            "secretKey": box['param']['secretKey'],
            "subject": box["param"]["subject"],
            "templateId": box['param']['templateId']
        }
        operators[box["step_name"]] = PythonOperator(task_id = box["step_name"], dag = dag, python_callable=proccess_data, op_kwargs=op_kwargs)

# Setting up dependencies
for box in boxes:
    # Single parent
    if box["param"]["input"] != "":
        operators[box["step_name"]].set_upstream(operators[box["param"]["input"]])

