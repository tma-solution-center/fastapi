from pydantic import BaseModel, Field
from typing import List
import json

class DebeziumRequest(BaseModel):
    database_type: str 
    connector_name: str = "mysql-school-connector"
    debezium_host: str = "debezium:8083"
    db_hostname: str = "mysql"
    port: int = 3306
    user: str = "root"
    password: str = "12345678"
    topic_prefix: str = "mysql"
    database: str = "school"
    schema_name: str = "public"
    table: str = "students"
    kafka_url: str = "kafka1:9092,kafka2:9092,kafka3:9092"


class Session(BaseModel):
    job_path: str = "/opt/bitnami/spark/spark-test.py"
    # driver_memory: str = "1G"
    # driver_cores: int = 1
    executor_memory: str = "1G"
    num_executors: int = 1
    name: str = "Minh test session"
    args: List[str] = ['--topic', 'Minh_topic', 'Truc_topic', '--app-name', 'My Spark app1', '--cores-max', '2']