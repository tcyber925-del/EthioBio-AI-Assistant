"""Shared fixtures for integration and journey tests.

Provides mock DB sessions, mock LLM routers, and mock retrievers
that integration tests can reuse instead of each defining their own.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

test_docs = [
    {
        "content": "Test curriculum content",
        "metadata": {"topic": "Cell Biology", "grade_level": 10},
        "score": 0.95,
        "id": "1",
    },
]


@pytest.fixture
def mock_db_session():
    """Returns an AsyncMock session with canned execute behavior."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalar_one_or_none = AsyncMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_session_factory(mock_db_session):
    """Returns a callable that returns the mock_db_session."""
    factory = MagicMock()
    factory.return_value = mock_db_session
    return factory


@pytest.fixture
def mock_llm_router():
    """Returns an AsyncMock ModelRouter with canned responses."""
    router = AsyncMock()
    router.route = AsyncMock(
        return_value={
            "content": "Mock LLM response for testing.",
            "model": "mock-model",
            "usage": {"total_tokens": 50, "prompt_tokens": 30, "completion_tokens": 20},
            "provider": "mock",
        }
    )
    router.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    router.generate_embeddings = AsyncMock(return_value=[[0.1] * 384])
    return router


@pytest.fixture
def mock_retriever():
    """Returns a MagicMock VectorStoreAdapter with canned retrieval."""
    retriever = MagicMock()
    retriever.search = AsyncMock(return_value=[])
    retriever.retrieve = AsyncMock(return_value=test_docs)
    return retriever


@pytest.fixture
def mock_cache():
    """Returns an AsyncMock cache manager."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    return cache


@pytest.fixture
def agentic_rag_state():
    """Returns a minimal AgentState dict for integration tests."""
    return {
        "intent": "tutoring",
        "user_message": "What is mitosis?",
        "grade_level": 8,
        "language": "en",
        "requires_planning": True,
        "subtasks": [],
        "retrieved_chunks": [],
        "rewritten_queries": [],
        "query_groups": {},
        "evidence_items": [],
        "evidence_ids": [],
        "coverage_score": 0.0,
        "retrieval_iterations": 0,
        "draft": "",
        "groundedness_score": 0.0,
        "safe": True,
        "status": "pending",
    }
