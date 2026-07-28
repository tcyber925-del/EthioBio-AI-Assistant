from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.chat import TutorRequest
from src.schemas.conversation import ConversationRequest, ConversationResponse

TEST_UUID = "550e8400-e29b-41d4-a716-446655440000"


class TestConversationSchemas:
    def test_conversation_request_minimal(self):
        req = ConversationRequest(
            user_id=TEST_UUID,
            conversation_id="conv-1",
            session_id="session-1",
            transcript="What is a cell?",
        )
        assert req.user_id == TEST_UUID
        assert req.transcript == "What is a cell?"
        assert req.modality == "text"
        assert req.language is None

    def test_conversation_request_voice(self):
        req = ConversationRequest(
            user_id=TEST_UUID,
            conversation_id="conv-1",
            session_id="session-1",
            transcript="What is a cell?",
            modality="voice",
            language="am",
            language_confidence=0.92,
            metadata={"topic": "Cell Biology"},
        )
        assert req.modality == "voice"
        assert req.language == "am"
        assert req.language_confidence == 0.92
        assert req.metadata["topic"] == "Cell Biology"

    def test_conversation_request_frozen(self):
        req = ConversationRequest(
            user_id=TEST_UUID, conversation_id="c1", session_id="s1", transcript="hello"
        )
        with pytest.raises(AttributeError):
            req.transcript = "changed"

    def test_conversation_response_minimal(self):
        resp = ConversationResponse(answer="Cells are the basic unit of life.")
        assert resp.answer == "Cells are the basic unit of life."
        assert resp.sources == []
        assert resp.session_id == ""
        assert resp.language == "en"

    def test_conversation_response_full(self):
        resp = ConversationResponse(
            answer="Cells are basic.",
            language="en",
            sources=["src1"],
            model_used="gpt-4",
            confidence=0.95,
            status="approved",
            session_id="sess-1",
            metadata={"xp_awarded": 10},
        )
        assert resp.model_used == "gpt-4"
        assert resp.metadata["xp_awarded"] == 10

    def test_conversation_response_frozen(self):
        resp = ConversationResponse(answer="test")
        with pytest.raises(AttributeError):
            resp.answer = "changed"


class TestTutorRequestToConversationRequest:
    def test_tutor_request_to_conversation_request(self):
        tutor_req = TutorRequest(
            question="What is photosynthesis?",
            grade_level=10,
            topic="Biology",
            language="en",
            socratic_mode=True,
            stream=False,
        )
        conv_req = ConversationRequest(
            user_id=TEST_UUID,
            conversation_id=tutor_req.session_id or "",
            session_id="",
            transcript=tutor_req.question,
            language=tutor_req.language.value if tutor_req.language else None,
            modality="text",
            metadata={
                "topic": tutor_req.topic,
                "grade_level": tutor_req.grade_level,
                "model": tutor_req.model,
                "socratic_mode": tutor_req.socratic_mode,
                "hint_level": tutor_req.hint_level,
                "reveal_answer": tutor_req.reveal_answer,
                "use_rag": tutor_req.use_rag,
                "generate_diagram": tutor_req.generate_diagram,
            },
        )
        assert conv_req.transcript == "What is photosynthesis?"
        assert conv_req.metadata["topic"] == "Biology"
        assert conv_req.metadata["grade_level"] == 10
        assert conv_req.metadata["socratic_mode"] is True
        assert conv_req.user_id == TEST_UUID
        assert conv_req.modality == "text"

    def test_conversation_response_metadata_access(self):
        conv_resp = ConversationResponse(
            answer="Photosynthesis converts light to energy.",
            language="en",
            sources=["textbook-1"],
            model_used="gpt-4",
            confidence=0.94,
            status="approved",
            session_id="sess-1",
            metadata={
                "xp_awarded": 5,
                "level_up": False,
                "diagram_svg": "",
            },
        )
        assert conv_resp.answer == "Photosynthesis converts light to energy."
        assert conv_resp.metadata["xp_awarded"] == 5


@pytest.mark.asyncio
async def test_conversation_service_process_calls_run_graph():
    import src.core.conversation.service as conv_service_module

    with (
        patch.object(conv_service_module, "run_graph", new_callable=AsyncMock) as mock_run_graph,
        patch.object(conv_service_module, "award_xp", return_value=(AsyncMock(), None, False)),
        patch.object(conv_service_module, "check_achievements", new_callable=AsyncMock),
        patch.object(conv_service_module, "update_streak", new_callable=AsyncMock),
    ):
        mock_result = AsyncMock()
        mock_result.answer = "Test answer"
        mock_result.model_used = "test-model"
        mock_result.confidence = 0.9
        mock_result.sources = []
        mock_result.status = "approved"
        mock_result.requires_teacher_review = False
        mock_result.session_id = ""
        mock_result.socratic_mode = False
        mock_result.socratic_stage = ""
        mock_result.socratic_focus = ""
        mock_result.socratic_understanding = ""
        mock_result.socratic_next_question = ""
        mock_result.hint_level = 0
        mock_result.reveal_answer = False
        mock_result.misconception_detected = False
        mock_result.misconception_correction = ""
        mock_run_graph.return_value = mock_result

        mock_xp_gam = AsyncMock()
        mock_xp_gam.level = 1
        mock_run_graph.return_value = mock_result

        service = conv_service_module.ConversationService()
        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = None
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_exec_result)
        mock_session.commit = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.rollback = AsyncMock()

        req = ConversationRequest(
            user_id=TEST_UUID,
            conversation_id="conv-1",
            session_id="session-1",
            transcript="Test question",
        )
        resp = await service.process(req, mock_session)
        assert resp.answer == "Test answer"
        assert resp.model_used == "test-model"
        assert resp.language == "en"
        mock_run_graph.assert_called_once()


@pytest.mark.asyncio
async def test_conversation_service_handles_run_graph_failure():
    import src.core.conversation.service as conv_service_module

    with (
        patch.object(conv_service_module, "run_graph", new_callable=AsyncMock) as mock_run_graph,
        patch.object(conv_service_module, "award_xp"),
        patch.object(conv_service_module, "check_achievements"),
        patch.object(conv_service_module, "update_streak"),
    ):
        from fastapi import HTTPException

        mock_run_graph.side_effect = ValueError("LLM unavailable")

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = None
        service = conv_service_module.ConversationService()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        req = ConversationRequest(
            user_id=TEST_UUID,
            conversation_id="conv-1",
            session_id="session-1",
            transcript="Test question",
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.process(req, mock_session)
        assert exc_info.value.status_code == 500
        mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_chat_request_uses_conversation_service():
    import src.api.chat as chat_module

    with patch.object(chat_module, "conversation_service") as mock_service:
        mock_conv_response = ConversationResponse(
            answer="Mock answer from service",
            language="en",
            metadata={
                "xp_awarded": 5,
                "level_up": False,
            },
        )
        mock_service.process = AsyncMock(return_value=mock_conv_response)

        request = TutorRequest(
            question="What is biology?",
            stream=False,
            language="en",
        )
        mock_session = AsyncMock(spec=AsyncSession)
        result = await chat_module.handle_chat_request(request, mock_session, current_user=None)

        assert result.answer == "Mock answer from service"
        assert result.model_used == ""
        assert result.status == "approved"
        assert result.xp_awarded == 5
        mock_service.process.assert_awaited_once()
