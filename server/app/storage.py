"""MinIO storage helpers for storing raw documents (resumes, JDs, artifacts).

Uses environment variables:
- MINIO_ENDPOINT
- MINIO_ACCESS_KEY
- MINIO_SECRET_KEY
- MINIO_BUCKET (default: talentflow)
"""
from __future__ import annotations

import os
from typing import Optional
try:
    from minio import Minio
    from minio.error import S3Error
    _HAS_MINIO = True
except Exception:
    Minio = None
    S3Error = Exception
    _HAS_MINIO = False

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "talentflow")


def get_client() -> Minio:
    if not _HAS_MINIO:
        raise RuntimeError("minio package not installed; install optional dependencies to use MinIO")
    return Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)


def ensure_bucket(client: Optional[Minio] = None, bucket: str = MINIO_BUCKET) -> None:
    c = client or get_client()
    try:
        if not c.bucket_exists(bucket):
            c.make_bucket(bucket)
    except S3Error as e:
        # Best effort in dev - surface as warning
        print(f"MinIO bucket ensure failed: {e}")


def upload_bytes(data: bytes, object_name: str, content_type: str = "application/octet-stream", client: Optional[Minio] = None, bucket: str = MINIO_BUCKET) -> str:
    c = client or get_client()
    ensure_bucket(c, bucket)
    c.put_object(bucket, object_name, data, length=len(data), content_type=content_type)
    return f"minio://{bucket}/{object_name}"


def download_bytes(object_name: str, client: Optional[Minio] = None, bucket: str = MINIO_BUCKET) -> Optional[bytes]:
    c = client or get_client()
    try:
        resp = c.get_object(bucket, object_name)
        data = resp.read()
        resp.close(); resp.release_conn()
        return data
    except Exception:
        return None
