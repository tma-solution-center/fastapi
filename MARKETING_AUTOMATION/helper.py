from datetime import datetime, timedelta

from MARKETING_AUTOMATION.models import Box, ParamDataModelBox, ParamBirthDayBox
from MARKETING_AUTOMATION.template_constant import SPLIT_LIST_BY_RATIO_FUNC_TEMPLATE, \
    PROCESS_FOR_WAIT_TIME_BOX_TEMPLATE, CALL_SEND_SMS_API_TEMPLATE
from constants import SEND_SMS_API_URL


def generate_template_data_model_box(box: Box):
    sql_query = parse_trino_sql(box.param)

    template = """{step_name} = TrinoOperator(task_id='{step_name}', sql=\"\"\"{sql_query}\"\"\",
    trino_conn_id='test_trino_conn', handler=process_and_push_trino_results, do_xcom_push=True, dag=dag)
    """.format(step_name=box.step_name, sql_query=sql_query)

    return template


def generate_template_wait_until_box(box: Box):
    param = box.param
    function_template = PROCESS_FOR_WAIT_TIME_BOX_TEMPLATE.format(task_id=param.input) + '\n\n'

    template = "{step_name} = PythonOperator(task_id='{step_name}', python_callable=process_for_wait_time_box,\n" \
               "op_kwargs={{'param': {param}}}, provide_context=True, do_xcom_push=True, dag=dag)" \
        .format(step_name=box.step_name, param=param.model_dump())

    return f'{function_template}{template}'


def generate_template_birthday_box(box):
    sql_query = parse_trino_sql_for_birthday_box(box.param)

    template = """{step_name} = TrinoOperator(task_id='{step_name}', sql=\"\"\"{sql_query}\"\"\",
        trino_conn_id='test_trino_conn', handler=process_and_push_trino_results, do_xcom_push=True, dag=dag)
        """.format(step_name=box.step_name, sql_query=sql_query)

    return template


def generate_template_ab_test_box(box):
    function_template = SPLIT_LIST_BY_RATIO_FUNC_TEMPLATE.format(task_id=box.param.input) + '\n\n'

    template = "{step_name} = PythonOperator(task_id='{step_name}', python_callable=split_list_by_ratio,\n" \
               "op_kwargs={{'group_a_ratio': {group_a_percent}, 'group_b_ratio': {group_b_percent}}}, \n" \
               "provide_context=True, do_xcom_push=True, dag=dag)" \
        .format(step_name=box.step_name, group_a_percent=box.param.group_a_percent,
                group_b_percent=box.param.group_b_percent)

    return f'{function_template}{template}'


def generate_template_send_sms_box(box):
    url = SEND_SMS_API_URL

    function_template = CALL_SEND_SMS_API_TEMPLATE.format(task_id=box.param.input, url=url,
                                                          step_name=box.step_name)

    template = "{step_name} = PythonOperator(task_id='{step_name}', python_callable=call_post_api,\n" \
               "op_kwargs={{'param': {param}}}, provide_context=True, dag=dag)" \
        .format(step_name=box.step_name, param=box.param.model_dump())

    return f'{function_template}{template}'


def parse_trino_sql_for_birthday_box(sql_params: ParamBirthDayBox):
    table_name = sql_params.table_name
    select_columns = sql_params.select_columns
    column_name = sql_params.column_name
    time = sql_params.time
    schema = sql_params.schema

    # Lấy ngày hiện tại
    current_date = datetime.now()

    # Tính toán target_date
    target_date = current_date + timedelta(days=time)

    # Kiểm tra xem target_date có phải là tháng mới hay không
    if target_date.month > current_date.month:
        sql_query = f"""
                SELECT {', '.join(select_columns)}
                FROM {schema}.{table_name}
                WHERE day(CAST({column_name} AS DATE)) = day(date_add('day', {time}, CURRENT_DATE))
                AND MONTH(CAST({column_name} AS DATE)) = MONTH(date_add('month', 1, CURRENT_DATE))
            """
    elif target_date.month < current_date.month:
        sql_query = f"""
                SELECT {', '.join(select_columns)}
                FROM {schema}.{table_name}
                WHERE day(CAST({column_name} AS DATE)) = day(date_add('day', {time}, CURRENT_DATE))
                AND MONTH(CAST({column_name} AS DATE)) = MONTH(date_add('month', -1, CURRENT_DATE))
            """
    else:
        sql_query = f"""
                SELECT {', '.join(select_columns)}
                FROM {schema}.{table_name}
                WHERE day(CAST({column_name} AS DATE)) = day(date_add('day', {time}, CURRENT_DATE))
                AND MONTH(CAST({column_name} AS DATE)) = MONTH(CURRENT_DATE)
            """

    return sql_query


def parse_trino_sql(sql_params: ParamDataModelBox):
    trino_selected_columns = {value: index for index, value in enumerate(sql_params.select_columns)}
    sql_template = """
    select {columns_statement}
    from {table}
    where {conditions}
    """

    # generate condition query
    condition_query = ""
    if sql_params.where is not None and len(sql_params.where) > 0:
        for i in range(len(sql_params.where)):
            cond = sql_params.where[i]
            if i < len(sql_params.where) - 1:
                condition_query = condition_query + \
                                  f'{cond.get("column_name")} {cond.get("conditional")} {cond.get("value")} ' \
                                  f'{cond.get("aggregation") if cond.get("aggregation") is not None else ""} '
            else:
                condition_query = condition_query + \
                                  f'{cond.get("column_name")} {cond.get("conditional")} {cond.get("value")}'
    else:
        condition_query = "1=1"

    mapping = {
        "columns_statement": ", ".join(trino_selected_columns),
        "table": f'{sql_params.schema}.{sql_params.table_name}',
        "conditions": f'{condition_query}'
    }

    sql_query = sql_template.format_map(mapping)
    return sql_query


def check_valid_param_segment_box(box_param):
    required_fields = ["segment_name", "columns", "schema"]
    for field in required_fields:
        if not box_param.get(field):
            raise Exception(f"{field} is not empty or null")


def generate_template_segment_box(box):
    # check_valid_param_segment_box(box.param)
    # Extract necessary information from the box
    trino_selected_columns = {value: index for index, value in enumerate(box.param.columns)}
    # generate query
    sql_template = """
        select {columns_statement}
        from {table}
        """
    mapping = {
        "columns_statement": ", ".join(trino_selected_columns),
        "table": f'{box.param.schema}.{box.param.segment_name}'
    }
    sql_query = sql_template.format_map(mapping)

    template = """{step_name} = TrinoOperator(task_id='{step_name}', sql=\"\"\"{sql_query}\"\"\",
        trino_conn_id='test_trino_conn', handler=process_and_push_trino_results, do_xcom_push=True, dag=dag)
        """.format(step_name=box.step_name, sql_query=sql_query)
    return template


