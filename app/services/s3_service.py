"""
Bazaura.pk - S3 / MinIO Service (Demo Mode)
Generates presigned PUT URLs for direct client uploads to a local MinIO instance.
Uses boto3 with ``aws_access_key_id``/``aws_secret_access_key`` from settings.
"""

import urllib.parse
from datetime import datetime, timedelta
from typing import Dict

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class S3Service:
    """Utility wrapper around ``boto3`` for generating presigned URLs.

    The service is deliberately minimal – it only supports a ``presign_put``
    operation required by the ``/uploads/presigned-url`` endpoint.
    """

    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url="http://localhost:9000",  # MinIO local endpoint
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket = settings.AWS_S3_BUCKET_NAME

    def presign_put(
        self,
        folder: str,
        file_name: str,
        file_type: str,
        expires_in: int = 300,
    ) -> Dict[str, str]:
        """Return a dict with a presigned PUT URL and the final public file URL.

        Parameters
        ----------
        folder: str
            Logical folder inside the bucket (e.g. ``"sourcing_requests"``).
        file_name: str
            Desired object name.
        file_type: str
            MIME type – stored as ``Content-Type`` metadata.
        expires_in: int, optional
            Seconds until the URL expires (default 5 minutes).
        """
        object_key = f"{folder.rstrip('/')}/{file_name}".lstrip('/')
        try:
            upload_url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": object_key,
                    "ContentType": file_type,
                },
                ExpiresIn=expires_in,
                HttpMethod="PUT",
            )
        except ClientError as exc:
            raise RuntimeError(f"Failed to generate presigned URL: {exc}") from exc

        # Public URL – MinIO serves objects at ``/bucket_name/object_key``
        final_url = f"{settings.S3_PUBLIC_BASE_URL}/{urllib.parse.quote(object_key)}"
        return {"uploadUrl": upload_url, "finalFileUrl": final_url, "expiresInSeconds": expires_in}


__all__ = ["S3Service"]
