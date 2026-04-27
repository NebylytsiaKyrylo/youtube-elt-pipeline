"""
This script contains mock data and configurations for testing YouTube Client functionalities.

The module includes predefined constants such as fake responses
for channel details, video details, playlist pages, and other mock data
to simulate YouTube API responses. It is used for testing purposes
with tools like pytest and unittest.mock.

uv run pytest tests/unit/test_client.py -v
uv run pytest tests/unit/test_client.py -v --cov=youtube.client --cov-report=term-missing
coverage: 100%
"""

from unittest.mock import MagicMock, patch

import pytest

from youtube.client import YouTubeClient

FAKE_CHANNEL_RESPONSE = {
    "kind": "youtube#channelListResponse",
    "etag": "d2Jb-YP7fFFUv4Y9W4KOS-lVbbY",
    "pageInfo": {"totalResults": 1, "resultsPerPage": 5},
    "items": [
        {
            "kind": "youtube#channel",
            "etag": "0N0jLzBkplero0RdSN00fLIq2a4",
            "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
            "snippet": {
                "title": "Google for Developers",
                "description": "Subscribe to join a community of creative developers and learn the latest in Google technology — from AI and cloud, to mobile and web.\n\nExplore more at developers.google.com\n\n",
                "customUrl": "@googledevelopers",
                "publishedAt": "2007-08-23T00:34:43Z",
                "thumbnails": {
                    "default": {
                        "url": "https://yt3.ggpht.com/WZ_63J_-745xyW_DGxGi3VUyTZAe0Jvhw2ZCg7fdz-tv9esTbNPZTFR9X79QzA0ArIrMjYJCDA=s88-c-k-c0x00ffffff-no-rj",
                        "width": 88,
                        "height": 88,
                    },
                    "medium": {
                        "url": "https://yt3.ggpht.com/WZ_63J_-745xyW_DGxGi3VUyTZAe0Jvhw2ZCg7fdz-tv9esTbNPZTFR9X79QzA0ArIrMjYJCDA=s240-c-k-c0x00ffffff-no-rj",
                        "width": 240,
                        "height": 240,
                    },
                    "high": {
                        "url": "https://yt3.ggpht.com/WZ_63J_-745xyW_DGxGi3VUyTZAe0Jvhw2ZCg7fdz-tv9esTbNPZTFR9X79QzA0ArIrMjYJCDA=s800-c-k-c0x00ffffff-no-rj",
                        "width": 800,
                        "height": 800,
                    },
                },
                "localized": {
                    "title": "Google for Developers",
                    "description": "Subscribe to join a community of creative developers and learn the latest in Google technology — from AI and cloud, to mobile and web.\n\nExplore more at developers.google.com\n\n",
                },
                "country": "US",
            },
            "contentDetails": {"relatedPlaylists": {"likes": "", "uploads": "UU_x5XG1OV2P6uZZ5FSM9Ttw"}},
            "statistics": {
                "viewCount": "333709074",
                "subscriberCount": "2620000",
                "hiddenSubscriberCount": "false",
                "videoCount": "6398",
            },
        }
    ],
}

FAKE_PLAYLIST_PAGE_1 = {
    "kind": "youtube#playlistItemListResponse",
    "etag": "v-DP2CIX0_ct0PO8H6_4TGET-Rc",
    "nextPageToken": "EAAaHlBUOkNESWlFREV6TmpCR01UY3hSakl6UTBNMk56Yw",
    "items": [
        {
            "kind": "youtube#playlistItem",
            "etag": "XXHQzOA3c75BztVoEFMRBUSd208",
            "id": "VVVfeDVYRzFPVjJQNnVaWjVGU005VHR3LnF6bk90d2lHdWRv",
            "contentDetails": {"videoId": "qznOtiGudoo", "videoPublishedAt": "2026-04-24T16:01:35Z"},
        },
        {
            "kind": "youtube#playlistItem",
            "etag": "ZVk2WJD0H2Pf664tCx45vbboa9A",
            "id": "VVVfeDVYRzFPVjJQNnVaWjVGU005VHR3LlR1SFkzMzFUR2g0",
            "contentDetails": {"videoId": "TuY331TGh44", "videoPublishedAt": "2026-04-24T04:00:23Z"},
        },
        {
            "kind": "youtube#playlistItem",
            "etag": "MlbigB20u0_r3Nnt-aKNnu04z8M",
            "id": "VVVfeDVYRzFPVjJQNnVaWjVGU005VHR3LldZUGR6M09aZnVR",
            "contentDetails": {"videoId": "WYPdzOZfuQQ", "videoPublishedAt": "2026-04-23T19:00:52Z"},
        },
    ],
    "pageInfo": {"totalResults": 6398, "resultsPerPage": 3},
}

FAKE_PLAYLIST_PAGE_2 = {
    "kind": "youtube#playlistItemListResponse",
    "etag": "v-DP2CIX0_ct0PO8H6_4TGET-Rc",
    "items": [
        {
            "kind": "youtube#playlistItem",
            "etag": "XXHQzOA3c75BztVoEFMRBUSd208",
            "id": "VVVfeDVYRzFPVjJQNnVaWjVGU005VHR3LnF6bk90d2lHdWRv",
            "contentDetails": {"videoId": "qznOtwiGudo", "videoPublishedAt": "2026-04-24T16:01:35Z"},
        },
        {
            "kind": "youtube#playlistItem",
            "etag": "ZVk2WJD0H2Pf664tCx45vbboa9A",
            "id": "VVVfeDVYRzFPVjJQNnVaWjVGU005VHR3LlR1SFkzMzFUR2g0",
            "contentDetails": {"videoId": "TuHY331TGh4", "videoPublishedAt": "2026-04-24T04:00:23Z"},
        },
        {
            "kind": "youtube#playlistItem",
            "etag": "MlbigB20u0_r3Nnt-aKNnu04z8M",
            "id": "VVVfeDVYRzFPVjJQNnVaWjVGU005VHR3LldZUGR6M09aZnVR",
            "contentDetails": {"videoId": "WYPdz3OZfuQ", "videoPublishedAt": "2026-04-23T19:00:52Z"},
        },
    ],
    "pageInfo": {"totalResults": 3, "resultsPerPage": 3},
}

FAKE_VIDEO_RESPONSE = {
    "kind": "youtube#videoListResponse",
    "etag": "0kika6uw972zG0pegV8GMuz38AU",
    "items": [
        {
            "kind": "youtube#video",
            "etag": "yJfoyoUSapMaaViCzehpAMOLHXs",
            "id": "qznOtwiGudo",
            "snippet": {
                "publishedAt": "2026-04-24T16:01:35Z",
                "channelId": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                "title": "Give your Gemini Live Agent a phone number!",
                "description": "Learn how you can call your AI assistant with the power of Gemini, Google Cloud, and Twilio. \n\nSubscribe to Google for Developers → https://goo.gle/developers \n\nProducts Mentioned: Gemini \nSpeakers: Thor Schaeff",
                "thumbnails": {
                    "default": {"url": "https://i.ytimg.com/vi/qznOtwiGudo/default.jpg", "width": 120, "height": 90},
                    "medium": {"url": "https://i.ytimg.com/vi/qznOtwiGudo/mqdefault.jpg", "width": 320, "height": 180},
                    "high": {"url": "https://i.ytimg.com/vi/qznOtwiGudo/hqdefault.jpg", "width": 480, "height": 360},
                    "standard": {
                        "url": "https://i.ytimg.com/vi/qznOtwiGudo/sddefault.jpg",
                        "width": 640,
                        "height": 480,
                    },
                    "maxres": {
                        "url": "https://i.ytimg.com/vi/qznOtwiGudo/maxresdefault.jpg",
                        "width": 1280,
                        "height": 720,
                    },
                },
                "channelTitle": "Google for Developers",
                "tags": [
                    "Google",
                    "developers",
                    "pr_pr: AI DevRel (fka Core ML);",
                    "Purpose: Learn;",
                    "Campaign:;",
                    "Video Type:G4D SV: Educational ;",
                    "ct: AIG;",
                    "gds:N/A;",
                ],
                "categoryId": "28",
                "liveBroadcastContent": "none",
                "defaultLanguage": "en",
                "localized": {
                    "title": "Give your Gemini Live Agent a phone number!",
                    "description": "Learn how you can call your AI assistant with the power of Gemini, Google Cloud, and Twilio. \n\nSubscribe to Google for Developers → https://goo.gle/developers \n\nProducts Mentioned: Gemini \nSpeakers: Thor Schaeff",
                },
                "defaultAudioLanguage": "en",
            },
            "contentDetails": {
                "duration": "PT48S",
                "dimension": "2d",
                "definition": "hd",
                "caption": "false",
                "licensedContent": "false",
                "contentRating": {},
                "projection": "rectangular",
            },
            "statistics": {"viewCount": "8089", "likeCount": "166", "favoriteCount": "0", "commentCount": "5"},
        }
    ],
    "pageInfo": {"totalResults": 1, "resultsPerPage": 1},
}


class TestGetChannelInfo:
    def test_success(self):
        # Arrange
        fake_response = MagicMock()
        fake_response.json.return_value = FAKE_CHANNEL_RESPONSE
        client = YouTubeClient(api_key="fake_key")

        # Act
        with patch.object(client.session, "get", return_value=fake_response):
            result = client.get_channel_info("UC_x5XG1OV2P6uZZ5FSM9Ttw")

        # Assert
        assert result == {
            "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
            "channel_name": "Google for Developers",
            "channel_start_date": "2007-08-23T00:34:43Z",
            "uploads_playlist_id": "UU_x5XG1OV2P6uZZ5FSM9Ttw",
            "subscribers_count": "2620000",
        }

    def test_channel_not_found_raises_value_error(self):
        # Arrange
        fake_response = MagicMock()
        fake_response.json.return_value = {"items": []}
        client = YouTubeClient(api_key="fake_key")

        # Act + Assert
        with (
            patch.object(client.session, "get", return_value=fake_response),
            pytest.raises(ValueError, match="Channel not found"),
        ):
            client.get_channel_info("UC_fake_id")


class TestGetVideosIds:
    def test_single_page_without_next_page_token(self):
        fake_response = MagicMock()
        fake_response.json.return_value = FAKE_PLAYLIST_PAGE_2
        client = YouTubeClient(api_key="fake_key")

        with patch.object(client.session, "get", return_value=fake_response):
            result = client.get_video_ids("UU_x5XG1OV2P6uZZ5FSM9Ttw")

        assert result == ["qznOtwiGudo", "TuHY331TGh4", "WYPdz3OZfuQ"]

    def test_two_pages_with_next_page_token(self):
        fake_page_1 = MagicMock()
        fake_page_1.json.return_value = FAKE_PLAYLIST_PAGE_1

        fake_page_2 = MagicMock()
        fake_page_2.json.return_value = FAKE_PLAYLIST_PAGE_2

        client = YouTubeClient(api_key="fake_key")

        with patch.object(client.session, "get", side_effect=[fake_page_1, fake_page_2]):
            result = client.get_video_ids("UU_x5XG1OV2P6uZZ5FSM9Ttw")

        assert result == ["qznOtiGudoo", "TuY331TGh44", "WYPdzOZfuQQ", "qznOtwiGudo", "TuHY331TGh4", "WYPdz3OZfuQ"]


class TestGetVideosDetails:
    def test_batching_75_ids_makes_2_api_calls(self):
        fake_response = MagicMock()
        fake_response.json.return_value = {"items": []}

        client = YouTubeClient(api_key="fake_key")
        video_ids = [f"vid{i:03d}" for i in range(75)]

        with patch.object(client.session, "get", return_value=fake_response) as mock_get:
            client.get_videos_details(video_ids)

        assert mock_get.call_count == 2

    def test_returns_correctly_structured_video_dicts(self):
        fake_response = MagicMock()
        fake_response.json.return_value = FAKE_VIDEO_RESPONSE
        client = YouTubeClient(api_key="fake_key")

        with patch.object(client.session, "get", return_value=fake_response):
            result = client.get_videos_details(["qznOtwiGudo"])

        assert result == [
            {
                "video_id": "qznOtwiGudo",
                "title": "Give your Gemini Live Agent a phone number!",
                "published_at": "2026-04-24T16:01:35Z",
                "duration_iso": "PT48S",
                "view_count": "8089",
                "like_count": "166",
                "comment_count": "5",
            }
        ]


class TestBatch:
    def test_splits_into_correct_chunks(self):
        ids = ["a", "b", "c", "d", "e"]
        result = list(YouTubeClient._batch(lst=ids, size=2))
        assert result == [["a", "b"], ["c", "d"], ["e"]]

    def test_empty_list_returns_empty(self):
        ids = []
        result = list(YouTubeClient._batch(lst=ids, size=2))
        assert result == []

    def test_size_larger_than_list_returns_single_batch(self):
        ids = ["a", "b", "c", "d", "e"]
        result = list(YouTubeClient._batch(lst=ids, size=20))
        assert result == [["a", "b", "c", "d", "e"]]
