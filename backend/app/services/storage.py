"""Private evidence storage.

Evidence is always encrypted (AES-256-GCM) *before* it reaches storage, so
neither the disk nor an object storage provider ever sees plaintext. Storage
keys are random and unrelated to the complaint or the original file name.
Nothing here is reachable through a public URL: evidence is only served by
an authenticated admin endpoint.
"""

from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from app.config import get_settings


class StorageError(Exception):
    pass


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not key.isalnum():
            raise StorageError("Invalid storage key")
        # Shard into sub-directories to keep folders small.
        return self.root / key[:2] / key

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except OSError:  # pragma: no cover - Windows ignores POSIX modes
            pass

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise StorageError("Evidence file not found")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


class S3Storage:  # pragma: no cover - requires a real bucket
    """S3-compatible private object storage (AWS S3, MinIO, Cloudflare R2...).

    The bucket must block all public access. Objects are additionally
    encrypted by the application before upload.
    """

    def __init__(self, bucket: str, prefix: str, region: str | None, endpoint_url: str | None) -> None:
        try:
            import boto3  # noqa: PLC0415
        except ImportError as exc:
            raise StorageError("Install boto3 (pip install -r requirements-s3.txt) to use S3 storage.") from exc
        self.bucket = bucket
        self.prefix = prefix
        self.client = boto3.client("s3", region_name=region, endpoint_url=endpoint_url)

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=self.prefix + key, Body=data,
                               ContentType="application/octet-stream", ServerSideEncryption="AES256")

    def get(self, key: str) -> bytes:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=self.prefix + key)["Body"].read()
        except Exception as exc:  # noqa: BLE001
            raise StorageError("Evidence file not found") from exc

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self.prefix + key)


@lru_cache
def get_storage():
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage(settings.s3_bucket or "", settings.s3_prefix, settings.s3_region, settings.s3_endpoint_url)
    return LocalStorage(settings.evidence_dir)


def new_storage_key() -> str:
    return secrets.token_hex(24)
