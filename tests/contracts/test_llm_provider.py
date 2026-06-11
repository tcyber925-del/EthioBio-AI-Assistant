"""Contract tests for the LLMProvider ABC.

Verifies that any concrete provider implements the full interface.
These tests do NOT instantiate a real provider — they validate
that the abstract interface contract is sound.
"""

from src.llm.providers.base import LLMProvider


def test_llm_provider_has_all_abstract_methods():
    """LLMProvider ABC requires 6 abstract methods + 1 abstract property."""
    abstract_methods = {
        "chat",
        "is_available",
        "get_available_models",
        "check_health",
        "get_info",
        "name",
    }
    found = set()
    for name in dir(LLMProvider):
        attr = getattr(LLMProvider, name, None)
        if attr is not None and getattr(attr, "__isabstractmethod__", False):
            found.add(name)
    assert found == abstract_methods, f"Missing abstract: {abstract_methods - found}"


def test_llm_provider_cannot_be_instantiated():
    """LLMProvider ABC raises TypeError on direct instantiation."""
    try:
        LLMProvider()  # type: ignore
        assert False, "Should have raised TypeError"
    except TypeError:
        pass


def test_chat_response_has_required_fields():
    """ChatResponse dataclass has expected fields."""
    from src.llm.providers.base import ChatResponse, UsageInfo

    response = ChatResponse(
        content="test",
        model="test-model",
        usage=UsageInfo(total_tokens=10, prompt_tokens=5, completion_tokens=5),
        provider="test-provider",
    )
    assert response.content == "test"
    assert response.model == "test-model"
    assert response.usage["total_tokens"] == 10
    assert response.provider == "test-provider"


def test_provider_info_has_required_fields():
    """ProviderInfo dataclass has expected fields."""
    from src.llm.providers.base import ProviderInfo

    info = ProviderInfo(
        name="test",
        provider_type="ollama",
        base_url="http://localhost:11434",
    )
    assert info.name == "test"
    assert info.provider_type == "ollama"
    assert info.available_models == []
