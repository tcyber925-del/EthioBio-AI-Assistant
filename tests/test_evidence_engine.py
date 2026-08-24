import pytest

from src.core.teacher_copilot.evidence_engine import EvidenceEngine


class TestEvidenceEngine:
    def test_format_citations_empty(self):
        result = EvidenceEngine.format_citations([])
        assert result == "No evidence available."

    def test_format_citations_mastery_record(self):
        evidence = [
            {
                "source": "mastery_record",
                "confidence": 0.7,
                "content": {"topic": "Cell Biology", "score": 0.45},
            }
        ]
        result = EvidenceEngine.format_citations(evidence)
        assert "Cell Biology" in result
        assert "mastery score: 0.45" in result
        assert "confidence: 70%" in result

    def test_format_citations_quiz_attempt(self):
        evidence = [
            {
                "source": "quiz_attempt",
                "confidence": 0.8,
                "content": {"score": 6, "total": 10, "percent": 60.0},
            }
        ]
        result = EvidenceEngine.format_citations(evidence)
        assert "Quiz score: 6/10" in result
        assert "60.0%" in result

    def test_format_citations_memory_event(self):
        evidence = [
            {
                "source": "memory_event",
                "confidence": 0.6,
                "content": {"event_type": "quiz_completed", "metadata": {"key": "val"}},
            }
        ]
        result = EvidenceEngine.format_citations(evidence)
        assert "quiz_completed" in result
        assert "confidence: 60%" in result

    def test_format_citations_unknown_source(self):
        evidence = [
            {
                "source": "custom_source",
                "confidence": 0.5,
                "content": {"custom": "data"},
            }
        ]
        result = EvidenceEngine.format_citations(evidence)
        assert "custom_source" in result

    def test_multiple_entries_numbered(self):
        evidence = [
            {
                "source": "mastery_record",
                "confidence": 0.7,
                "content": {"topic": "Genetics", "score": 0.8},
            },
            {
                "source": "quiz_attempt",
                "confidence": 0.9,
                "content": {"score": 9, "total": 10, "percent": 90.0},
            },
        ]
        result = EvidenceEngine.format_citations(evidence)
        assert "[1]" in result
        assert "[2]" in result
        assert result.index("[1]") < result.index("[2]")

    def test_mastery_missing_fields_shows_question_mark(self):
        evidence = [
            {
                "source": "mastery_record",
                "confidence": 0.7,
                "content": {},
            }
        ]
        result = EvidenceEngine.format_citations(evidence)
        assert "Topic '?'" in result


@pytest.mark.asyncio
async def test_get_quiz_evidence_orders_by_started_at_and_reports_stored_percent():
    import uuid
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    engine = EvidenceEngine()
    row = SimpleNamespace(quiz_id=uuid.uuid4(), score=80.0, total=10)
    result_mock = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = [row]
    result_mock.scalars.return_value = scalars
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    evidence = await engine._get_quiz_evidence(uuid.uuid4(), session)

    stmt = session.execute.await_args.args[0]
    assert "started_at DESC" in str(stmt)
    assert evidence[0]["content"]["percent"] == 80.0
