import logging

import pandas as pd
from sqlalchemy import Engine, text


logger = logging.getLogger(__name__)


def load_staging_batch(df: pd.DataFrame, engine: Engine) -> int:
    """TRUNCATE staging.yt_video_snapshot then insert all rows atomically. Returns row count."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE staging.yt_video_snapshot"))
        df.to_sql(
            name="yt_video_snapshot",
            con=conn,
            schema="staging",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=500,
        )

    logger.info(f"Loaded {len(df)} rows into staging.yt_video_snapshot")
    return len(df)


def load_raw_to_staging(raw_data: list[dict], engine: Engine) -> int:
    df = pd.DataFrame(raw_data)
    return load_staging_batch(df, engine)
