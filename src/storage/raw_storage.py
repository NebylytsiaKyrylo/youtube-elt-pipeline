"""Raw storage layer — read/write YouTube data JSON files in MinIO (S3-compatible)."""

import json
import logging
from datetime import date

import boto3
from botocore.exceptions import ClientError

from src.youtube.client import EnrichedVideoDetails

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

    @staticmethod
    def _build_key(ds: date) -> str:
        """Build the S3 object key for a given extraction date.

        Args:
            ds: Extraction date (e.g. 2026-04-16)

        Returns:
            Object key (e.g. "youtube_data_2026-04-16.json")
        """
        return f"youtube_data_{ds}.json"

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
        key = self._build_key(ds)
        payload = json.dumps(videos, ensure_ascii=False, indent=2)

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload.encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Uploaded %d videos → s3://%s/%s", len(videos), self.bucket, key)
        return key

    def read(self, ds: date | str | None = None) -> list[dict]:
        """Download and deserialize a JSON file from MinIO.

        Args:
            ds: Extraction date — accepts a date object, an ISO string ("2026-04-16"),
                or None to default to today.

        Returns:
            List of video dicts

        Raises:
            FileNotFoundError: If no file exists for the given date
            botocore.exceptions.ClientError: For any other S3 error
        """
        if ds is None:
            ds = date.today()
        elif isinstance(ds, str):
            ds = date.fromisoformat(ds)
        key = self._build_key(ds)
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
