"""Regression tests for page-number citation offsets.

Grade 10 stores PRINTED page numbers (re-ingested from a clean-text PDF with
_page_extract_number), so it must NOT have the display-time front-matter offset
applied. Grades 9/11/12 still store raw 1-indexed PDF page numbers and DO need
the offset.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.graph.nodes.retrieval import PAGE_OFFSET, RetrievalNode, _correct_page
from src.graph.state import AgentState
from src.retrieval.adapter import RetrievalResult


class TestCorrectPage:
    def test_grade_10_passes_through_uncorrected(self):
        # Grade 10 stores printed page numbers already.
        assert _correct_page(51, 10) == 51
        assert _correct_page(1, 10) == 1

    def test_grades_9_11_12_still_subtract_offset(self):
        assert PAGE_OFFSET == {9: 7, 11: 10, 12: 5}
        assert _correct_page(8, 9) == 1
        assert _correct_page(11, 11) == 1
        assert _correct_page(6, 12) == 1

    def test_unknown_grade_uncorrected(self):
        assert _correct_page(45, 13) == 45
        assert _correct_page(45, 0) == 45


class TestRetrievalNodePageCorrection:
    """RetrievalNode must not double-correct grade-10 printed page numbers."""

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
        # Grade 10 stores printed page numbers; the node must NOT subtract the
        # front-matter offset (regression: double-correction produced p.45 for
        # content that is actually on textbook page 51).
        node = RetrievalNode(self._adapter(page_number=51, grade=10))
        state = AgentState(user_message="What is water?", grade_level=10)

        result = await node(state)

        assert result.retrieved_chunks
        assert result.retrieved_chunks[0]["metadata"]["page_number"] == 51
        assert "p.51" in result.context

    @pytest.mark.asyncio
    async def test_grade_9_page_number_offset_applied(self):
        # Grades that still store raw PDF indices keep the display-time offset.
        node = RetrievalNode(self._adapter(page_number=8, grade=9))
        state = AgentState(user_message="Test query", grade_level=9)

        result = await node(state)

        assert result.retrieved_chunks[0]["metadata"]["page_number"] == 1
        assert "p.1" in result.context
