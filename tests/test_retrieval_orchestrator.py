"""Regression tests for memory retrieval resilience.

Verifies that cross-session recall still works through the Postgres BM25
path when the vector store (chromadb) is unavailable, so chat memory context
is not lost in deployments without chromadb.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.memory.retrieval_orchestrator import RetrievalOrchestrator


def _bm25_entry(**overrides):
    entry = {
        "id": "abc-123",
        "content": "Earlier the student asked about mitosis.",
        "topic": "Cell Division",
        "understanding_level": "intermediate",
        "confidence": 0.8,
        "created_at": "2026-08-01T12:00:00+00:00",
        "rank": 0.5,
    }
    entry.update(overrides)
    return entry


@pytest.mark.asyncio
async def test_search_falls_back_to_bm25_when_vector_store_fails():
    orch = RetrievalOrchestrator()
    orch.embedder = MagicMock()
    orch.embedder.embed_text = AsyncMock(return_value=[0.1, 0.2])
    orch.vector_store = MagicMock()
    orch.vector_store.search = AsyncMock(side_effect=RuntimeError("No module named 'chromadb'"))
    orch._bm25_search = AsyncMock(return_value=[_bm25_entry()])
    orch._bm25_search_summaries = AsyncMock(return_value=[])
    orch._entity_match_score = AsyncMock(return_value=0.0)
    db = MagicMock()

    results = await orch.search("mitosis", n_results=5, user_id="u1", db=db)

    assert len(results) == 1
    assert results[0].content == "Earlier the student asked about mitosis."
    orch.vector_store.search.assert_awaited_once()
    orch._bm25_search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_uses_vector_store_when_available():
    orch = RetrievalOrchestrator()
    orch.embedder = MagicMock()
    orch.embedder.embed_text = AsyncMock(return_value=[0.1, 0.2])
    orch.vector_store = MagicMock()
    orch.vector_store.search = AsyncMock(
        return_value=[
            {
                "id": "vec-1",
                "content": "A vector-stored memory.",
                "metadata": {"topic": "Cells", "confidence": 0.7, "created_at": None},
                "score": 0.9,
            }
        ]
    )
    orch._entity_match_score = AsyncMock(return_value=0.0)
    db = MagicMock()

    results = await orch.search("cells", n_results=5, user_id="u1", db=db)

    assert len(results) == 1
    assert results[0].memory_id == "vec-1"
    orch.vector_store.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_returns_empty_when_both_paths_empty():
    orch = RetrievalOrchestrator()
    orch.embedder = MagicMock()
    orch.embedder.embed_text = AsyncMock(return_value=[0.1, 0.2])
    orch.vector_store = MagicMock()
    orch.vector_store.search = AsyncMock(return_value=[])
    orch._bm25_search = AsyncMock(return_value=[])
    orch._bm25_search_summaries = AsyncMock(return_value=[])
    orch._entity_match_score = AsyncMock(return_value=0.0)

    results = await orch.search("nothing", n_results=5, user_id="u1", db=MagicMock())

    assert results == []
