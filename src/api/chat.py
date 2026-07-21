import asyncio
from collections.abc import AsyncGenerator
from typing import Optional, Union

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user
from src.api.gamification import XP_SOURCES, award_xp, check_achievements, update_streak
from src.core.learning_intelligence.tutor.tutor_context_adapter import TutorContextAdapter
from src.core.memory.context_assembler import ContextAssembler
from src.core.memory.cross_session_recall import CrossSessionRecall
from src.core.memory.event_logger import EventLogger
from src.core.memory.session_manager import SessionManager
from src.core.memory.socratic_manager import SocraticManager
from src.database.models import User
from src.database.session import async_session_factory, get_session
from src.graph.orchestrator import run_graph
from src.guardrails.input.conversation_context import ConversationTracker
from src.guardrails.input.prompt_injection import PromptInjectionDetector
from src.guardrails.input.sanitizer import InputSanitizer
from src.guardrails.output import OutputGuardrailRunner
from src.schemas.chat import TutorRequest, TutorResponse
from src.schemas.common import LanguageEnum
from src.schemas.streaming import TokenChunk

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["Chat"])

session_manager = SessionManager()
socratic_manager = SocraticManager()
context_assembler = ContextAssembler()
event_logger = EventLogger()
context_adapter = TutorContextAdapter()

input_sanitizer = InputSanitizer()
prompt_injection_detector = PromptInjectionDetector()
conversation_tracker = ConversationTracker()
output_guardrails = OutputGuardrailRunner()


@router.post("")
async def chat_tutor(
    request: TutorRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await handle_chat_request(request, session, current_user)


async def handle_chat_request(
    request: TutorRequest,
    session: AsyncSession,
    current_user: Optional[User] = None,
) -> Union[TutorResponse, StreamingResponse]:
    if request.stream:
        return await _handle_chat_stream(request, session, current_user)
    return await _handle_chat_blocking(request, session, current_user)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


async def _resolve_language(
    request: TutorRequest,
    user_id: Optional[str],
    session: AsyncSession,
) -> LanguageEnum:
    effective_language = request.language
    if user_id and effective_language == LanguageEnum.EN:
        result = await session.execute(
            select(User.language_preference).where(User.id == user_id)
        )
        db_lang = result.scalar_one_or_none()
        if db_lang and db_lang != "en":
            effective_language = LanguageEnum(db_lang)
    return effective_language


async def _build_context(
    request: TutorRequest,
    user_id: Optional[str],
    effective_language: LanguageEnum,
    session: AsyncSession,
):
    mem_session = None
    socratic_state_rec = None
    conversation_messages: list[dict] = []
    if user_id:
        mem_session = await session_manager.get_or_create_active_session(
            user_id,
            topic=request.topic,
            db=session,
        )
        if mem_session:
            conversation_messages = session_manager.get_messages(mem_session)

        if request.socratic_mode and request.topic and mem_session:
            socratic_state_rec = await socratic_manager.get_state(
                user_id,
                request.topic,
                session,
            )

    memory_context = ""
    if user_id and mem_session:
        memory_context = await context_assembler.assemble(
            user_id=user_id,
            topic=request.topic,
            db=session,
            session_state={
                "active_topic": mem_session.active_topic,
                "tutoring_mode": mem_session.tutoring_mode,
                "educational_context": mem_session.educational_context,
                "unresolved_questions": mem_session.unresolved_questions,
            }
            if mem_session
            else None,
            socratic_state={
                "socratic_stage": socratic_state_rec.socratic_stage,
                "current_focus": socratic_state_rec.current_focus,
                "student_understanding": socratic_state_rec.student_understanding,
                "conceptual_gaps": socratic_state_rec.conceptual_gaps,
            }
            if socratic_state_rec
            else None,
        )

    learner_profile_block = ""
    if user_id:
        try:
            package = await context_adapter.build(
                session,
                user_id,
                current_topic=request.topic,
            )
            learner_profile_block = package.formatted_block
        except Exception:
            logger.warning("tutor_context_build_failed", user_id=str(user_id))

    return (
        mem_session,
        socratic_state_rec,
        conversation_messages,
        memory_context,
        learner_profile_block,
    )


# ---------------------------------------------------------------------------
# Streaming path
# ---------------------------------------------------------------------------

async def _handle_chat_stream(
    request: TutorRequest,
    session: AsyncSession,
    current_user: Optional[User] = None,
) -> StreamingResponse:
    user_id = request.user_id or (current_user.id if current_user else None)

    sanitized = _validate_input(request, user_id)
    if sanitized is None:
        raise HTTPException(status_code=400, detail="Message is empty after sanitization")

    effective_language = await _resolve_language(request, user_id, session)
    ctx = await _build_context(request, user_id, effective_language, session)
    mem_session = ctx[0]
    socratic_state_rec = ctx[1]
    conversation_messages = ctx[2]
    memory_context = ctx[3]
    learner_profile_block = ctx[4]

    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

    # Push immediate status so the user sees something right away
    queue.put_nowait(
        TokenChunk(delta="Analyzing your question...", node="orchestrator", status=True)
    )

    graph_task = asyncio.create_task(
        run_graph(
            user_message=sanitized,
            user_id=user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=effective_language,
            preferred_model=request.model,
            socratic_mode=request.socratic_mode,
            hint_level=request.hint_level,
            reveal_answer=request.reveal_answer,
            session_id=str(mem_session.session_id) if mem_session else None,
            memory_context=memory_context,
            learner_profile_block=learner_profile_block,
            socratic_stage=socratic_state_rec.socratic_stage if socratic_state_rec else "",
            socratic_focus=socratic_state_rec.current_focus if socratic_state_rec else "",
            socratic_understanding=(
                socratic_state_rec.student_understanding if socratic_state_rec else ""
            ),
            socratic_next_question=socratic_state_rec.next_question if socratic_state_rec else "",
            messages=conversation_messages,
            db_session_factory=async_session_factory,
            token_queue=queue,
        )
    )

    return StreamingResponse(
        _stream_events(
            queue,
            graph_task,
            _request=request,
            _session=session,
            _user_id=user_id,
            _mem_session=mem_session,
            _conversation_messages=conversation_messages,
            _socratic_state_rec=socratic_state_rec,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_events(
    queue: asyncio.Queue[TokenChunk | None],
    graph_task: asyncio.Task,
    _request: Optional[TutorRequest] = None,
    _session: Optional[AsyncSession] = None,
    _user_id: Optional[str] = None,
    _mem_session=None,
    _conversation_messages: Optional[list] = None,
    _socratic_state_rec=None,
) -> AsyncGenerator[str, None]:
    try:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            if chunk.error:
                yield f"data: {chunk.model_dump_json()}\n\n"
                break
            if chunk.done:
                # Queue done — graph finished streaming tokens.
                # Don't yield yet; we'll yield our own done:true
                # after persisting history, so the sidebar fetch sees it.
                break
            yield f"data: {chunk.model_dump_json()}\n\n"

        # Await graph task — it may still be running safety/post-processing
        try:
            result = await graph_task
        except Exception as exc:
            yield f"data: {TokenChunk(delta='', done=True, error=str(exc)).model_dump_json()}\n\n"
            return

        # Persist conversation history BEFORE sending done so sidebar refresh sees it
        if _session and _user_id and _mem_session and _request:
            await _persist_chat_history(
                request=_request,
                session=_session,
                user_id=_user_id,
                mem_session=_mem_session,
                conversation_messages=_conversation_messages or [],
                result=result,
                socratic_state_rec=_socratic_state_rec,
            )

        yield f"data: {TokenChunk(
            delta='',
            done=True,
            metadata={
                'model_used': result.model_used,
                'confidence': result.confidence,
                'sources': result.sources,
                'xp_awarded': getattr(result, 'xp_awarded', 0),
                'level_up': getattr(result, 'level_up', False),
                'status': result.status,
            },
        ).model_dump_json()}\n\n"
    except Exception as e:
        yield f"data: {TokenChunk(delta='', done=True, error=str(e)).model_dump_json()}\n\n"


async def _persist_chat_history(
    request: TutorRequest,
    session: AsyncSession,
    user_id: str,
    mem_session,
    conversation_messages: list,
    result,
    socratic_state_rec=None,
) -> None:
    try:
        if request.socratic_mode and request.topic:
            await socratic_manager.update_state(
                user_id=user_id,
                topic=request.topic,
                db=session,
                updates={
                    "socratic_stage": result.socratic_stage,
                    "current_focus": result.socratic_focus,
                    "student_understanding": result.socratic_understanding,
                    "next_question": result.socratic_next_question,
                },
            )

        conversation_messages.append({"role": "user", "content": request.question})
        if result.answer:
            conversation_messages.append({"role": "assistant", "content": result.answer})
        session_manager.set_messages(mem_session, conversation_messages[-20:])

        await session.flush()
        mem_session.unresolved_questions = [
            getattr(result, attr, "")
            for attr in ("guiding_question",)
            if getattr(result, "guiding_question", "")
        ]
        await session_manager.heartbeat(mem_session.session_id, session)

        await event_logger.log(
            user_id,
            "tutor_interaction",
            topic=request.topic,
            db=session,
        )

        await update_streak(user_id, session)
        xp_amount = XP_SOURCES.get("tutor_interaction", 5)
        gam, _, _ = await award_xp(
            user_id,
            "tutor_interaction",
            xp_amount,
            {"question_topic": request.topic or ""},
            session,
        )
        await check_achievements(user_id, gam, session)

        await session.commit()

        # Best-effort: record conversation turns. The FK to memory_sessions
        # may fail in some deployment environments; the sidebar now reads
        # from MemorySession.educational_context.messages as a fallback.
        try:
            turn_factory = async_session_factory()
            async with turn_factory() as turn_session:
                await CrossSessionRecall().record_turns(
                    user_id=user_id,
                    session_id=mem_session.session_id,
                    turns=conversation_messages[-2:],
                    topic=request.topic,
                    db=turn_session,
                )
                await turn_session.commit()
        except Exception as turn_e:
            logger.warning("record_turns_async_error", error=str(turn_e))
    except Exception as e:
        logger.error("stream_chat_history_save_failed", error=str(e))
        await session.rollback()


# ---------------------------------------------------------------------------
# Blocking (non-streaming) path — original behavior
# ---------------------------------------------------------------------------

async def _handle_chat_blocking(
    request: TutorRequest,
    session: AsyncSession,
    current_user: Optional[User] = None,
) -> TutorResponse:
    user_id = request.user_id or (current_user.id if current_user else None)

    sanitized = _validate_input(request, user_id)
    if sanitized is None:
        raise HTTPException(status_code=400, detail="Message is empty after sanitization")

    effective_language = await _resolve_language(request, user_id, session)
    ctx = await _build_context(request, user_id, effective_language, session)
    mem_session = ctx[0]
    socratic_state_rec = ctx[1]
    conversation_messages = ctx[2]
    memory_context = ctx[3]
    learner_profile_block = ctx[4]

    try:
        result = await run_graph(
            user_message=sanitized,
            user_id=user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=effective_language,
            preferred_model=request.model,
            socratic_mode=request.socratic_mode,
            hint_level=request.hint_level,
            reveal_answer=request.reveal_answer,
            session_id=str(mem_session.session_id) if mem_session else None,
            memory_context=memory_context,
            learner_profile_block=learner_profile_block,
            socratic_stage=socratic_state_rec.socratic_stage if socratic_state_rec else "",
            socratic_focus=socratic_state_rec.current_focus if socratic_state_rec else "",
            socratic_understanding=(
                socratic_state_rec.student_understanding if socratic_state_rec else ""
            ),
            socratic_next_question=socratic_state_rec.next_question if socratic_state_rec else "",
            messages=conversation_messages,
            db_session_factory=async_session_factory,
        )

        output_check = output_guardrails.check(result.answer or "", topic=request.topic)
        if output_check.blocked:
            logger.warning("output_guardrail_triggered", reasons=output_check.reasons)
            raise HTTPException(status_code=422, detail="Response blocked by output safety filter")

        if request.socratic_mode and request.topic and user_id:
            await socratic_manager.update_state(
                user_id=user_id,
                topic=request.topic,
                db=session,
                updates={
                    "socratic_stage": result.socratic_stage,
                    "current_focus": result.socratic_focus,
                    "student_understanding": result.socratic_understanding,
                    "next_question": result.socratic_next_question,
                },
            )

        if mem_session:
            conversation_messages.append({"role": "user", "content": request.question})
            if result.answer:
                conversation_messages.append({"role": "assistant", "content": result.answer})
            session_manager.set_messages(mem_session, conversation_messages[-20:])
            await CrossSessionRecall().record_turns(
                user_id=user_id,
                session_id=mem_session.session_id,
                turns=conversation_messages[-2:],
                topic=request.topic,
                db=session,
            )

            mem_session.unresolved_questions = [
                getattr(result, attr, "")
                for attr in ("guiding_question",)
                if getattr(result, "guiding_question", "")
            ]
            await session_manager.heartbeat(mem_session.session_id, session)

        if user_id:
            await event_logger.log(
                user_id,
                "tutor_interaction",
                topic=request.topic,
                db=session,
            )

        diagram_data: dict = {}
        if request.generate_diagram and request.topic and request.grade_level:
            try:
                from src.agents.diagram_tutor_integration import (
                    generate_tutor_diagram,
                )

                diagram_data = await generate_tutor_diagram(
                    question=request.question,
                    topic=request.topic,
                    grade_level=request.grade_level,
                    db_session=session,
                )
            except Exception:
                logger.warning("tutor_diagram_generate_failed")

        xp_awarded = 0
        level_up = False
        new_level = 0
        if user_id:
            await update_streak(user_id, session)
            xp_amount = XP_SOURCES.get("tutor_interaction", 5)
            gam, _, level_up = await award_xp(
                user_id,
                "tutor_interaction",
                xp_amount,
                {"question_topic": request.topic or ""},
                session,
            )
            xp_awarded = xp_amount
            new_level = gam.level if level_up else 0
            await check_achievements(user_id, gam, session)

        await session.commit()

        return TutorResponse(
            answer=result.answer,
            language=effective_language.value
            if hasattr(effective_language, "value")
            else str(effective_language),
            sources=result.sources,
            model_used=result.model_used,
            confidence=result.confidence,
            status=result.status,
            requires_teacher_review=result.requires_teacher_review,
            session_id=result.session_id or "",
            socratic_mode=result.socratic_mode,
            socratic_stage=result.socratic_stage,
            socratic_focus=result.socratic_focus,
            socratic_understanding=result.socratic_understanding,
            socratic_next_question=result.socratic_next_question,
            hint_level=result.hint_level,
            reveal_answer=result.reveal_answer,
            misconception_detected=result.misconception_detected,
            misconception_correction=result.misconception_correction,
            xp_awarded=xp_awarded,
            level_up=level_up,
            new_level=new_level,
            diagram_svg=diagram_data.get("diagram_svg", ""),
            diagram_labels=diagram_data.get("labels", []),
            diagram_title=diagram_data.get("title", ""),
            diagram_textbook_ref=diagram_data.get("textbook_ref", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
