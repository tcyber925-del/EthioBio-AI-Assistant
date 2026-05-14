import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_router():
    router = AsyncMock()
    router.route.return_value = {
        "content": "Test response",
        "model": "ollama/test",
        "confidence": 0.95,
        "usage": {"total_tokens": 50},
    }
    router.generate_embedding.return_value = [0.1] * 384
    return router


@pytest.fixture
def mock_retriever():
    retriever = AsyncMock()
    retriever.retrieve.return_value = [
        {"content": "Test curriculum content", "metadata": {"topic": "Cell Biology", "grade_level": 10}, "score": 0.95, "id": "1"}
    ]
    retriever.format_context.return_value = "[Source 1] Topic: Cell Biology | Grade: 10\nTest curriculum content"
    return retriever
