import sys
sys.path.append('C:\\Users\\milli\\Portfolio\\weather_Project')

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import datetime
from datetime import timedelta
from weather_Project.final_project_script import etl_process

default_args = {
    'owner': 'final_project',
    'depends_on_past': False,
    'start_date': datetime(2023, 11, 10),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(seconds=15)
}

dag = DAG(
    'final_project',
    default_args=default_args,
    description='final_project',
    schedule_interval=timedelta(days=1),
)

etl_task = PythonOperator(
    task_id='etl_task',
    python_callable=etl_process,
    dag=dag,
)

etl_task