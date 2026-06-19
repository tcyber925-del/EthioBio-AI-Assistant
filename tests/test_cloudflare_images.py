import base64
from unittest.mock import AsyncMock, MagicMock

import pytest

VALID_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
VALID_PNG_BYTES = base64.b64decode(VALID_PNG_B64)


def _mock_http_response(status_code: int = 200, json_body: dict | None = None):
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = str(json_body) if json_body else ""
    if status_code == 200:
        dummy_b64 = base64.b64encode(b"fake-image-bytes").decode()
        mock.json.return_value = json_body or {"result": {"image": dummy_b64}}
    return mock


class TestCloudflareConfig:
    def test_settings_have_cloudflare_fields(self):
        from src.config import Settings

        s = Settings()
        assert hasattr(s, "cloudflare_account_id")
        assert hasattr(s, "cloudflare_api_token")
        assert hasattr(s, "cloudflare_image_model")


class TestCloudflareGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_bytes_on_success(self):
        from src.services.cloudflare_images import CloudflareImageGenerator

        mock_client = MagicMock()
        mock_response = _mock_http_response(200)
        mock_client.post = AsyncMock(return_value=mock_response)

        generator = CloudflareImageGenerator(
            account_id="test-account",
            api_token="test-token",
            http_client=mock_client,
        )
        result = await generator.generate(prompt="A cell diagram", model="@cf/test/model")
        assert result == b"fake-image-bytes"

    @pytest.mark.asyncio
    async def test_generate_raises_on_api_error(self):
        from src.services.cloudflare_images import CloudflareImageGenerator

        mock_client = MagicMock()
        mock_response = _mock_http_response(400, {"error": "bad request"})
        mock_client.post = AsyncMock(return_value=mock_response)

        generator = CloudflareImageGenerator(
            account_id="test-account",
            api_token="test-token",
            http_client=mock_client,
        )
        with pytest.raises(RuntimeError, match="Cloudflare API error"):
            await generator.generate(prompt="fail")

    @pytest.mark.asyncio
    async def test_generate_uses_configured_model_by_default(self):
        from src.services.cloudflare_images import CloudflareImageGenerator

        mock_client = MagicMock()
        mock_response = _mock_http_response(200)
        mock_client.post = AsyncMock(return_value=mock_response)

        generator = CloudflareImageGenerator(
            account_id="test-account",
            api_token="test-token",
            http_client=mock_client,
            default_model="@cf/test/default",
        )
        await generator.generate(prompt="test")
        call_url = mock_client.post.call_args[0][0]
        assert "@cf/test/default" in call_url

    @pytest.mark.asyncio
    async def test_generate_allows_override_model(self):
        from src.services.cloudflare_images import CloudflareImageGenerator

        mock_client = MagicMock()
        mock_response = _mock_http_response(200)
        mock_client.post = AsyncMock(return_value=mock_response)

        generator = CloudflareImageGenerator(
            account_id="test-account",
            api_token="test-token",
            http_client=mock_client,
            default_model="@cf/test/default",
        )
        await generator.generate(prompt="test", model="@cf/test/override")
        call_url = mock_client.post.call_args[0][0]
        assert "@cf/test/override" in call_url
        assert "@cf/test/default" not in call_url

    @pytest.mark.asyncio
    async def test_generate_sets_auth_header(self):
        from src.services.cloudflare_images import CloudflareImageGenerator

        mock_client = MagicMock()
        mock_response = _mock_http_response(200)
        mock_client.post = AsyncMock(return_value=mock_response)

        generator = CloudflareImageGenerator(
            account_id="test-account",
            api_token="test-token",
            http_client=mock_client,
        )
        await generator.generate(prompt="test", model="@cf/test/model")
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-token"


class TestCloudflareImageToImage:
    @pytest.mark.asyncio
    async def test_image_to_image_returns_bytes(self):
        from src.services.cloudflare_images import CloudflareImageGenerator

        mock_client = MagicMock()
        mock_response = _mock_http_response(200)
        mock_client.post = AsyncMock(return_value=mock_response)

        generator = CloudflareImageGenerator(
            account_id="test-account",
            api_token="test-token",
            http_client=mock_client,
        )
        result = await generator.image_to_image(
            prompt="enhance this",
            input_image=VALID_PNG_BYTES,
        )
        assert result == b"fake-image-bytes"

    @pytest.mark.asyncio
    async def test_image_to_image_sends_base64(self):
        from src.services.cloudflare_images import CloudflareImageGenerator

        mock_client = MagicMock()
        mock_response = _mock_http_response(200)
        mock_client.post = AsyncMock(return_value=mock_response)

        generator = CloudflareImageGenerator(
            account_id="test-account",
            api_token="test-token",
            http_client=mock_client,
        )
        await generator.image_to_image(
            prompt="enhance",
            input_image=VALID_PNG_BYTES,
        )
        call_kwargs = mock_client.post.call_args[1]
        body = call_kwargs["json"]
        assert "prompt" in body
        assert "image_b64" in body
        assert isinstance(body["image_b64"], str)
        assert len(body["image_b64"]) > 0

    @pytest.mark.asyncio
    async def test_image_to_image_uses_sd_model_by_default(self):
        from src.services.cloudflare_images import CloudflareImageGenerator

        mock_client = MagicMock()
        mock_response = _mock_http_response(200)
        mock_client.post = AsyncMock(return_value=mock_response)

        generator = CloudflareImageGenerator(
            account_id="test-account",
            api_token="test-token",
            http_client=mock_client,
        )
        await generator.image_to_image(prompt="enhance", input_image=VALID_PNG_BYTES)
        call_url = mock_client.post.call_args[0][0]
        assert "stable-diffusion" in call_url or "sdxl" in call_url.lower()


class TestCloudflareFactory:
    def test_from_settings_creates_generator(self):
        from src.services.cloudflare_images import CloudflareImageGenerator

        settings = MagicMock()
        settings.cloudflare_account_id = "acc-123"
        settings.cloudflare_api_token = "tok-456"
        settings.cloudflare_image_model = "@cf/test/model"

        generator = CloudflareImageGenerator.from_settings(settings)
        assert generator.account_id == "acc-123"
        assert generator.api_token == "tok-456"
        assert generator.default_model == "@cf/test/model"
