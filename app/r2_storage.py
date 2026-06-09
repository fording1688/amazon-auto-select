from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.client import Config

from app.config import get_settings


class R2StorageError(RuntimeError):
    pass


def _settings():
    settings = get_settings()
    missing = []
    if not settings.r2_access_key_id:
        missing.append("R2_ACCESS_KEY_ID")
    if not settings.r2_secret_access_key:
        missing.append("R2_SECRET_ACCESS_KEY")
    if not settings.r2_endpoint_url:
        missing.append("R2_ENDPOINT_URL")
    if not settings.r2_bucket_name:
        missing.append("R2_BUCKET_NAME")
    if missing:
        raise R2StorageError("R2 配置不完整，请在 .env 配置：" + ", ".join(missing))
    return settings


def _client():
    settings = _settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def safe_filename(name: str) -> str:
    stem = Path(name or "listing-image").stem[:80] or "listing-image"
    suffix = Path(name or "").suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-") or "listing-image"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"
    return f"{stem}{suffix}"


def build_listing_image_key(user_id: int | None, project_id: int, file_name: str) -> str:
    return f"listing-images/user-{user_id or 'unknown'}/project-{project_id}/{uuid.uuid4().hex}-{safe_filename(file_name)}"


def upload_listing_image(fileobj: BinaryIO, *, key: str, content_type: str | None = None) -> dict[str, str]:
    settings = _settings()
    client = _client()
    content_type = content_type or mimetypes.guess_type(key)[0] or "application/octet-stream"
    client.upload_fileobj(
        fileobj,
        settings.r2_bucket_name,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return {
        "bucket": settings.r2_bucket_name or "",
        "key": key,
        "public_url": public_url_for_key(key),
    }


def delete_object(key: str, bucket: str | None = None) -> None:
    if not key:
        return
    settings = _settings()
    _client().delete_object(Bucket=bucket or settings.r2_bucket_name, Key=key)


def public_url_for_key(key: str) -> str:
    settings = get_settings()
    base = (settings.r2_public_base_url or "").strip().rstrip("/")
    return f"{base}/{key}" if base else ""


def signed_url_for_key(key: str, bucket: str | None = None, expires_in: int = 3600) -> str:
    if not key:
        return ""
    settings = _settings()
    if settings.r2_public_base_url:
        return public_url_for_key(key)
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket or settings.r2_bucket_name, "Key": key},
        ExpiresIn=expires_in,
    )
