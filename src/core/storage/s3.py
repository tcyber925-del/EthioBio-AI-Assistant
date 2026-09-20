from __future__ import annotations

import asyncio
import functools
import hashlib
import hmac
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
import structlog

from src.core.storage.interface import StorageAdapter
from src.core.storage.safe import safe_storage_parts, validate_storage_key

logger = structlog.get_logger()

_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def _signing_key(secret: str, date_stamp: str, region: str, service: str) -> bytes:
    def _hmac(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    k_date = _hmac(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region = _hmac(k_date, region)
    k_service = _hmac(k_region, service)
    return _hmac(k_service, "aws4_request")


class S3StorageAdapter(StorageAdapter):
    """Minimal S3-compatible (MinIO/AWS) adapter using httpx + AWS SigV4.

    Uses path-style addressing (``endpoint/bucket/key``), which works with
    MinIO and most S3-compatible stores. ``retrieve`` downloads to a temp
    file that is unlinked after ``temp_ttl_seconds``; callers must not delete
    returned paths themselves.
    """

    def __init__(
        self,
        bucket: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        client: httpx.AsyncClient | None = None,
        temp_ttl_seconds: float = 3600.0,
    ) -> None:
        self._bucket = bucket
        self._endpoint = endpoint_url.rstrip("/")
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._client = client or httpx.AsyncClient()
        self._temp_ttl_seconds = temp_ttl_seconds

    def _object_url(self, key: str) -> str:
        return f"{self._endpoint}/{self._bucket}/{quote(key, safe='/')}"

    def _auth_headers(
        self, method: str, path: str, payload_hash: str, now: datetime
    ) -> dict[str, str]:
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        host = urlparse(self._endpoint).netloc
        headers = {
            "host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        canonical_headers = "".join(f"{k}:{headers[k].strip()}\n" for k in sorted(headers))
        signed_headers = ";".join(sorted(headers))
        canonical_request = "\n".join(
            [method, path, "", canonical_headers, signed_headers, payload_hash]
        )
        scope = f"{date_stamp}/{self._region}/s3/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                scope,
                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
            ]
        )
        signature = hmac.new(
            _signing_key(self._secret_key, date_stamp, self._region, "s3"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        auth = (
            f"AWS4-HMAC-SHA256 Credential={self._access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return {**headers, "Authorization": auth}

    async def _request(self, method: str, key: str, *, data: bytes | None = None) -> httpx.Response:
        validate_storage_key(key)
        url = self._object_url(key)
        path = urlparse(url).path
        payload_hash = (
            hashlib.sha256(data).hexdigest() if data is not None else _EMPTY_SHA256
        )
        headers = self._auth_headers(method, path, payload_hash, datetime.now(timezone.utc))
        return await self._client.request(method, url, headers=headers, content=data)

    def _schedule_cleanup(self, path: Path) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        unlink = functools.partial(path.unlink, missing_ok=True)
        loop.call_later(self._temp_ttl_seconds, unlink)

    async def store(self, file_path: Path, workspace_id: str, ko_id: str, filename: str) -> str:
        ws_id, ko_id, safe_name = safe_storage_parts(workspace_id, ko_id, filename)
        key = f"{ws_id}/{ko_id}/{safe_name}"
        data = await asyncio.to_thread(file_path.read_bytes)
        resp = await self._request("PUT", key, data=data)
        resp.raise_for_status()
        logger.info("s3_object_stored", key=key, status=resp.status_code)
        return key

    async def retrieve(self, storage_key: str) -> Path:
        resp = await self._request("GET", storage_key)
        if resp.status_code == 404:
            raise FileNotFoundError(f"Storage key not found: {storage_key}")
        resp.raise_for_status()

        fd, tmp_name = tempfile.mkstemp(
            prefix="ethiosci-s3-", suffix=Path(storage_key).name
        )
        os.write(fd, resp.content)
        os.close(fd)
        path = Path(tmp_name)
        self._schedule_cleanup(path)
        return path

    async def delete(self, storage_key: str) -> None:
        resp = await self._request("DELETE", storage_key)
        resp.raise_for_status()

    async def exists(self, storage_key: str) -> bool:
        resp = await self._request("HEAD", storage_key)
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return True
