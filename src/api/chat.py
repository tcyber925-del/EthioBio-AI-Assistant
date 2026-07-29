import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional, Union

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user
from src.core.conversation.service import ConversationService
from src.database.models import User
from src.database.session import get_session
from src.guardrails.input.conversation_context import ConversationTracker
from src.guardrails.input.prompt_injection import PromptInjectionDetector
from src.guardrails.input.sanitizer import InputSanitizer
from src.schemas.chat import TutorRequest, TutorResponse
from src.schemas.conversation import ConversationRequest
from src.voice.audio import guess_mime_from_bytes, validate_audio_size
from src.voice.gateways import WebVoiceAdapter
from src.voice.providers import speech_registry as _speech_registry
from src.voice.streaming import AudioChunk, VoiceStreamManager

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["Chat"])

input_sanitizer = InputSanitizer()
prompt_injection_detector = PromptInjectionDetector()
conversation_tracker = ConversationTracker()

conversation_service = ConversationService()
_web_adapter = WebVoiceAdapter()
_stream_manager = VoiceStreamManager()


@router.post("")
async def chat_tutor(
    request: TutorRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await handle_chat_request(request, session, current_user)


@router.post("/voice")
async def chat_voice(
    audio: UploadFile = File(...),
    grade_level: Optional[int] = Form(None),
    topic: Optional[str] = Form(None),
    language: str = Form("am"),
    model: Optional[str] = Form(None),
    stream: bool = Form(False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    audio_bytes = await audio.read()
    err = validate_audio_size(audio_bytes)
    if err:
        raise HTTPException(status_code=400, detail=err)

    mime_type = audio.content_type or guess_mime_from_bytes(audio_bytes) or "audio/webm"
    result = await _speech_registry.transcribe(audio_bytes, language=language, mime_type=mime_type)
    transcript = result.text

    if not transcript or not transcript.strip():
        raise HTTPException(status_code=400, detail="Speech recognition returned empty transcript")

    conv_request = ConversationRequest(
        user_id=str(current_user.id),
        conversation_id="",
        session_id="",
        transcript=transcript,
        language=language,
        modality="voice",
        metadata={
            "topic": topic or "",
            "grade_level": grade_level or "",
            "model": model or "",
        },
    )

    if stream:
        return StreamingResponse(
            _voice_stream(conv_request, transcript, session),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    conv_response = await conversation_service.process(conv_request, session)
    return {
        "transcript": transcript,
        "answer": conv_response.answer,
        "model_used": conv_response.model_used,
        "confidence": conv_response.confidence,
        "sources": conv_response.sources,
        "session_id": conv_response.session_id,
        "language": conv_response.language,
    }


@router.post("/voice/chunk")
async def chat_voice_chunk(
    audio: UploadFile = File(...),
    stream_session_id: str = Form(...),
    language: str = Form("am"),
    final: bool = Form(False),
    grade_level: Optional[int] = Form(None),
    topic: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio chunk")

    stream_session = _stream_manager.get_or_create(stream_session_id, language=language)
    mime_type = audio.content_type or guess_mime_from_bytes(audio_bytes) or "audio/webm"

    stream_session.buffer.append(
        AudioChunk(
            data=audio_bytes,
            sequence=stream_session.chunk_count,
            mime_type=mime_type,
            is_final=final,
        )
    )
    stream_session.chunk_count += 1
    stream_session.chunks_since_transcribe += 1
    stream_session.last_activity = datetime.now(timezone.utc)

    result: dict = {}

    transcribe = final or stream_session.chunks_since_transcribe >= 3
    if transcribe:
        try:
            if final:
                audio_data = stream_session.buffer.assemble()
            else:
                audio_data = audio_bytes

            tr = await _speech_registry.transcribe(
                audio_data, language=language, mime_type=mime_type
            )
            text = tr.text.strip() if tr.text else ""
            if text:
                if final:
                    result["final_transcript"] = text
                elif text != stream_session.last_partial:
                    result["partial_transcript"] = text
                    stream_session.last_partial = text
        except Exception as e:
            logger.warning("stream_transcribe_failed", error=str(e))
        stream_session.chunks_since_transcribe = 0

    if final:
        _stream_manager.remove(stream_session_id)

    return result


async def _voice_stream(
    conv_request: ConversationRequest,
    transcript: str,
    session: AsyncSession,
) -> AsyncGenerator[str, None]:
    meta_event = {
        "delta": "",
        "node": "stt",
        "done": False,
        "error": None,
        "status": False,
        "metadata": {"transcript": transcript},
    }
    yield f"data: {json.dumps(meta_event)}\n\n"

    async for line in conversation_service.process_stream(conv_request, session):
        yield line


async def handle_chat_request(
    request: TutorRequest,
    session: AsyncSession,
    current_user: Optional[User] = None,
) -> Union[TutorResponse, StreamingResponse]:
    uid = request.user_id or (current_user.id if current_user else None)
    user_id = str(uid) if uid else ""

    sanitized = _validate_input(request, user_id)
    if sanitized is None:
        raise HTTPException(status_code=400, detail="Message is empty after sanitization")

    request.question = sanitized
    conv_request = _web_adapter.build_request(request)

    if request.stream:
        return StreamingResponse(
            conversation_service.process_stream(conv_request, session),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    conv_response = await conversation_service.process(conv_request, session)
    return _web_adapter.extract_response(conv_response)


class TTSRequest(BaseModel):
    text: str
    language: str = "am"


@router.post("/tts")
async def chat_tts(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")

    result = await _speech_registry.synthesize(request.text, language=request.language)
    return Response(
        content=result.audio_bytes,
        media_type=f"audio/{result.format}",
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "public, max-age=3600",
        },
    )


def _validate_input(request: TutorRequest, user_id: Optional[str]) -> Optional[str]:
    sanitized = input_sanitizer.sanitize(request.question)
    if not input_sanitizer.validate_length(sanitized):
        return None

    inj_result = prompt_injection_detector.check(sanitized)
    if user_id:
        conv_ctx = conversation_tracker.get_or_create(str(user_id))
        multi_turn_conf = conv_ctx.check_multiturn_attack(sanitized)
        conv_ctx.add_turn(sanitized)
    else:
        multi_turn_conf = 0.0

    if inj_result.detected or multi_turn_conf >= 0.7:
        logger.warning(
            "input_guardrail_triggered",
            injection_detected=inj_result.detected,
            injection_pattern=inj_result.pattern_match,
            multi_turn_confidence=multi_turn_conf,
        )
        raise HTTPException(status_code=403, detail="Message blocked by content safety filter")

    return sanitized
