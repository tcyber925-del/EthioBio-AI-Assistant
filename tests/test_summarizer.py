"""Regression tests for the session summarizer (memory summarization).

Verifies that a DB summary is still persisted even when the vector store
(e.g. chromadb) is unavailable, so sessions never cascade into summary="".
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.memory.summarizer import Summarizer
from src.database.models import MemoryEducationalSummary, MemorySession

VALID_SUMMARY = json.dumps(
    {
        "understanding_level": "intermediate",
        "key_misconceptions": [],
        "confidence": 0.8,
        "next_learning_goal": "practice cell division",
    }
)


@pytest.fixture
def session():
    s = MemorySession(
        session_id=uuid4(),
        user_id=uuid4(),
        active_topic="Cell Division",
        tutoring_mode="direct",
    )
    s.educational_context = {"messages": [{"role": "user", "content": "explain mitosis"}]}
    return s


def _make_summarizer(vs_add_side_effect=None):
    llm = AsyncMock()
    llm.route.return_value = {"content": VALID_SUMMARY}
    summ = Summarizer(llm_router=llm)
    summ.embedder = MagicMock()
    summ.embedder.embed_text = AsyncMock(return_value=[0.1, 0.2])
    vs = MagicMock()
    vs.add_memory = AsyncMock(side_effect=vs_add_side_effect)
    summ.vector_store = vs
    return summ


def _make_db():
    db = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_summarize_persists_db_summary_when_vector_store_fails(session):
    summ = _make_summarizer(vs_add_side_effect=RuntimeError("No module named 'chromadb'"))
    db = _make_db()

    with patch("src.core.memory.entity_extractor.EntityExtractor") as extractor_cls:
        extractor_cls.return_value.extract_from_session = AsyncMock(return_value=None)
        result = await summ.summarize_session(session, conversation_context="hi", db=db)

    assert result is not None
    assert isinstance(result, MemoryEducationalSummary)
    assert session.summary  # DB summary saved despite vector store failure
    # DB got the summary row, and the vector store failure was swallowed
    added_args = [c.args[0] for c in db.add.call_args_list]
    assert MemoryEducationalSummary in [type(a) for a in added_args]
    assert db.flush.await_count > 0


@pytest.mark.asyncio
async def test_summarize_persists_db_summary_and_uses_vector_store(session):
    summ = _make_summarizer(vs_add_side_effect=None)
    db = _make_db()

    with patch("src.core.memory.entity_extractor.EntityExtractor") as extractor_cls:
        extractor_cls.return_value.extract_from_session = AsyncMock(return_value=None)
        result = await summ.summarize_session(session, conversation_context="hi", db=db)

    assert result is not None
    assert session.summary
    assert summ.vector_store.add_memory.await_count == 1


@pytest.mark.asyncio
async def test_summarize_returns_none_without_db(session):
    summ = _make_summarizer()
    result = await summ.summarize_session(session, conversation_context="hi", db=None)
    assert result is None
    summ.vector_store.add_memory.assert_not_awaited()
