"""Write extracted YouTube data to MinIO (S3-compatible raw data lake)."""

import json
import logging
from datetime import date

import boto3

from src.youtube.client import EnrichedVideoDetails

logger = logging.getLogger(__name__)


class RawWriter:
    """Uploads extracted YouTube data as JSON to MinIO."""

    def __init__(
            self,
            endpoint_url: str,
            access_key: str,
            secret_key: str,
            bucket: str,
    ):
        """Initialize S3-compatible MinIO client.

        Args:
            endpoint_url: MinIO endpoint (e.g. "http://localhost:9000")
            access_key: MinIO root user (MINIO_ROOT_USER)
            secret_key: MinIO root password (MINIO_ROOT_PASSWORD)
            bucket: Target bucket name (e.g. "youtube-raw")
        """
        self.bucket = bucket
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def write(self, videos: list[EnrichedVideoDetails], ds: date) -> str:
        """Serialize and upload videos to MinIO as a single JSON file.

        Args:
            videos: List of enriched video details
            ds: Extraction date used as the object key (e.g. 2026-04-15)

        Returns:
            Object key stored in MinIO (e.g. "2026-04-15.json")

        Raises:
            botocore.exceptions.ClientError: If upload to MinIO fails
        """
        key = f"youtube_data_{ds}.json"
        payload = json.dumps(videos, ensure_ascii=False, indent=2)

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload.encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Uploaded %d videos → s3://%s/%s", len(videos), self.bucket, key)
        return key
