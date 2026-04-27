"""
Unit tests for the channel and video extraction functions.

This module provides test cases for the `extract_channel` and `extract_all_channels`
functions. Each test case assesses the behavior of these functions under various
scenarios, including successful responses, empty results, and exception handling.

Classes:
- TestExtractChannel: Contains test cases for `extract_channel` function.
- TestExtractAllChannels: Contains test cases for `extract_all_channels` function.

uv run pytest tests/unit/test_extractor.py -v
uv run pytest tests/unit/test_extractor.py -v --cov=youtube.extractor --cov-report=term-missing
coverage: 100%
"""

from unittest.mock import MagicMock, patch

import pytest

from youtube.extractor import extract_channel, extract_all_channels


class TestExtractChannel:
    def test_success_enriches_videos_with_channel_info(self):
        mock_client = MagicMock()
        mock_client.get_channel_info.return_value = {
            "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
            "channel_name": "Google for Developers",
            "channel_start_date": "2007-08-23T00:34:43Z",
            "uploads_playlist_id": "UU_x5XG1OV2P6uZZ5FSM9Ttw",
            "subscribers_count": "2620000"
        }
        mock_client.get_video_ids.return_value = ["qznOtwiGudo", "TuHY331TGh4", "WYPdz3OZfuQ"]
        mock_client.get_videos_details.return_value = [
            {
                "video_id": "qznOtwiGudo",
                "title": "Give your Gemini Live Agent a phone number!",
                "published_at": "2026-04-24T16:01:35Z",
                "duration_iso": "PT48S",
                "view_count": "8089",
                "like_count": "166",
                "comment_count": "5"
            },
            {
                "video_id": "TuHY331TGh4",
                "title": "How to use Gemini in your app",
                "published_at": "2026-04-24T04:00:23Z",
                "duration_iso": "PT48S",
                "view_count": "1234",
                "like_count": "123",
                "comment_count": "12"
            },
            {
                "video_id": "WYPdz3OZfuQ",
                "title": "How to use Claude in your app",
                "published_at": "2026-04-24T04:00:23Z",
                "duration_iso": "PT50S",
                "view_count": "12340",
                "like_count": "1222",
                "comment_count": "120"
            }]

        result = extract_channel(client=mock_client, channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw")

        assert len(result) == 3

        assert result == [
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
                "subscribers_count": "2620000"
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
                "subscribers_count": "2620000"
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
                "subscribers_count": "2620000"
            }
        ]

    def test_no_video_ids_returns_empty_list(self):
        mock_client = MagicMock()
        mock_client.get_channel_info.return_value = {
            "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
            "channel_name": "Google for Developers",
            "channel_start_date": "2007-08-23T00:34:43Z",
            "uploads_playlist_id": "UU_x5XG1OV2P6uZZ5FSM9Ttw",
            "subscribers_count": "2620000"
        }
        mock_client.get_video_ids.return_value = []

        result = extract_channel(client=mock_client, channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw")

        assert result == []

    def test_value_error_returns_empty_list(self):
        mock_client = MagicMock()
        mock_client.get_channel_info.side_effect = ValueError("Channel not found")

        result = extract_channel(client=mock_client, channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw")

        assert result == []

    def test_unexpected_exception_returns_empty_list(self):
        mock_client = MagicMock()
        mock_client.get_channel_info.side_effect = ConnectionError("Network failure")

        result = extract_channel(client=mock_client, channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw")

        assert result == []


class TestExtractAllChannels:
    def test_success_returns_all_videos(self):
        channels = [{"channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw", "channel_name": "Google for Developers"},
                    {"channel_id": "UC_x5XG1OV346uZZ5FSM9T-tw", "channel_name": "Claude for Developers"}]

        with patch("youtube.extractor.YouTubeClient") as MockClient:
            instance = MockClient("fake_api")
            instance.get_channel_info.side_effect = [
                {
                    "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                    "channel_name": "Google for Developers",
                    "channel_start_date": "2007-08-23T00:34:43Z",
                    "uploads_playlist_id": "UU_x5XG1OV2P6uZZ5FSM9Ttw",
                    "subscribers_count": "2620000"
                },
                {
                    "channel_id": "UC_x5XG1OV346uZZ5FSM9T-tw",
                    "channel_name": "Claude for Developers",
                    "channel_start_date": "2019-08-23T00:34:43Z",
                    "uploads_playlist_id": "UU_x5XG1OV346uZZ5FSM9Ttw",
                    "subscribers_count": "12620000"
                }

            ]
            instance.get_video_ids.side_effect = [["qznOtwiGudo", "TuHY331TGh4", "WYPdz3OZfuQ"], ["qznOtwiGudo0"]]
            instance.get_videos_details.side_effect = [[
                {
                    "video_id": "qznOtwiGudo",
                    "title": "Give your Gemini Live Agent a phone number!",
                    "published_at": "2026-04-24T16:01:35Z",
                    "duration_iso": "PT48S",
                    "view_count": "8089",
                    "like_count": "166",
                    "comment_count": "5"
                },
                {
                    "video_id": "TuHY331TGh4",
                    "title": "How to use Gemini in your app",
                    "published_at": "2026-04-24T04:00:23Z",
                    "duration_iso": "PT48S",
                    "view_count": "1234",
                    "like_count": "123",
                    "comment_count": "12"
                },
                {
                    "video_id": "WYPdz3OZfuQ",
                    "title": "How to use Claude in your app",
                    "published_at": "2026-04-24T04:00:23Z",
                    "duration_iso": "PT50S",
                    "view_count": "12340",
                    "like_count": "1222",
                    "comment_count": "120"
                }],
                [{
                    "video_id": "qznOtwiGudo0",
                    "title": "Give your Claude Agent a phone number!",
                    "published_at": "2026-04-25T16:01:35Z",
                    "duration_iso": "PT55S",
                    "view_count": "80890",
                    "like_count": "1662",
                    "comment_count": "50"
                }]]

            result = extract_all_channels(api_key="fake_key", channels_ids=channels)

        assert len(result) == 4

        assert result == [
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
                "subscribers_count": "2620000"
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
                "subscribers_count": "2620000"
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
                "subscribers_count": "2620000"
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
                "subscribers_count": "12620000"
            }
        ]

    def test_raises_runtime_error_if_all_channels_empty(self):
        channels = [{"channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw", "channel_name": "Google for Developers"},
                    {"channel_id": "UC_x5XG1OV346uZZ5FSM9T-tw", "channel_name": "Claude for Developers"}]

        with patch("youtube.extractor.YouTubeClient") as MockClient:
            MockClient.return_value.get_channel_info.side_effect = ValueError("Not found")
            with pytest.raises(RuntimeError):
                extract_all_channels(api_key="fake_key", channels_ids=channels)
