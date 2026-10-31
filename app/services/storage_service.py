"""
Direct-to-storage uploads using presigned PUT URLs (works with AWS S3,
Cloudflare R2 and MinIO). The client uploads the file itself, so image bytes
never pass through the API server.
"""

import secrets
from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.exceptions import AppError, BadRequestError
from app.schemas.storefront import PresignedUpload
from app.utils.text import slugify

ALLOWED_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
ALLOWED_FOLDERS = {"avatars", "custom-requests", "reviews", "products", "content"}
STAFF_ONLY_FOLDERS = {"products", "content"}
UPLOAD_URL_TTL_SECONDS = 300


@lru_cache
def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.STORAGE_ENDPOINT_URL,
        aws_access_key_id=settings.STORAGE_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.STORAGE_SECRET_ACCESS_KEY or None,
        region_name=settings.STORAGE_REGION,
    )


def create_presigned_upload(folder: str, file_name: str, content_type: str, *, is_staff: bool) -> PresignedUpload:
    if folder not in ALLOWED_FOLDERS or (folder in STAFF_ONLY_FOLDERS and not is_staff):
        raise BadRequestError(f"Uploads to '{folder}' are not allowed", code="UPLOAD_FOLDER_NOT_ALLOWED")
    extension = ALLOWED_CONTENT_TYPES.get(content_type)
    if not extension:
        raise BadRequestError("Only JPEG, PNG and WebP images are allowed", code="UPLOAD_TYPE_NOT_ALLOWED")

    stem = slugify(file_name.rsplit(".", 1)[0], max_length=60)
    key = f"{folder}/{secrets.token_hex(8)}-{stem}.{extension}"
    try:
        upload_url = _client().generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.STORAGE_BUCKET, "Key": key, "ContentType": content_type},
            ExpiresIn=UPLOAD_URL_TTL_SECONDS,
            HttpMethod="PUT",
        )
    except (BotoCoreError, ClientError) as exc:
        raise AppError("Could not create upload URL", code="STORAGE_UNAVAILABLE") from exc

    return PresignedUpload(
        upload_url=upload_url,
        file_url=f"{settings.STORAGE_PUBLIC_BASE_URL.rstrip('/')}/{key}",
        expires_in_seconds=UPLOAD_URL_TTL_SECONDS,
    )
