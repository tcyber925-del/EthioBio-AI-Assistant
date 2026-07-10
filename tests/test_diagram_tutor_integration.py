"""Tests for diagram-tutor integration module."""

from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.diagram_tutor_integration import (
    _get_diagram_agent,
    find_best_textbook_diagram,
    generate_tutor_diagram,
    should_generate_diagram,
)


class TestShouldGenerateDiagram:
    def test_rag_trigger_with_textbook_diagram_chunk(self):
        chunks = [{"metadata": {"source_type": "textbook_diagram"}}]
        assert should_generate_diagram(chunks, "cells") is True

    def test_rag_trigger_no_textbook_diagram_chunk(self):
        chunks = [{"metadata": {"source_type": "pdf_page"}}]
        assert should_generate_diagram(chunks, topic="evolution", question="tell me about") is False

    def test_rag_trigger_empty_chunks(self):
        assert should_generate_diagram([], topic="evolution", question="tell me about") is False

    def test_rag_trigger_missing_metadata(self):
        chunks = [{"content": "some text"}]
        assert should_generate_diagram(chunks, topic="evolution", question="tell me about") is False

    def test_rag_trigger_multiple_chunks_one_match(self):
        chunks = [
            {"metadata": {"source_type": "pdf_page"}},
            {"metadata": {"source_type": "textbook_diagram"}},
            {"metadata": {"source_type": "pdf_page"}},
        ]
        assert should_generate_diagram(chunks, "cells") is True


class TestFindBestTextbookDiagram:
    def _make_session_mock(self, rows: list) -> AsyncMock:
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        mock_session.execute.return_value = mock_result
        return mock_session

    async def test_exact_grade_topic_match(self):
        mock_row = MagicMock()
        mock_row.caption = "Structure of a plant cell"
        mock_row.figure_number = 2
        mock_row.unit = "Unit 3: Cells"
        mock_row.grade_level = 10
        mock_row.topic = "Cells"
        mock_session = self._make_session_mock([mock_row])

        result = await find_best_textbook_diagram(
            query="plant cell",
            grade_level=10,
            topic="Cells",
            session=mock_session,
        )
        assert result is not None
        assert result["caption"] == "Structure of a plant cell"
        assert result["figure_number"] == 2
        assert result["grade_level"] == 10

    async def test_grade_match_topic_substring(self):
        mock_row = MagicMock()
        mock_row.caption = "Animal cell diagram"
        mock_row.figure_number = 1
        mock_row.unit = "Unit 3"
        mock_row.grade_level = 9
        mock_row.topic = "Cell Biology"
        mock_session = self._make_session_mock([mock_row])

        result = await find_best_textbook_diagram(
            query="animal cell",
            grade_level=9,
            topic="cell",
            session=mock_session,
        )
        assert result is not None
        assert result["caption"] == "Animal cell diagram"

    async def test_no_match_returns_none(self):
        mock_session = self._make_session_mock([])

        result = await find_best_textbook_diagram(
            query="quantum physics",
            grade_level=10,
            topic="physics",
            session=mock_session,
        )
        assert result is None

    async def test_prefers_starts_with_over_substring(self):
        row1 = MagicMock()
        row1.caption = "Advanced genetics"
        row1.figure_number = 5
        row1.unit = "Unit 5"
        row1.grade_level = 11
        row1.topic = "Genetics and Heredity"
        row2 = MagicMock()
        row2.caption = "Basic genetics overview"
        row2.figure_number = 1
        row2.unit = "Unit 5"
        row2.grade_level = 11
        row2.topic = "Genetics"
        mock_session = self._make_session_mock([row1, row2])

        result = await find_best_textbook_diagram(
            query="genetics",
            grade_level=11,
            topic="Genetics",
            session=mock_session,
        )
        assert result is not None
        assert result["caption"] == "Basic genetics overview"

    async def test_db_exception_returns_none(self):
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute.side_effect = Exception("DB error")

        result = await find_best_textbook_diagram(
            query="cells",
            grade_level=10,
            topic="cells",
            session=mock_session,
        )
        assert result is None


class TestGenerateTutorDiagram:
    @patch("src.agents.diagram_tutor_integration._get_diagram_agent")
    async def test_generates_diagram_when_textbook_match(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.generate.return_value = {
            "diagram_svg": "<svg>textbook plant cell</svg>",
            "labels": [{"id": "nucleus", "text": "Nucleus", "x": 100, "y": 200}],
            "title": "Plant Cell Structure",
        }
        mock_get_agent.return_value = mock_agent

        mock_row = MagicMock()
        mock_row.caption = "Structure of a plant cell"
        mock_row.figure_number = 2
        mock_row.unit = "Unit 3: Cells and Tissues"
        mock_row.grade_level = 10
        mock_row.topic = "Cells"
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        result = await generate_tutor_diagram(
            question="draw a plant cell",
            topic="Cells",
            grade_level=10,
            db_session=mock_session,
            retrieved_chunks=[{"metadata": {"source_type": "textbook_diagram"}}],
            diagram_agent=mock_agent,
        )
        assert result["diagram_svg"] == "<svg>textbook plant cell</svg>"
        assert len(result["labels"]) == 1
        assert result["title"] == "Plant Cell Structure"
        assert "Grade 10" in result.get("textbook_ref", "")
        assert "Figure 2" in result.get("textbook_ref", "")
        mock_agent.generate.assert_awaited_once_with(
            prompt="Structure of a plant cell",
            topic="Cells",
            difficulty="beginner",
            grade=10,
        )

    @patch("src.agents.diagram_tutor_integration._get_diagram_agent")
    async def test_no_diagram_when_no_rag_trigger(self, mock_get_agent):
        result = await generate_tutor_diagram(
            question="what is biology",
            topic="biology",
            grade_level=10,
            db_session=None,
            retrieved_chunks=[],
        )
        assert result == {}
        mock_get_agent.assert_not_called()

    @patch("src.agents.diagram_tutor_integration._get_diagram_agent")
    async def test_no_diagram_when_chunks_no_textbook(self, mock_get_agent):
        result = await generate_tutor_diagram(
            question="explain evolution",
            topic="evolution",
            grade_level=10,
            db_session=None,
            retrieved_chunks=[{"metadata": {"source_type": "pdf_page"}}],
        )
        assert result == {}
        mock_get_agent.assert_not_called()

    @patch("src.agents.diagram_tutor_integration._get_diagram_agent")
    async def test_fallback_when_no_db_session(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.generate.return_value = {
            "diagram_svg": "<svg>fallback</svg>",
            "labels": [],
            "title": "Cells",
        }
        mock_get_agent.return_value = mock_agent

        result = await generate_tutor_diagram(
            question="draw a cell",
            topic="cells",
            grade_level=10,
            db_session=None,
            retrieved_chunks=[{"metadata": {"source_type": "textbook_diagram"}}],
            diagram_agent=mock_agent,
        )
        assert result["diagram_svg"] == "<svg>fallback</svg>"
        assert "textbook_ref" not in result

    @patch("src.agents.diagram_tutor_integration._get_diagram_agent")
    async def test_generation_failure_returns_empty(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.generate.side_effect = Exception("LLM error")
        mock_get_agent.return_value = mock_agent

        result = await generate_tutor_diagram(
            question="draw a cell",
            topic="cells",
            grade_level=10,
            db_session=None,
            retrieved_chunks=[{"metadata": {"source_type": "textbook_diagram"}}],
            diagram_agent=mock_agent,
        )
        assert result == {}

    @patch("src.agents.diagram_tutor_integration._get_diagram_agent")
    async def test_uses_cached_agent_when_none_passed(self, mock_get_agent):
        mock_agent = AsyncMock()
        mock_agent.generate.return_value = {
            "diagram_svg": "<svg>cached</svg>",
            "labels": [],
            "title": "Cells",
        }
        mock_get_agent.return_value = mock_agent

        result = await generate_tutor_diagram(
            question="draw a cell",
            topic="cells",
            grade_level=10,
            db_session=None,
            retrieved_chunks=[{"metadata": {"source_type": "textbook_diagram"}}],
        )
        assert result["diagram_svg"] == "<svg>cached</svg>"
        mock_get_agent.assert_called_once()


class TestCachedDiagramAgent:
    def test_singleton_returns_same_instance(self):
        agent1 = _get_diagram_agent()
        agent2 = _get_diagram_agent()
        assert agent1 is agent2
