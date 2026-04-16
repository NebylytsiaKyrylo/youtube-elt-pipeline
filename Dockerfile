ARG AIRFLOW_VERSION=3.2.0
ARG PYTHON_VERSION=3.12

FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

RUN pip install --no-cache-dir \
    requests \
    urllib3 \
    pandas \
    psycopg2-binary \
    sqlalchemy \
    boto3 \
    soda-core-postgres