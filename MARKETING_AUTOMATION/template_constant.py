PROCESS_AND_PUSH_TRINO_RESULT = """
def process_and_push_trino_results(cursor, **kwargs):    
    # get column names
    column_names = [desc[0] for desc in cursor.description]
    # get records
    records = cursor.fetchall()    
    
    result = {
        "column_names": column_names,
        "records": records
    }
    
    return result   
"""

SPLIT_LIST_BY_RATIO_FUNC_TEMPLATE = """
def split_list_by_ratio(group_a_ratio, group_b_ratio, **kwargs):
    ti = kwargs['ti']    
    input_list = ti.xcom_pull(task_ids='{task_id}')
    column_names = input_list.get('column_names')
    records = input_list.get('records')
    
    split_index = int(len(records) * group_a_ratio)
   
    group_a = records[:split_index]
    group_b = records[split_index:]
    result= {{
        "columns_name": column_names,
        "group_a": group_a,
        "group_b": group_b
    }}

    return result
"""

PROCESS_FOR_WAIT_TIME_BOX_TEMPLATE = """
def process_for_wait_time_box(param, **kwargs):
    ti = kwargs['ti']
    data = ti.xcom_pull(task_ids='{task_id}')
    if 'wait_time' not in param or param['wait_time'] is None:
        date_string = f"{{param['year']}}-{{param['month']}}-{{param['day']}} {{param['hour']}}:{{param['minute']}}:{{param['second']}}"
        date_set = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")

        # Get current datetime
        current_date = datetime.now()
        # Calculate the total number of seconds difference
        time_difference = date_set - current_date
        total_seconds = round(time_difference.total_seconds())
        wait_time = total_seconds
    else:
        wait_time = param['wait_time']
    
    print(f'Sleep: {{wait_time}}')
    print(f'Start: {{datetime.now()}}')    
    time.sleep(wait_time)
    print(f'End: {{datetime.now()}}')
    return data
"""

CALL_SEND_SMS_API_TEMPLATE = """
def call_post_api(param, **kwargs):
    ti = kwargs['ti']
    data = ti.xcom_pull(task_ids='{task_id}')
    records = data.get("records")
    column_names = data.get("column_names")
    df = pd.DataFrame(records, columns=column_names)
    
    # get list phones
    phones =  df[param.get('column_name')].tolist()
    
    url = "{url}"

    payload = {{
        "workflowId": "work_flow_id",
        "nodeName": "{step_name}",
        "apiKey": param.get('apiKey'),
        "secretKey": param.get('secretKey'),
        "params": [],
        "linkWeb": param.get('link_tracking'),
        "templateId": param.get('templateName')
    }}
    

    # todo: set value for customer_unified_key, tag_id
    for i in range(len(phones)):
        payload['params'].append({{
            "phones": str(phones[i].replace(" ", "").replace("-", "")),
            "email": str(phones[i].replace(" ", "").replace("-", "")),
            "customerId": str('customer_unified_key[i]'),
            "params": param.get('params'),
            "tagId": 'tag_id'
        }})
    headers = {{
        'Content-Type': 'application/json'
    }}

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # Raise an exception for HTTP errors

    # Log the response data
    data = response.json()
    print(data)

    # Optionally push data to XCom
    kwargs['ti'].xcom_push(key='api_data', value=data)
"""
