"""Raw storage layer — read/write YouTube data JSON files in MinIO (S3-compatible)."""

import json
import logging
from datetime import date

import boto3
from botocore.exceptions import ClientError

from youtube.client import EnrichedVideoDetails

logger = logging.getLogger(__name__)


class RawStorage:
    """Uploads and downloads YouTube data JSON files from MinIO."""

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
            access_key: MinIO access key (MINIO_ACCESS_KEY)
            secret_key: MinIO secret key (MINIO_SECRET_KEY)
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
            ds: Extraction date used to build the object key

        Returns:
            Object key stored in MinIO (e.g. "youtube_data_2026-04-16.json")

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

    def read(self, key: str) -> list[dict]:
        """Download and deserialize a JSON file from MinIO.

        Args:
            key: Object key returned by write() (e.g. "youtube_data_2026-04-16.json")

        Returns:
            List of video dicts

        Raises:
            FileNotFoundError: If no file exists for the given key
            botocore.exceptions.ClientError: For any other S3 error
        """
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"].read().decode("utf-8")
            data = json.loads(body)
            logger.info("Downloaded %d records from s3://%s/%s", len(data), self.bucket, key)
            return data
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"s3://{self.bucket}/{key} not found")
            raise
