from unittest.mock import AsyncMock, MagicMock

import pytest

from src.llm.ollama_client import OllamaClient
from src.llm.router import ModelRouter


@pytest.mark.asyncio
async def test_ollama_chat_success():
    client = OllamaClient(base_url="http://test:11434", model="test-model")
    client.client = AsyncMock()
    import httpx

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json = MagicMock(
        return_value={
            "message": {"content": "Test biology answer"},
            "eval_count": 50,
            "prompt_eval_count": 30,
        }
    )
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
    router._manager = AsyncMock()
    router._manager.route.return_value = {
        "content": "I'm not sure about the answer",
        "model": "ollama/test",
        "usage": {"total_tokens": 20},
    }

    result = await router.route(
        messages=[{"role": "user", "content": "test"}],
        request_type="test",
    )
    assert "I'm not sure" in result["content"]
    assert result["confidence"] == 0.3


@pytest.mark.asyncio
async def test_router_ollama_down_fallback():
    router = ModelRouter()
    router._manager = AsyncMock()
    router._manager.route.side_effect = ConnectionError("Ollama down")

    with pytest.raises(ConnectionError):
        await router.route(
            messages=[{"role": "user", "content": "test"}],
            request_type="test",
        )


@pytest.mark.asyncio
async def test_ollama_provider_chat():
    from src.llm.providers.ollama import OllamaProvider

    provider = OllamaProvider(base_url="http://test:11434", default_model="test-model")
    provider._client = AsyncMock()
    import httpx

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.json = MagicMock(
        return_value={
            "message": {"content": "Test response"},
            "eval_count": 50,
            "prompt_eval_count": 30,
        }
    )
    provider._client.post.return_value = mock_response

    result = await provider.chat([{"role": "user", "content": "test"}])
    assert result.content == "Test response"
    assert result.model == "ollama/test-model"
    assert result.provider == "ollama"
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_provider_list_models():
    from src.llm.providers.ollama import OllamaProvider

    provider = OllamaProvider(base_url="http://test:11434")
    provider._client = AsyncMock()
    import httpx

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.is_success = True
    mock_response.json = MagicMock(
        return_value={"models": [{"name": "llama3.2:3b"}, {"name": "gemma4:31b-cloud"}]}
    )
    provider._client.get.return_value = mock_response

    models = await provider.get_available_models()
    assert models == ["llama3.2:3b", "gemma4:31b-cloud"]
    await provider.close()


@pytest.mark.asyncio
async def test_provider_manager_fallback_chain():
    from src.llm.manager import ProviderManager

    manager = ProviderManager()
    assert "ollama" in manager._providers
    assert "ollama" in manager._fallback_chain


@pytest.mark.asyncio
async def test_provider_manager_set_active_model():
    from src.llm.manager import ProviderManager

    manager = ProviderManager()
    manager.set_active_model("gemma4:31b-cloud")
    assert manager.active_model == "gemma4:31b-cloud"


@pytest.mark.asyncio
async def test_model_registry_discovery():
    from src.llm.registry import ModelRegistry

    registry = ModelRegistry(base_url="http://test:11434")
    registry._client = AsyncMock()
    import httpx

    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.is_success = True
    mock_response.json = MagicMock(
        return_value={"models": [{"name": "model1"}, {"name": "model2"}]}
    )
    registry._client.get.return_value = mock_response

    models = await registry.list_ollama_models()
    assert models == ["model1", "model2"]
    models2 = await registry.list_ollama_models()
    assert models2 == ["model1", "model2"]
    await registry.close()


@pytest.mark.asyncio
async def test_router_backward_compat():
    from src.llm.router import ModelRouter

    router = ModelRouter()
    router._manager = AsyncMock()
    router._manager.route.return_value = {
        "content": "Test response",
        "model": "ollama/test",
        "usage": {"total_tokens": 50},
    }

    result = await router.route(
        messages=[{"role": "user", "content": "test"}],
        request_type="test",
    )
    assert result["content"] == "Test response"
    assert result["model"] == "ollama/test"
    await router.close()
