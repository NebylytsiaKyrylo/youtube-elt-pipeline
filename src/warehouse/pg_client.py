# This file contains the logic for connecting to the database

from sqlalchemy import Engine, create_engine


def build_conn_string(db_user: str, db_password: str, db_host: str, db_port: int, db_name) -> str:
    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_engine(url: str) -> Engine:
    # Lazy connection
    return create_engine(url)
