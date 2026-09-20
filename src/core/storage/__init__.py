from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.storage.interface import StorageAdapter
from src.core.storage.local import LocalFileStorage

if TYPE_CHECKING:
    from src.config import Settings

__all__ = [
    "StorageAdapter",
    "LocalFileStorage",
    "get_storage",
]


def get_storage(settings: Settings | None = None) -> StorageAdapter:
    """Build the configured file-storage backend (``storage_backend``: local | s3)."""
    if settings is None:
        from src.config import settings as app_settings

        settings = app_settings

    if settings.storage_backend == "s3":
        if not settings.s3_bucket or not settings.s3_endpoint_url:
            raise RuntimeError("storage_backend=s3 requires s3_bucket and s3_endpoint_url")
        from src.core.storage.s3 import S3StorageAdapter

        return S3StorageAdapter(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
        )
    return LocalFileStorage()
