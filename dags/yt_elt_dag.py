from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.smtp.notifications.smtp import SmtpNotifier
from airflow.sdk import TaskGroup, Variable, dag, get_current_context, task

from soda_utils.soda_checks import soda_scanner
from storage.raw_storage import RawStorage
from warehouse.loader import load_raw_to_staging
from youtube.channels import CHANNELS
from youtube.extractor import extract_all_channels

SQL_BASE = "/opt/airflow/sql"
POSTGRES_CONN_ID = "postgres_elt"
SODA_BASE = "/opt/airflow/soda"
TEMPLATES_BASE = Path("/opt/airflow/templates")

_smtp_on_failure = SmtpNotifier(
    smtp_conn_id="smtp_default",
    from_email="knebylytsia.it@gmail.com",
    to="knebylytsia.it@gmail.com",
    subject="[Airflow] Failure — {{ dag.dag_id }} | {{ ds }}",
    html_content=(TEMPLATES_BASE / "email_failure.html").read_text(),
)

_smtp_on_success = SmtpNotifier(
    smtp_conn_id="smtp_default",
    from_email="knebylytsia.it@gmail.com",
    to="knebylytsia.it@gmail.com",
    subject="[Airflow] Success  — {{ dag.dag_id }} | {{ ds }}",
    html_content=(TEMPLATES_BASE / "email_success.html").read_text(),
)

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
    "owner": "data_engineer",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=10),
    "retry_exponential_backoff": True,
    "on_failure_callback": [_smtp_on_failure],
}


@dag(
    dag_id="yt_elt_pipeline",
    description="ELT pipeline — Tech & Data YouTube FR",
    schedule="0 14 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    dagrun_timeout=timedelta(minutes=45),
    template_searchpath=[SQL_BASE],
    tags=["youtube", "elt"],
    on_success_callback=[_smtp_on_success],
)
def yt_elt_pipeline() -> None:
    def raw_storage() -> RawStorage:
        return RawStorage(
            endpoint_url=Variable.get("MINIO_ENDPOINT"),
            access_key=Variable.get("MINIO_ACCESS_KEY"),
            secret_key=Variable.get("MINIO_SECRET_KEY"),
            bucket=Variable.get("MINIO_BUCKET"),
        )

    @task(execution_timeout=timedelta(minutes=20))
    def extract_to_s3() -> str:
        api_key = Variable.get("YOUTUBE_API_KEY")
        context = get_current_context()
        snapshot_date = context["logical_date"].date()
        data = extract_all_channels(api_key, CHANNELS)
        writer = raw_storage()
        return writer.write(data, snapshot_date)

    @task()
    def load_raw_staging(key: str) -> int:
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        engine = hook.get_sqlalchemy_engine()
        reader = raw_storage()
        data = reader.read(key)
        return load_raw_to_staging(data, engine)

    setup_staging = SQLExecuteQueryOperator(
        task_id="setup_staging",
        conn_id=POSTGRES_CONN_ID,
        sql="staging/ddl_staging.sql",
    )

    @task
    def quality_check_staging() -> None:
        context = get_current_context()
        ds = str(context["logical_date"].date())
        soda_scanner(
            data_source_name="yt_dwh",
            configuration_yaml_file_path=f"{SODA_BASE}/configuration.yml",
            sodacl_yaml_file=f"{SODA_BASE}/checks_staging.yml",
            variables={"ds": ds},
        )

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

    @task
    def quality_check_core() -> None:
        context = get_current_context()
        ds = str(context["logical_date"].date())
        soda_scanner(
            data_source_name="yt_dwh",
            configuration_yaml_file_path=f"{SODA_BASE}/configuration.yml",
            sodacl_yaml_file=f"{SODA_BASE}/checks_core.yml",
            variables={"ds": ds},
        )

    soft_delete_core = SQLExecuteQueryOperator(
        task_id="soft_delete_core",
        conn_id=POSTGRES_CONN_ID,
        sql="core/dml_soft_delete.sql",
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

    @task
    def quality_check_marts() -> None:
        soda_scanner(
            data_source_name="yt_dwh",
            configuration_yaml_file_path=f"{SODA_BASE}/configuration.yml",
            sodacl_yaml_file=f"{SODA_BASE}/checks_marts.yml",
        )

    s3_key = extract_to_s3()
    load_staging = load_raw_staging(s3_key)
    qc_staging = quality_check_staging()
    qc_core = quality_check_core()
    qc_marts = quality_check_marts()

    # Pipeline ELT
    s3_key >> setup_staging >> load_staging >> qc_staging
    qc_staging >> setup_core >> transform_core >> qc_core >> soft_delete_core
    soft_delete_core >> setup_marts >> marts_group >> qc_marts


dag = yt_elt_pipeline()
