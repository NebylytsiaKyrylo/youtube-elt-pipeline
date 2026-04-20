"""Orchestration of YouTube data extraction across multiple channels."""

import logging

from src.youtube.client import YouTubeClient, EnrichedVideoDetails

logger = logging.getLogger(__name__)


def extract_channel(client: YouTubeClient, channel_id: str) -> list[EnrichedVideoDetails]:
    """Extract all videos and metadata for a single channel.

    Orchestrates: channel info → playlist → video IDs → video details.

    Args:
        client: YouTubeClient instance
        channel_id: Channel id (e.g., "UC7BNBNLwMF8GjgXLDP8PWQw")

    Returns:
        List of video dicts enriched with channel metadata.
        Returns empty list if channel fails (non-blocking).
    """
    try:
        # Step 1: Fetch channel metadata
        channel_info = client.get_channel_info(channel_id)

        # Step 2: Fetch video IDs from uploads playlist
        playlist_id = channel_info["uploads_playlist_id"]
        video_ids = client.get_video_ids(playlist_id)

        if not video_ids:
            logger.info(f"No videos found for channel_id: {channel_id}")
            return []

        # Step 3: Fetch video details (stats, duration, etc.)
        videos = client.get_videos_details(video_ids)

        # Step 4: Enrich each video with channel metadata
        for video in videos:
            video["channel_id"] = channel_info["channel_id"]
            video["channel_name"] = channel_info["channel_name"]
            video["channel_start_date"] = channel_info["channel_start_date"]
            video["subscribers_count"] = channel_info["subscribers_count"]

        logger.info(
            f"Extracted {len(videos)} videos from channel_id: {channel_id} "
            f"({channel_info['channel_name']})"
        )
        return videos

    except ValueError as e:
        # Channel not found or other API error
        logger.error(f"Failed to extract channel id: {channel_id}: {e}")
        return []
    except Exception as e:
        # Catch unexpected errors (network, timeout, etc.)
        logger.error(f"Unexpected error extracting for channel_id: {channel_id}: {e}", exc_info=True)
        return []


def extract_all_channels(api_key: str, channels_ids: list[dict[str, str]]) -> list[EnrichedVideoDetails]:
    """Extract data from multiple channels and aggregate results.

    Args:
        api_key: YouTube Data v3 API key
        channels_ids: List of channels (e.g., [{"channel_id": "UCj_iGliGCkLcHSZ8eqVNPDQ", "channel_name": "Grafikart.fr"}])

    Returns:
        Aggregated list of all videos from all channels.
    """
    client = YouTubeClient(api_key)
    all_videos = []

    for i, channel in enumerate(channels_ids, start=1):
        logger.info(f"Processing {i}/{len(channels_ids)}: {channel["channel_name"]} with id {channel["channel_id"]}")
        videos = extract_channel(client, channel["channel_id"])
        all_videos.extend(videos)

    logger.info(f"Extraction complete: {len(all_videos)} videos from {len(channels_ids)} channels")
    return all_videos
