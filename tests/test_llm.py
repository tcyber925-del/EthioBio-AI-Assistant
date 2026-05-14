import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.llm.ollama_client import OllamaClient
from src.llm.router import ModelRouter


@pytest.mark.asyncio
async def test_ollama_chat_success():
    client = OllamaClient(base_url="http://test:11434", model="test-model")
    client.client = AsyncMock()
    import httpx
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json = MagicMock(return_value={
        "message": {"content": "Test biology answer"},
        "eval_count": 50,
        "prompt_eval_count": 30,
    })
    client.client.post.return_value = mock_response

    result = await client.chat([{"role": "user", "content": "What is a cell?"}])
    assert result["content"] == "Test biology answer"
    assert "model" in result
    assert "usage" in result
    await client.close()


@pytest.mark.asyncio
async def test_ollama_connection_error():
    client = OllamaClient(base_url="http://nonexistent:11434", model="test-model")
    client.client = AsyncMock()
    client.client.post.side_effect = ConnectionError("Connection refused")

    with pytest.raises(ConnectionError):
        await client.chat([{"role": "user", "content": "test"}])
    await client.close()


@pytest.mark.asyncio
async def test_router_low_confidence_fallback():
    router = ModelRouter()
    router.ollama = AsyncMock()
    router.ollama.chat.return_value = {
        "content": "I'm not sure about the answer",
        "model": "ollama/test",
        "usage": {"total_tokens": 20},
    }
    router.fallback = AsyncMock()
    router.fallback.is_available.return_value = True
    router.fallback.chat.return_value = {
        "content": "The correct biology answer is...",
        "model": "fallback/gpt-4o-mini",
        "usage": {"total_tokens": 100},
    }

    result = await router.route(
        messages=[{"role": "user", "content": "test"}],
        request_type="test",
    )
    assert router.fallback.chat.called
    assert "The correct biology answer" in result["content"]


@pytest.mark.asyncio
async def test_router_ollama_down_fallback():
    router = ModelRouter()
    router.ollama = AsyncMock()
    router.ollama.chat.side_effect = ConnectionError("Ollama down")
    router.fallback = AsyncMock()
    router.fallback.is_available.return_value = True
    router.fallback.chat.return_value = {
        "content": "Fallback response",
        "model": "fallback/gpt-4o-mini",
        "usage": {"total_tokens": 50},
    }

    result = await router.route(
        messages=[{"role": "user", "content": "test"}],
        request_type="test",
    )
    assert "Fallback response" in result["content"]
