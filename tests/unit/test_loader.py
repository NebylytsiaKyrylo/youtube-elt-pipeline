"""
Unit tests for warehouse loader functions.

uv run pytest tests/unit/test_loader.py -v
uv run pytest tests/unit/test_loader.py -v --cov=warehouse.loader --cov-report=term-missing
"""

from unittest.mock import MagicMock

import pandas as pd

from warehouse.loader import load_raw_to_staging, load_staging_batch

FAKE_VIDEOS = [
    {
        "video_id": "qznOtwiGudo",
        "title": "Give your Gemini Live Agent a phone number!",
        "published_at": "2026-04-24T16:01:35Z",
        "duration_iso": "PT48S",
        "view_count": "8089",
        "like_count": "166",
        "comment_count": "5",
        "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "channel_name": "Google for Developers",
        "channel_start_date": "2007-08-23T00:34:43Z",
        "subscribers_count": "2620000",
    },
    {
        "video_id": "TuHY331TGh4",
        "title": "How to use Gemini in your app",
        "published_at": "2026-04-24T04:00:23Z",
        "duration_iso": "PT48S",
        "view_count": "1234",
        "like_count": "123",
        "comment_count": "12",
        "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "channel_name": "Google for Developers",
        "channel_start_date": "2007-08-23T00:34:43Z",
        "subscribers_count": "2620000",
    },
    {
        "video_id": "WYPdz3OZfuQ",
        "title": "How to use Claude in your app",
        "published_at": "2026-04-24T04:00:23Z",
        "duration_iso": "PT50S",
        "view_count": "12340",
        "like_count": "1222",
        "comment_count": "120",
        "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "channel_name": "Google for Developers",
        "channel_start_date": "2007-08-23T00:34:43Z",
        "subscribers_count": "2620000",
    },
    {
        "video_id": "qznOtwiGudo0",
        "title": "Give your Claude Agent a phone number!",
        "published_at": "2026-04-25T16:01:35Z",
        "duration_iso": "PT55S",
        "view_count": "80890",
        "like_count": "1662",
        "comment_count": "50",
        "channel_id": "UC_x5XG1OV346uZZ5FSM9T-tw",
        "channel_name": "Claude for Developers",
        "channel_start_date": "2019-08-23T00:34:43Z",
        "subscribers_count": "12620000",
    },
]


def make_engine():
    engine = MagicMock()
    conn = engine.begin().__enter__()
    return engine, conn


class TestLoadStagingBatch:
    def test_returns_row_count(self):
        engine, _conn = make_engine()
        df = pd.DataFrame(FAKE_VIDEOS)

        result = load_staging_batch(df=df, engine=engine)

        assert result == 4

    def test_truncate_is_called(self):
        engine, conn = make_engine()
        df = pd.DataFrame(FAKE_VIDEOS)

        load_staging_batch(df=df, engine=engine)

        conn.execute.assert_called_once()
        actual_arg = conn.execute.call_args[0][0]
        assert str(actual_arg) == "TRUNCATE TABLE staging.yt_video_snapshot"

    def test_to_sql_called_with_correct_args(self):
        df_mock = MagicMock(spec=pd.DataFrame)
        df_mock.__len__ = MagicMock(return_value=4)
        engine, conn = make_engine()

        load_staging_batch(df=df_mock, engine=engine)

        df_mock.to_sql.assert_called_once_with(
            name="yt_video_snapshot",
            con=conn,
            schema="staging",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=500,
        )


class TestLoadRawToStaging:
    def test_converts_dicts_to_dataframe_and_loads(self):
        engine, _conn = make_engine()

        result = load_raw_to_staging(raw_data=FAKE_VIDEOS, engine=engine)

        assert result == 4
