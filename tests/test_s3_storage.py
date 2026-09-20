
import httpx
import pytest

from src.core.storage.s3 import S3StorageAdapter


class TestS3StorageAdapter:
    def _adapter(self, requests: list, status: int = 200, body: bytes = b"") -> S3StorageAdapter:
        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.method == "HEAD" and status == 404:
                return httpx.Response(404)
            return httpx.Response(status, content=body)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return S3StorageAdapter(
            bucket="uploads",
            endpoint_url="http://minio:9000",
            access_key="test-access",
            secret_key="test-secret",
            client=client,
        )

    async def test_store_puts_object_and_returns_key(self, tmp_path):
        requests: list[httpx.Request] = []
        adapter = self._adapter(requests, status=200)
        src = tmp_path / "file.pdf"
        src.write_bytes(b"pdf-bytes")

        key = await adapter.store(src, "ws-1", "ko-1", "file.pdf")

        assert key == "ws-1/ko-1/file.pdf"
        assert len(requests) == 1
        req = requests[0]
        assert req.method == "PUT"
        assert "/uploads/ws-1/ko-1/file.pdf" in str(req.url)
        assert req.content == b"pdf-bytes"
        assert req.headers["authorization"].startswith("AWS4-HMAC-SHA256")

    async def test_store_sanitizes_traversal_filename(self, tmp_path):
        requests: list[httpx.Request] = []
        adapter = self._adapter(requests, status=200)
        src = tmp_path / "f.txt"
        src.write_text("x")

        key = await adapter.store(src, "ws-1", "ko-1", "../../evil.txt")

        assert key == "ws-1/ko-1/evil.txt"
        assert "/uploads/ws-1/ko-1/evil.txt" in str(requests[0].url)

    async def test_store_rejects_traversal_workspace_id(self, tmp_path):
        adapter = self._adapter([], status=200)
        src = tmp_path / "f.txt"
        src.write_text("x")
        with pytest.raises(ValueError, match="workspace_id"):
            await adapter.store(src, "../ws", "ko-1", "f.txt")

    async def test_retrieve_downloads_to_temp_file(self, tmp_path):
        requests: list[httpx.Request] = []
        adapter = self._adapter(requests, status=200, body=b"downloaded")

        path = await adapter.retrieve("ws-1/ko-1/file.pdf")

        assert path.read_bytes() == b"downloaded"
        assert len(requests) == 1
        assert requests[0].method == "GET"
        path.unlink(missing_ok=True)

    async def test_retrieve_missing_raises(self):
        adapter = self._adapter([], status=404)
        with pytest.raises(FileNotFoundError):
            await adapter.retrieve("ws-1/ko-1/nope.pdf")

    async def test_delete_sends_delete(self):
        requests: list[httpx.Request] = []
        adapter = self._adapter(requests, status=204)

        await adapter.delete("ws-1/ko-1/file.pdf")

        assert len(requests) == 1
        assert requests[0].method == "DELETE"
        assert "/uploads/ws-1/ko-1/file.pdf" in str(requests[0].url)

    async def test_exists_head_returns_true(self):
        requests: list[httpx.Request] = []
        adapter = self._adapter(requests, status=200)

        assert await adapter.exists("ws-1/ko-1/file.pdf") is True
        assert requests[0].method == "HEAD"

    async def test_exists_missing_returns_false(self):
        adapter = self._adapter([], status=404)

        assert await adapter.exists("ws-1/ko-1/nope.pdf") is False

    async def test_retrieve_rejects_traversal_key(self):
        adapter = self._adapter([], status=200)
        with pytest.raises(ValueError, match="storage key"):
            await adapter.retrieve("../../etc/passwd")


class TestGetStorage:
    def _settings(self, backend: str = "local", **overrides):
        class FakeSettings:
            storage_backend = backend
            s3_endpoint_url = "http://minio:9000"
            s3_bucket = "uploads"
            s3_access_key = "ak"
            s3_secret_key = "sk"
            s3_region = "us-east-1"

        for k, v in overrides.items():
            setattr(FakeSettings, k, v)
        return FakeSettings()

    def test_local_backend_returns_local(self):
        from src.core.storage import LocalFileStorage, get_storage

        storage = get_storage(self._settings())
        assert isinstance(storage, LocalFileStorage)

    def test_s3_backend_returns_s3(self):
        from src.core.storage import get_storage

        storage = get_storage(self._settings(backend="s3"))
        assert isinstance(storage, S3StorageAdapter)

    def test_s3_backend_missing_config_raises(self):
        from src.core.storage import get_storage

        with pytest.raises(RuntimeError):
            get_storage(self._settings(backend="s3", s3_bucket=""))
