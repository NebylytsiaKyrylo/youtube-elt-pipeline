ARG AIRFLOW_VERSION=3.2.0
ARG PYTHON_VERSION=3.12

FROM apache/airflow:${AIRFLOW_VERSION}-python${PYTHON_VERSION}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt