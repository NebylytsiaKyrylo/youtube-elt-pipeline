from __future__ import annotations

from datetime import datetime, timedelta

from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task, TaskGroup, Variable, get_current_context

from storage.raw_storage import RawStorage
from warehouse.loader import load_raw_to_staging
from youtube.channels import CHANNELS
from youtube.extractor import extract_all_channels

SQL_BASE = "/opt/airflow/sql"
POSTGRES_CONN_ID = "postgres_elt"

MART_FILES = [
    "mart_channel_engagement_active",
    "mart_channel_size_distribution",
    "mart_channel_top_views",
    "mart_channel_top_subscribers",
    "mart_channel_top_likes_rate",
    "mart_channel_subscribers_vs_engagement",
    "mart_channel_latest_videos",
    "mart_channel_retention",
    "mart_video_top_views",
    "mart_video_format_engagement",
]

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email': 'knebylytsia.it@gmail.com',
    'email_on_failure': False,
    'email_on_retry': False,
    'execution_timeout': timedelta(minutes=10),
    'retry_exponential_backoff': True,
}


@dag(
    dag_id="yt_elt_pipeline",
    description="ELT pipeline — Tech & Data YouTube FR",
    schedule="0 14 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    dagrun_timeout=timedelta(minutes=30),
    template_searchpath=[SQL_BASE],
    tags=["youtube", "elt"],
)
def yt_elt_pipeline():
    def raw_storage() -> RawStorage:
        return RawStorage(
            endpoint_url=Variable.get("MINIO_ENDPOINT"),
            access_key=Variable.get("MINIO_ACCESS_KEY"),
            secret_key=Variable.get("MINIO_SECRET_KEY"),
            bucket=Variable.get("MINIO_BUCKET")
        )

    @task
    def extract_to_s3() -> str:
        api_key = Variable.get("YOUTUBE_API_KEY")
        context = get_current_context()
        snapshot_date = context["logical_date"].date()
        data = extract_all_channels(api_key, CHANNELS)
        writer = raw_storage()
        return writer.write(data, snapshot_date)

    @task
    def load_raw_staging(key: str) -> int:
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        engine = hook.get_sqlalchemy_engine()
        reader = raw_storage()
        data = reader.read(key)
        return load_raw_to_staging(data, engine)

    s3_key = extract_to_s3()

    setup_staging = SQLExecuteQueryOperator(
        task_id="setup_staging",
        conn_id=POSTGRES_CONN_ID,
        sql="staging/ddl_staging.sql",
    )

    load_staging = load_raw_staging(s3_key)

    setup_core = SQLExecuteQueryOperator(
        task_id="setup_core",
        conn_id=POSTGRES_CONN_ID,
        sql="core/ddl_core.sql",
    )

    transform_core = SQLExecuteQueryOperator(
        task_id="transform_core",
        conn_id=POSTGRES_CONN_ID,
        sql="core/dml_core.sql",
    )

    setup_marts = SQLExecuteQueryOperator(
        task_id="setup_marts",
        conn_id=POSTGRES_CONN_ID,
        sql="marts/ddl_schema_marts.sql",
    )

    with TaskGroup("marts") as marts_group:
        for name in MART_FILES:
            SQLExecuteQueryOperator(
                task_id=f"build_{name}",
                conn_id=POSTGRES_CONN_ID,
                sql=f"marts/{name}.sql",
            )

    s3_key >> setup_staging >> load_staging >> setup_core >> transform_core >> setup_marts >> marts_group


dag = yt_elt_pipeline()
