import base64
from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.diagram import SketchToDiagramResponse


class TestSketchToDiagramSchemas:
    def test_sketch_response_minimal(self):
        resp = SketchToDiagramResponse(
            image_base64="AAAA",
            topic="cell",
            prompt="enhance",
        )
        assert resp.topic == "cell"
        assert resp.width == 800

    def test_sketch_response_full(self):
        resp = SketchToDiagramResponse(
            image_base64="AAAA",
            topic="dna",
            prompt="clean",
            model_used="@cf/test",
            width=1024,
            height=768,
        )
        assert resp.model_used == "@cf/test"
        assert resp.width == 1024


class TestSketchToDiagramEndpoint:
    @patch("src.api.diagram.CloudflareImageGenerator")
    @patch("src.config.Settings")
    async def test_sketch_endpoint_success(self, MockSettings, MockGen):
        mock_settings = AsyncMock()
        mock_settings.cloudflare_account_id = "test_account"
        mock_settings.cloudflare_api_token = "test_token"
        MockSettings.return_value = mock_settings

        mock_gen = AsyncMock()
        mock_gen.image_to_image = AsyncMock(return_value=b"enhanced_image_bytes")
        mock_gen.default_model = "@cf/test"
        MockGen.from_settings.return_value = mock_gen

        from src.api.diagram import sketch_to_diagram

        class FakeFile:
            async def read(self):
                return b"fake_image_bytes"

        result = await sketch_to_diagram(
            file=FakeFile(),  # type: ignore
            topic="cell",
            prompt="make it clean",
        )
        assert isinstance(result, SketchToDiagramResponse)
        assert result.topic == "cell"
        assert result.prompt == "make it clean"
        encoded_expected = base64.b64encode(b"enhanced_image_bytes").decode("utf-8")
        assert result.image_base64 == encoded_expected
        mock_gen.image_to_image.assert_awaited_once_with(
            prompt="make it clean",
            input_image=b"fake_image_bytes",
        )

    @patch("src.api.diagram.CloudflareImageGenerator")
    async def test_sketch_endpoint_empty_file(self, MockGen):
        from src.api.diagram import sketch_to_diagram

        class FakeFile:
            async def read(self):
                return b""

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await sketch_to_diagram(file=FakeFile(), topic="bio")  # type: ignore
        assert exc.value.status_code == 400
