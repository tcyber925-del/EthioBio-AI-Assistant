"""Tests for auto-labeling textbook diagrams with vision LLMs."""

import json
from unittest.mock import AsyncMock

import pytest


def test_build_vision_messages_includes_image():
    from scripts.label_textbook_diagrams import _build_vision_messages

    messages = _build_vision_messages("fake_base64_data")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    content = messages[1]["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert "data:image/jpeg;base64," in content[1]["image_url"]["url"]


def test_parse_labels_valid_json():
    from scripts.label_textbook_diagrams import _parse_labels_from_response

    raw = json.dumps([
        {"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3},
        {"id": "2", "text": "Cell membrane", "x": 0.2, "y": 0.8},
    ])
    result = _parse_labels_from_response(raw)
    assert len(result) == 2
    assert result[0]["text"] == "Nucleus"


def test_parse_labels_invalid_json():
    from scripts.label_textbook_diagrams import _parse_labels_from_response

    result = _parse_labels_from_response("not json at all")
    assert result == []


def test_parse_labels_empty_array():
    from scripts.label_textbook_diagrams import _parse_labels_from_response

    result = _parse_labels_from_response("[]")
    assert result == []


@pytest.mark.asyncio
async def test_try_model_with_fallback_success_first():
    from scripts.label_textbook_diagrams import _try_model_with_fallback

    router = AsyncMock()
    router.route = AsyncMock(return_value={
        "content": json.dumps([{"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3}]),
        "model": "openrouter/openai/gpt-4o",
    })

    messages = [{"role": "user", "content": "test"}]
    labels, model_used = await _try_model_with_fallback(router, messages)
    assert len(labels) == 1
    assert model_used == "openrouter/openai/gpt-4o"


@pytest.mark.asyncio
async def test_try_model_with_fallback_all_fail():
    from scripts.label_textbook_diagrams import _try_model_with_fallback

    router = AsyncMock()
    router.route = AsyncMock(return_value={"content": "", "model": "openrouter/openai/gpt-4o"})

    messages = [{"role": "user", "content": "test"}]
    labels, model_used = await _try_model_with_fallback(router, messages)
    assert labels == []
    assert model_used is None


@pytest.mark.asyncio
async def test_label_diagram_dry_run():
    from scripts.label_textbook_diagrams import label_diagram

    router = AsyncMock()
    router.route = AsyncMock(return_value={
        "content": json.dumps([{"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3}]),
        "model": "openrouter/openai/gpt-4o",
    })

    result = await label_diagram(
        image_path="nonexistent.jpg",
        grade=10,
        router=router,
        dry_run=True,
    )
    # No real image file exists, so _encode_image returns None -> result is None
    assert result is None
