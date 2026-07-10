"""Tests for the persistent educational memory module."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.core.memory.event_logger import EventLogger
from src.core.memory.safety import (
    sanitize_summary_content,
    validate_confidence,
    validate_summary_content,
    validate_understanding_level,
)
from src.core.memory.session_manager import SessionManager
from src.core.memory.socratic_manager import SocraticManager
from src.schemas.memory import (
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResult,
    SessionCloseResponse,
    SessionStartRequest,
    SessionStartResponse,
    SummarizeRequest,
    SummarizeResponse,
    SummaryResponse,
)


class TestSafety:
    def test_sanitize_strips_email(self):
        text = "Contact me at student@gmail.com for help"
        result = sanitize_summary_content(text)
        assert "[email]" in result
        assert "student@gmail.com" not in result

    def test_sanitize_strips_ethiopia_phone(self):
        text = "Call +251911123456 for support"
        result = sanitize_summary_content(text)
        assert "[phone]" in result
        assert "+251911123456" not in result

    def test_sanitize_preserves_normal_text(self):
        text = "Student understands cell division well."
        result = sanitize_summary_content(text)
        assert result == text

    def test_sanitize_empty_string(self):
        assert sanitize_summary_content("") == ""

    def test_sanitize_none(self):
        assert sanitize_summary_content(None) == ""

    def test_validate_understanding_level_valid(self):
        for level in ("beginner", "intermediate", "advanced", "mastered"):
            assert validate_understanding_level(level) == level

    def test_validate_understanding_level_invalid_defaults(self):
        assert validate_understanding_level("expert") == "beginner"

    def test_validate_understanding_level_none_defaults(self):
        assert validate_understanding_level(None) == "beginner"

    def test_validate_confidence_clamps_low(self):
        assert validate_confidence(-0.5) == 0.0

    def test_validate_confidence_clamps_high(self):
        assert validate_confidence(1.5) == 1.0

    def test_validate_confidence_mid(self):
        assert validate_confidence(0.75) == 0.75

    def test_validate_summary_content_short(self):
        valid, reason = validate_summary_content("Hi")
        assert not valid
        assert "too short" in reason

    def test_validate_summary_content_ok(self):
        valid, reason = validate_summary_content("Student is doing well in biology class.")
        assert valid
        assert reason == ""


class TestSchemas:
    def test_session_start_request(self):
        user_id = uuid4()
        req = SessionStartRequest(user_id=user_id, topic="Cell Biology", tutoring_mode="socratic")
        assert req.user_id == user_id
        assert req.topic == "Cell Biology"
        assert req.tutoring_mode == "socratic"

    def test_session_start_request_default_mode(self):
        req = SessionStartRequest(user_id=uuid4())
        assert req.tutoring_mode == "direct"

    def test_session_start_request_missing_user_id(self):
        with pytest.raises(ValidationError):
            SessionStartRequest()

    def test_session_start_response(self):
        now = datetime.now(timezone.utc)
        resp = SessionStartResponse(
            session_id=uuid4(),
            user_id=uuid4(),
            active_topic="Genetics",
            tutoring_mode="socratic",
            started_at=now,
            last_active_at=now,
        )
        assert resp.tutoring_mode == "socratic"
        assert resp.active_topic == "Genetics"

    def test_summarize_request(self):
        req = SummarizeRequest(conversation_context="Some conversation text")
        assert req.conversation_context == "Some conversation text"

    def test_summarize_request_default(self):
        req = SummarizeRequest()
        assert req.conversation_context is None

    def test_summarize_response(self):
        resp = SummarizeResponse(
            summary_id=uuid4(),
            topic="Cell Biology",
            understanding_level="advanced",
            key_misconceptions=["m1"],
            confidence=0.85,
            next_learning_goal="Review mitosis",
            created_at=datetime.now(timezone.utc),
        )
        assert resp.understanding_level == "advanced"
        assert resp.confidence == 0.85
        assert len(resp.key_misconceptions) == 1

    def test_session_close_response(self):
        resp = SessionCloseResponse(
            session_id=uuid4(),
            summary="Done",
            closed=True,
        )
        assert resp.closed
        assert resp.summary_detail is None

    def test_memory_search_request(self):
        req = MemorySearchRequest(query="cell division", topic="Biology", n_results=3)
        assert req.query == "cell division"
        assert req.topic == "Biology"
        assert req.n_results == 3

    def test_memory_search_request_defaults(self):
        req = MemorySearchRequest(query="mitosis")
        assert req.n_results == 5
        assert req.topic is None

    def test_memory_search_result(self):
        r = MemorySearchResult(
            memory_id="abc",
            content="some summary",
            metadata={"topic": "Biology"},
            score=0.85,
            similarity=0.9,
        )
        assert r.memory_id == "abc"
        assert r.score == 0.85

    def test_memory_search_response(self):
        resp = MemorySearchResponse(results=[], total=0)
        assert resp.total == 0
        assert len(resp.results) == 0

    def test_summary_response(self):
        resp = SummaryResponse(
            id=uuid4(),
            user_id=uuid4(),
            topic="Biology",
            understanding_level="beginner",
            confidence=0.5,
            created_at=datetime.now(timezone.utc),
        )
        assert resp.topic == "Biology"


class TestSessionManager:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        query_result = MagicMock()
        query_result.scalar_one_or_none.return_value = None
        db.execute.return_value = query_result
        return db

    @pytest.mark.asyncio
    async def test_get_or_create_active_session_creates_new(self, mock_db):
        mgr = SessionManager()
        session = await mgr.get_or_create_active_session(
            user_id=uuid4(),
            topic="Biology",
            db=mock_db,
        )
        assert session is not None
        assert session.active_topic == "Biology"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_returns_none_for_unknown(self, mock_db):
        mgr = SessionManager()
        result = await mgr.get_active_session_for_user(uuid4(), mock_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_heartbeat_updates_timestamp(self):
        mock_db = AsyncMock()
        mock_session = MagicMock()
        mock_db.get.return_value = mock_session

        mgr = SessionManager()
        result = await mgr.heartbeat(uuid4(), mock_db)
        assert result == mock_session
        assert mock_session.last_active_at is not None

    @pytest.mark.asyncio
    async def test_lazy_close_expired_session(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        expired_session = MagicMock()
        expired_session.session_id = uuid4()

        first_call = MagicMock()
        first_call.scalar_one_or_none.return_value = None
        second_call = MagicMock()
        second_call.scalars.return_value.all.return_value = [expired_session]

        mock_db.execute.side_effect = [first_call, second_call]

        mgr = SessionManager()
        closed = []

        async def tracking_close(session_id, db):
            closed.append(session_id)
            return expired_session

        mgr.close_session = tracking_close

        session = await mgr.get_or_create_active_session(
            user_id=uuid4(),
            topic="Biology",
            db=mock_db,
        )
        assert session is not None
        assert len(closed) == 1
        assert closed[0] == expired_session.session_id

    @pytest.mark.asyncio
    async def test_lazy_close_no_expired_session(self):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        first_call = MagicMock()
        first_call.scalar_one_or_none.return_value = None
        second_call = MagicMock()
        second_call.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [first_call, second_call]

        mgr = SessionManager()
        closed = []

        async def tracking_close(session_id, db):
            closed.append(session_id)

        mgr.close_session = tracking_close

        session = await mgr.get_or_create_active_session(
            user_id=uuid4(),
            topic="Genetics",
            db=mock_db,
        )
        assert session is not None
        assert len(closed) == 0


class TestSocraticManager:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        query_result = MagicMock()
        query_result.scalar_one_or_none.return_value = None
        db.execute.return_value = query_result
        return db

    @pytest.mark.asyncio
    async def test_get_state_returns_none_when_missing(self, mock_db):
        mgr = SocraticManager()
        result = await mgr.get_state(user_id=uuid4(), topic="Biology", db=mock_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_state_creates_new(self, mock_db):
        mgr = SocraticManager()
        result = await mgr.update_state(
            user_id=uuid4(),
            topic="Biology",
            db=mock_db,
            updates={"socratic_stage": "guided_discovery"},
        )
        assert result is not None
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_state(self):
        mock_db = AsyncMock()
        mock_state = MagicMock()
        query_result = MagicMock()
        query_result.scalar_one_or_none.return_value = mock_state
        mock_db.execute.return_value = query_result

        mgr = SocraticManager()
        await mgr.clear_state(user_id=uuid4(), topic="Biology", db=mock_db)
        mock_db.delete.assert_called_once_with(mock_state)


class TestEventLogger:
    @pytest.mark.asyncio
    async def test_log_creates_event(self):
        mock_db = AsyncMock()
        logger = EventLogger()
        result = await logger.log(
            user_id=uuid4(),
            event_type="test_event",
            topic="Biology",
            metadata={"key": "val"},
            db=mock_db,
        )
        assert result is not None
        assert result.event_type == "test_event"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_skips_when_no_db(self):
        logger = EventLogger()
        result = await logger.log(user_id=uuid4(), event_type="test_event")
        assert result is None


class TestContextAssembler:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        query_result = MagicMock()
        query_result.scalar_one_or_none.return_value = None
        scalars_result = MagicMock()
        scalars_result.all.return_value = []
        query_result.scalars.return_value = scalars_result
        db.execute.return_value = query_result
        return db

    @pytest.mark.asyncio
    async def test_assemble_empty_when_no_state(self, mock_db):
        from src.core.memory.context_assembler import ContextAssembler

        assembler = ContextAssembler()
        with patch.object(assembler, "_format_summaries", AsyncMock(return_value="")):
            result = await assembler.assemble(
                user_id=uuid4(),
                topic=None,
                db=mock_db,
                session_state=None,
                socratic_state=None,
            )
        assert result == ""

    @pytest.mark.asyncio
    async def test_assemble_with_session_only(self, mock_db):
        from src.core.memory.context_assembler import ContextAssembler

        assembler = ContextAssembler()
        with patch.object(assembler, "_format_summaries", AsyncMock(return_value="")):
            result = await assembler.assemble(
                user_id=uuid4(),
                topic="Cell Biology",
                db=mock_db,
                session_state={
                    "active_topic": "Cell Biology",
                    "tutoring_mode": "socratic",
                    "educational_context": None,
                    "unresolved_questions": [],
                },
                socratic_state=None,
            )
        assert "## Learner Context" in result
        assert "Cell Biology" in result
        assert "socratic" in result

    @pytest.mark.asyncio
    async def test_assemble_with_socratic_state(self, mock_db):
        from src.core.memory.context_assembler import ContextAssembler

        assembler = ContextAssembler()
        with patch.object(assembler, "_format_summaries", AsyncMock(return_value="")):
            result = await assembler.assemble(
                user_id=uuid4(),
                topic="Genetics",
                db=mock_db,
                session_state={
                    "active_topic": "Genetics",
                    "tutoring_mode": "socratic",
                    "educational_context": None,
                    "unresolved_questions": [],
                },
                socratic_state={
                    "socratic_stage": "guided_discovery",
                    "current_focus": "Punnett squares",
                    "student_understanding": "partial",
                    "conceptual_gaps": ["dominant vs recessive"],
                },
            )
        assert "guided_discovery" in result
        assert "Punnett squares" in result

    @pytest.mark.asyncio
    async def test_assemble_drops_excessive_sections(self, mock_db):
        from src.core.memory.context_assembler import (
            ContextAssembler,
        )

        assembler = ContextAssembler()
        with patch.object(assembler, "_format_summaries", AsyncMock(return_value="")):
            moderate_topic = "B" * 400  # ~100 tokens, easily fits SESSION_BUDGET of 200
            result = await assembler.assemble(
                user_id=uuid4(),
                topic=moderate_topic,
                db=mock_db,
                session_state={
                    "active_topic": moderate_topic,
                    "tutoring_mode": "direct",
                    "educational_context": None,
                    "unresolved_questions": [],
                },
                socratic_state=None,
            )
        assert "## Learner Context" in result
        assert "Current Session" in result
