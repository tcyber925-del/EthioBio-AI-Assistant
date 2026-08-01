"""Regression tests for page-number citations.

All grades now store PRINTED textbook page numbers in the vector store
(extracted by scripts/ingest_curriculum.py:_extract_page_number()), so the
retrieval node must NOT apply any display-time front-matter offset.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.graph.nodes.retrieval import RetrievalNode
from src.graph.state import AgentState
from src.retrieval.adapter import RetrievalResult


class TestRetrievalNodePagePassthrough:
    """RetrievalNode must pass stored page numbers through unchanged."""

    def _quality_content(self) -> str:
        # Passes _is_quality_content via a long body-text block.
        return (
            "Water is considered as a biochemical molecule because it does not "
            "contain carbon and was not created through biological means except "
            "oxides. " * 4
        )

    def _adapter(self, page_number: int, grade: int) -> MagicMock:
        adapter = MagicMock()
        adapter.search = AsyncMock(
            return_value=[
                RetrievalResult(
                    content=self._quality_content(),
                    metadata={"grade_level": grade, "page_number": page_number, "source_file": "x.pdf"},
                    score=0.9,
                    source_id="a",
                )
            ]
        )
        adapter.format_context = lambda results, max_chars=4000: "".join(
            f"[Source {i + 1}] Grade {r.metadata.get('grade_level')} Biology | "
            f"p.{r.metadata.get('page_number')}\n{r.content}"
            for i, r in enumerate(results)
        )
        return adapter

    @pytest.mark.asyncio
    async def test_grade_10_page_number_preserved(self):
        # Regression: double-correction produced p.45 for content that is
        # actually on textbook page 51.
        node = RetrievalNode(self._adapter(page_number=51, grade=10))
        state = AgentState(user_message="What is water?", grade_level=10)

        result = await node(state)

        assert result.retrieved_chunks
        assert result.retrieved_chunks[0]["metadata"]["page_number"] == 51
        assert "p.51" in result.context

    @pytest.mark.asyncio
    async def test_grades_9_11_12_page_numbers_preserved(self):
        # All grades store printed page numbers; none get an offset applied.
        for grade, page in [(9, 45), (11, 100), (12, 254)]:
            node = RetrievalNode(self._adapter(page_number=page, grade=grade))
            state = AgentState(user_message="Test query", grade_level=grade)

            result = await node(state)

            assert result.retrieved_chunks[0]["metadata"]["page_number"] == page
            assert f"p.{page}" in result.context
