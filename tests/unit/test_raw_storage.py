"""
This module contains unit tests for the RawStorage class.

uv run pytest tests/unit/test_raw_storage.py -v
uv run pytest tests/unit/test_raw_storage.py -v --cov=storage.raw_storage --cov-report=term-missing
coverage: 100%
"""

from datetime import date
import json
from unittest.mock import MagicMock

from botocore.exceptions import ClientError
import pytest

from storage.raw_storage import RawStorage

FAKE_VIDEOS = [
    {
        "video_id": "qznOtwiGudo",
        "title": "Give your Gemini Live Agent a phone number!",
        "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
        "channel_name": "Google for Developers",
    }
]


def make_storage() -> RawStorage:
    storage = RawStorage(
        endpoint_url="http://fake-minio:9000",
        access_key="fake_access",
        secret_key="fake_secret",
        bucket="youtube-raw",
    )
    storage.s3 = MagicMock()
    return storage


class TestWrite:
    def test_success_returns_correct_key(self):
        storage = make_storage()

        result = storage.write(videos=FAKE_VIDEOS, ds=date(2026, 4, 16))

        assert result == "youtube_data_2026-04-16.json"

    def test_put_object_called_with_correct_args(self):
        storage = make_storage()

        storage.write(videos=FAKE_VIDEOS, ds=date(2026, 4, 16))

        storage.s3.put_object.assert_called_once_with(
            Bucket="youtube-raw",
            Key="youtube_data_2026-04-16.json",
            Body=json.dumps(FAKE_VIDEOS, ensure_ascii=False, indent=2).encode("utf-8"),
            ContentType="application/json",
        )


class TestRead:
    def test_success_returns_list_of_dicts(self):
        storage = make_storage()
        fake_body = MagicMock()
        fake_body.read.return_value = json.dumps(FAKE_VIDEOS).encode("utf-8")
        storage.s3.get_object.return_value = {"Body": fake_body}

        result = storage.read("youtube_data_2026-04-16.json")

        assert result == FAKE_VIDEOS

    def test_no_such_key_raises_file_not_found(self):
        storage = make_storage()
        storage.s3.get_object.side_effect = ClientError(
            error_response={"Error": {"Code": "NoSuchKey", "Message": "The key does not exist"}},
            operation_name="GetObject",
        )

        with pytest.raises(FileNotFoundError):
            storage.read("youtube_data_2026-04-16.json")

    def test_other_client_error_reraises(self):
        storage = make_storage()
        storage.s3.get_object.side_effect = ClientError(
            error_response={"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            operation_name="GetObject",
        )

        with pytest.raises(ClientError):
            storage.read("youtube_data_2026-04-16.json")
