from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.api.diagram import style_transfer
from src.schemas.diagram import StyleTransferRequest, StyleTransferResponse


class TestStyleTransferSchemas:
    def test_style_transfer_request_minimal(self):
        req = StyleTransferRequest(svg="<svg/>")
        assert req.prompt != ""
        assert req.reference_image_base64 == ""

    def test_style_transfer_request_full(self):
        req = StyleTransferRequest(
            svg="<svg/>",
            reference_image_base64="AAAA",
            prompt="make it look like a textbook",
        )
        assert req.prompt == "make it look like a textbook"

    def test_style_transfer_response(self):
        resp = StyleTransferResponse(image_base64="AAAA", prompt="test")
        assert resp.width == 800
        assert resp.height == 600


class TestStyleTransferEndpoint:
    @patch("src.api.diagram.CloudflareImageGenerator")
    @patch("src.config.Settings")
    @patch("src.api.diagram.render_svg_to_png")
    async def test_style_transfer_success(self, mock_render, mock_settings_cls, mock_gen_cls):
        mock_render.return_value = b"png_bytes"
        mock_settings = AsyncMock()
        mock_settings.cloudflare_account_id = "acc"
        mock_settings.cloudflare_api_token = "tok"
        mock_settings_cls.return_value = mock_settings

        mock_gen = AsyncMock()
        mock_gen.image_to_image = AsyncMock(return_value=b"styled_result")
        mock_gen_cls.from_settings.return_value = mock_gen

        result = await style_transfer(
            StyleTransferRequest(svg="<svg/>", prompt="style it"),
        )
        assert isinstance(result, StyleTransferResponse)
        assert result.image_base64 != ""
        assert result.prompt == "style it"
        mock_render.assert_called_once_with("<svg/>")
        mock_gen.image_to_image.assert_awaited_once_with(
            prompt="style it", input_image=b"png_bytes",
        )

    @patch("src.api.diagram.render_svg_to_png")
    async def test_style_transfer_bad_svg(self, mock_render):
        mock_render.side_effect = Exception("bad svg")

        with pytest.raises(HTTPException) as exc:
            await style_transfer(StyleTransferRequest(svg="bad"))
        assert exc.value.status_code == 422
