"""YouTube API client with retry logic and session management."""

import logging
from typing import Generator, TypedDict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

BASE_URL: str = "https://www.googleapis.com/youtube/v3"
TIMEOUT: int = 30  # seconds
MAX_RESULTS: int = 50


class VideoDetails(TypedDict):
    """Details of a single YouTube video as returned by the API."""
    video_id: str
    title: str
    published_at: str
    duration_iso: str
    view_count: str | None
    like_count: str | None
    comment_count: str | None


class EnrichedVideoDetails(VideoDetails):
    """Video details enriched with channel metadata."""
    channel_id: str
    channel_name: str
    subscribers_count: str
    channel_start_date: str


class ChannelInfo(TypedDict):
    """Channel metadata returned by the YouTube channels endpoint."""
    channel_id: str
    channel_name: str
    channel_start_date: str  # ISO 8601 datetime
    uploads_playlist_id: str
    subscribers_count: str


class YouTubeClient:
    """
    Client for interacting with the YouTube Data API v3.

    This class provides methods for retrieving information about YouTube channels,
    playlists, and videos using the YouTube Data API v3. It is designed to handle
    retries for transient errors, such as network issues or rate limits, and provides
    structured logging for its operations.
    """

    def __init__(self, api_key: str):
        """Initialize the YouTube client with a session and retry strategy.

        Args:
            api_key: YouTube Data v3 API key
        """
        self.api_key = api_key
        self.session = requests.Session()

        # Retry strategy: 3 retries with exponential backoff
        # Retry on: rate limit (429), server errors (500, 502, 503, 504)
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s, 2s, 4s delays
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

    def get_channel_info(self, channel_id: str) -> ChannelInfo:
        """Fetch channel info (ID, name, creation date, upload playlist).

        Args:
            channel_id: Channel id (e.g., "UC7BNBNLwMF8GjgXLDP8PWQw")

        Returns:
            Dict with keys: channel_id, channel_name, channel_start_date,
            uploads_playlist_id

        Raises:
            ValueError: If a channel is not found

        Notes:
            API reference: https://developers.google.com/youtube/v3/docs/channels/list
        """

        url = f"{BASE_URL}/channels"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": channel_id,
            "key": self.api_key,
        }

        response = self.session.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        if not items:
            raise ValueError(f"Channel not found with id: {channel_id}")

        item = items[0]
        channel_name = item["snippet"]["title"]
        channel_start_date = item["snippet"]["publishedAt"]
        uploads_playlist_id = item["contentDetails"]["relatedPlaylists"]["uploads"]
        subscribers_count = item["statistics"]["subscriberCount"]

        logger.info(f"Channel found: {channel_name} ({channel_id})")

        return {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "channel_start_date": channel_start_date,
            "uploads_playlist_id": uploads_playlist_id,
            "subscribers_count": subscribers_count
        }

    def get_video_ids(self, playlist_id: str) -> list[str]:
        """Fetch all video IDs from a playlist (handles pagination).

        Args:
            playlist_id: YouTube playlist ID (e.g., "UUNpZ...")

        Returns:
            List of video IDs

        Notes:
            API reference: https://developers.google.com/youtube/v3/docs/playlistItems/list
        """
        url = f"{BASE_URL}/playlistItems"
        video_ids = []
        next_page_token = None

        while True:
            params = {
                "part": "contentDetails",
                "maxResults": MAX_RESULTS,
                "playlistId": playlist_id,
                "key": self.api_key,
            }
            if next_page_token:
                params["pageToken"] = next_page_token

            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            for item in items:
                video_id = item["contentDetails"]["videoId"]
                video_ids.append(video_id)

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        logger.info(f"Found {len(video_ids)} video IDs in playlist {playlist_id}")
        return video_ids

    def get_videos_details(self, video_ids: list[str]) -> list[VideoDetails]:
        """Fetch details for videos (views, likes, comments, duration).

        YouTube API allows max 50 IDs per request, so batch into chunks.

        Args:
            video_ids: List of video IDs

        Returns:
            List of dicts with video metadata

        Notes:
            API reference: https://developers.google.com/youtube/v3/docs/videos/list
        """
        url = f"{BASE_URL}/videos"
        videos = []

        for batch in self._batch(video_ids, MAX_RESULTS):
            ids_str = ",".join(batch)
            params = {
                "part": "snippet,contentDetails,statistics",
                "id": ids_str,
                "key": self.api_key,
            }

            response = self.session.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            for item in items:
                video = {
                    "video_id": item["id"],
                    "title": item["snippet"]["title"],
                    "published_at": item["snippet"]["publishedAt"],
                    "duration_iso": item["contentDetails"]["duration"],
                    "view_count": item["statistics"].get("viewCount"),
                    "like_count": item["statistics"].get("likeCount"),
                    "comment_count": item["statistics"].get("commentCount"),
                }
                videos.append(video)

        logger.info(f"Fetched details for {len(videos)} videos")
        return videos

    @staticmethod
    def _batch(lst: list[str], size: int) -> Generator[list[str], None, None]:
        """Yield successive chunks of size from list.

        Args:
            lst: List to batch
            size: Batch size

        Yields:
            Lists of size `size` (last batch may be smaller)
        """
        for i in range(0, len(lst), size):
            yield lst[i: i + size]
