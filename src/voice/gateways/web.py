from __future__ import annotations

from typing import Any

from src.schemas.chat import TutorRequest, TutorResponse
from src.schemas.conversation import ConversationRequest, ConversationResponse

from .base import BaseVoiceAdapter


class WebVoiceAdapter(BaseVoiceAdapter[TutorRequest, TutorResponse]):
    """Adapter between the FastAPI /chat REST endpoint and ConversationService.

    Converts TutorRequest (the REST contract) to ConversationRequest
    and ConversationResponse back to TutorResponse.
    """

    def build_request(self, gateway_input: TutorRequest) -> ConversationRequest:
        metadata: dict[str, Any] = {
            "topic": gateway_input.topic or "",
            "grade_level": gateway_input.grade_level or "",
            "model": gateway_input.model or "",
            "socratic_mode": gateway_input.socratic_mode or False,
            "hint_level": gateway_input.hint_level or 0,
            "reveal_answer": gateway_input.reveal_answer or False,
            "generate_diagram": gateway_input.generate_diagram,
            "use_rag": gateway_input.use_rag,
        }
        if gateway_input.user_id:
            metadata["user_id"] = gateway_input.user_id
        return ConversationRequest(
            user_id=gateway_input.user_id or "",
            conversation_id="",
            session_id=gateway_input.session_id or "",
            transcript=gateway_input.question,
            language=gateway_input.language or "en",
            modality="text",
            metadata=metadata,
        )

    def extract_response(self, response_data: ConversationResponse) -> TutorResponse:
        meta = response_data.metadata or {}
        return TutorResponse(
            answer=response_data.answer,
            sources=response_data.sources,
            model_used=response_data.model_used,
            confidence=response_data.confidence,
            status=response_data.status,
            requires_teacher_review=response_data.requires_teacher_review,
            session_id=response_data.session_id,
            language=response_data.language,
            socratic_mode=meta.get("socratic_mode", False),
            socratic_stage=meta.get("socratic_stage", ""),
            socratic_focus=meta.get("socratic_focus", ""),
            socratic_understanding=meta.get("socratic_understanding", ""),
            socratic_next_question=meta.get("socratic_next_question", ""),
            hint_level=meta.get("hint_level", 0),
            reveal_answer=meta.get("reveal_answer", False),
            misconception_detected=meta.get("misconception_detected", False),
            misconception_correction=meta.get("misconception_correction", ""),
            xp_awarded=meta.get("xp_awarded", 0),
            level_up=meta.get("level_up", False),
            new_level=meta.get("new_level", 0),
            diagram_svg=meta.get("diagram_svg", ""),
            diagram_labels=meta.get("diagram_labels", []),
            diagram_title=meta.get("diagram_title", ""),
            diagram_textbook_ref=meta.get("diagram_textbook_ref", ""),
        )
