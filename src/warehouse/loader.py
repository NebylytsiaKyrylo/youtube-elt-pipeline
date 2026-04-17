import logging

import pandas as pd
from sqlalchemy import Engine, text

from src.youtube.client import EnrichedVideoDetails

logger = logging.getLogger(__name__)


def raw_to_dataframe(raw_data: list[EnrichedVideoDetails], run_id: str) -> pd.DataFrame:
    df = pd.DataFrame(raw_data)
    df["ingestion_ts"] = pd.Timestamp.now(tz="UTC")
    df["run_id"] = run_id
    return df


def load_staging_batch(df: pd.DataFrame, engine: Engine) -> int:
    """TRUNCATE staging.yt_video_snapshot then insert all rows. Returns row count."""

    with engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE staging.yt_video_snapshot"))
        conn.commit()

    df.to_sql(
        name="yt_video_snapshot",
        con=engine,
        schema="staging",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=500,
    )

    logger.info(f"Loaded {len(df)} rows into staging.yt_video_snapshot")

    return len(df)


def load_raw_to_staging(raw_data: list[EnrichedVideoDetails], run_id: str, engine: Engine) -> int:
    df = raw_to_dataframe(raw_data, run_id)
    return load_staging_batch(df, engine)
