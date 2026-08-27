import asyncio
import base64
from collections.abc import AsyncGenerator
from typing import Optional
from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.gamification import XP_SOURCES, award_xp, check_achievements, update_streak
from src.core.learning_intelligence.tutor.tutor_context_adapter import TutorContextAdapter
from src.core.memory.context_assembler import ContextAssembler
from src.core.memory.cross_session_recall import CrossSessionRecall
from src.core.memory.event_logger import EventLogger
from src.core.memory.session_manager import SessionManager
from src.core.memory.socratic_manager import SocraticManager
from src.database.models import User
from src.database.session import async_session_factory
from src.graph.orchestrator import run_graph
from src.guardrails.input.conversation_context import ConversationTracker
from src.guardrails.input.prompt_injection import PromptInjectionDetector
from src.guardrails.input.sanitizer import InputSanitizer
from src.guardrails.output import OutputGuardrailRunner
from src.schemas.common import LanguageEnum
from src.schemas.conversation import ConversationRequest, ConversationResponse
from src.schemas.streaming import TokenChunk
from src.voice.providers import speech_registry as _speech_registry

logger = structlog.get_logger()

input_sanitizer = InputSanitizer()
prompt_injection_detector = PromptInjectionDetector()
conversation_tracker = ConversationTracker()
output_guardrails = OutputGuardrailRunner()

session_manager = SessionManager()
socratic_manager = SocraticManager()
context_assembler = ContextAssembler()
event_logger = EventLogger()
context_adapter = TutorContextAdapter()


class ConversationService:
    async def process(
        self,
        request: ConversationRequest,
        session: AsyncSession,
    ) -> ConversationResponse:
        metadata = request.metadata or {}
        topic = metadata.get("topic")
        grade_level = metadata.get("grade_level")
        subject = metadata.get("subject")
        model = metadata.get("model")
        socratic_mode = metadata.get("socratic_mode", False)
        hint_level = metadata.get("hint_level", 0)
        reveal_answer = metadata.get("reveal_answer", False)
        generate_diagram = metadata.get("generate_diagram", True)

        effective_language = await self._resolve_language(
            request.language, request.user_id, session
        )
        ctx = await self._build_context(
            user_id=request.user_id,
            topic=topic,
            socratic_mode=socratic_mode,
            session=session,
        )
        mem_session = ctx["mem_session"]
        socratic_state_rec = ctx["socratic_state_rec"]
        conversation_messages = ctx["conversation_messages"]
        memory_context = ctx["memory_context"]
        learner_profile_block = ctx["learner_profile_block"]

        try:
            result = await run_graph(
                user_message=request.transcript,
                user_id=request.user_id,
                grade_level=grade_level,
                subject=subject,
                topic=topic,
                language=effective_language,
                preferred_model=model,
                socratic_mode=socratic_mode,
                hint_level=hint_level,
                reveal_answer=reveal_answer,
                session_id=str(mem_session.session_id) if mem_session else None,
                memory_context=memory_context,
                learner_profile_block=learner_profile_block,
                socratic_stage=socratic_state_rec.socratic_stage if socratic_state_rec else "",
                socratic_focus=socratic_state_rec.current_focus if socratic_state_rec else "",
                socratic_understanding=(
                    socratic_state_rec.student_understanding if socratic_state_rec else ""
                ),
                socratic_next_question=(
                    socratic_state_rec.next_question if socratic_state_rec else ""
                ),
                messages=conversation_messages,
                db_session_factory=async_session_factory,
            )

            output_check = output_guardrails.check(result.answer or "", topic=topic)
            answer_text = output_check.redacted_text or result.answer or ""
            if output_check.blocked:
                raise HTTPException(
                    status_code=422, detail="Response blocked by output safety filter"
                )

            gamification = await self._persist_history(
                user_id=request.user_id,
                transcript=request.transcript,
                answer=answer_text,
                topic=topic,
                socratic_mode=socratic_mode,
                session=session,
                mem_session=mem_session,
                socratic_state_rec=socratic_state_rec,
                conversation_messages=conversation_messages,
                result=result,
            )

            diagram_data = {}
            if generate_diagram and topic and grade_level:
                try:
                    from src.agents.diagram_tutor_integration import generate_tutor_diagram

                    diagram_data = await generate_tutor_diagram(
                        question=request.transcript,
                        topic=topic,
                        grade_level=grade_level,
                        db_session=session,
                    )
                except Exception:
                    logger.warning("tutor_diagram_generate_failed")

            effective_lang = (
                effective_language.value
                if hasattr(effective_language, "value")
                else str(effective_language)
            )
            return ConversationResponse(
                answer=answer_text,
                language=effective_lang,
                sources=result.sources,
                model_used=result.model_used,
                confidence=result.confidence,
                status=result.status,
                requires_teacher_review=result.requires_teacher_review,
                session_id=result.session_id or "",
                metadata={
                    "socratic_mode": result.socratic_mode,
                    "socratic_stage": result.socratic_stage,
                    "socratic_focus": result.socratic_focus,
                    "socratic_understanding": result.socratic_understanding,
                    "socratic_next_question": result.socratic_next_question,
                    "hint_level": result.hint_level,
                    "reveal_answer": result.reveal_answer,
                    "misconception_detected": result.misconception_detected,
                    "misconception_correction": result.misconception_correction,
                    **gamification,
                    "diagram_svg": diagram_data.get("diagram_svg", ""),
                    "diagram_labels": diagram_data.get("labels", []),
                    "diagram_title": diagram_data.get("title", ""),
                    "diagram_textbook_ref": diagram_data.get("textbook_ref", ""),
                },
            )
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.error("conversation_service_error", error=str(e))
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def process_stream(
        self,
        request: ConversationRequest,
        session: AsyncSession,
    ) -> AsyncGenerator[str, None]:
        metadata = request.metadata or {}
        topic = metadata.get("topic")
        grade_level = metadata.get("grade_level")
        subject = metadata.get("subject")
        model = metadata.get("model")
        socratic_mode = metadata.get("socratic_mode", False)
        hint_level = metadata.get("hint_level", 0)
        reveal_answer = metadata.get("reveal_answer", False)

        effective_language = await self._resolve_language(
            request.language, request.user_id, session
        )
        ctx = await self._build_context(
            user_id=request.user_id,
            topic=topic,
            socratic_mode=socratic_mode,
            session=session,
        )
        mem_session = ctx["mem_session"]
        socratic_state_rec = ctx["socratic_state_rec"]
        conversation_messages = ctx["conversation_messages"]
        memory_context = ctx["memory_context"]
        learner_profile_block = ctx["learner_profile_block"]

        queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()
        queue.put_nowait(
            TokenChunk(delta="Analyzing your question...", node="orchestrator", status=True)
        )

        graph_task = asyncio.create_task(
            run_graph(
                user_message=request.transcript,
                user_id=request.user_id,
                grade_level=grade_level,
                subject=subject,
                topic=topic,
                language=effective_language,
                preferred_model=model,
                socratic_mode=socratic_mode,
                hint_level=hint_level,
                reveal_answer=reveal_answer,
                session_id=str(mem_session.session_id) if mem_session else None,
                memory_context=memory_context,
                learner_profile_block=learner_profile_block,
                socratic_stage=socratic_state_rec.socratic_stage if socratic_state_rec else "",
                socratic_focus=socratic_state_rec.current_focus if socratic_state_rec else "",
                socratic_understanding=(
                    socratic_state_rec.student_understanding if socratic_state_rec else ""
                ),
                socratic_next_question=(
                    socratic_state_rec.next_question if socratic_state_rec else ""
                ),
                messages=conversation_messages,
                db_session_factory=async_session_factory,
                token_queue=queue,
            )
        )

        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                if chunk.error:
                    yield f"data: {chunk.model_dump_json()}\n\n"
                    break
                if chunk.done:
                    break
                yield f"data: {chunk.model_dump_json()}\n\n"

            try:
                result = await graph_task
            except Exception as exc:
                chunk = TokenChunk(delta="", done=True, error=str(exc))
                yield f"data: {chunk.model_dump_json()}\n\n"
                return

            gamification = await self._persist_history(
                user_id=request.user_id,
                transcript=request.transcript,
                answer=result.answer,
                topic=topic,
                socratic_mode=socratic_mode,
                session=session,
                mem_session=mem_session,
                socratic_state_rec=socratic_state_rec,
                conversation_messages=conversation_messages,
                result=result,
            )

            final_meta = {
                "model_used": result.model_used,
                "confidence": result.confidence,
                "sources": result.sources,
                **gamification,
                "status": result.status,
            }
            chunk = TokenChunk(delta="", done=True, metadata=final_meta)
            yield f"data: {chunk.model_dump_json()}\n\n"
        except Exception as e:
            chunk = TokenChunk(delta="", done=True, error=str(e))
            yield f"data: {chunk.model_dump_json()}\n\n"
        finally:
            if not graph_task.done():
                graph_task.cancel()
                await asyncio.gather(graph_task, return_exceptions=True)

    async def voice_turn_stream(
        self,
        request: ConversationRequest,
        session: AsyncSession,
    ) -> AsyncGenerator[str, None]:
        """SSE stream: STT metadata → tutor text tokens → TTS audio chunks → final metadata."""
        metadata = request.metadata or {}
        topic = metadata.get("topic")
        grade_level = metadata.get("grade_level")
        subject = metadata.get("subject")
        model = metadata.get("model")
        socratic_mode = metadata.get("socratic_mode", False)
        hint_level = metadata.get("hint_level", 0)
        reveal_answer = metadata.get("reveal_answer", False)

        effective_language = await self._resolve_language(
            request.language, request.user_id, session
        )
        ctx = await self._build_context(
            user_id=request.user_id,
            topic=topic,
            socratic_mode=socratic_mode,
            session=session,
        )
        mem_session = ctx["mem_session"]
        socratic_state_rec = ctx["socratic_state_rec"]
        conversation_messages = ctx["conversation_messages"]
        memory_context = ctx["memory_context"]
        learner_profile_block = ctx["learner_profile_block"]

        queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()
        queue.put_nowait(
            TokenChunk(delta="Analyzing your question...", node="orchestrator", status=True)
        )

        graph_task = asyncio.create_task(
            run_graph(
                user_message=request.transcript,
                user_id=request.user_id,
                grade_level=grade_level,
                subject=subject,
                topic=topic,
                language=effective_language,
                preferred_model=model,
                socratic_mode=socratic_mode,
                hint_level=hint_level,
                reveal_answer=reveal_answer,
                session_id=str(mem_session.session_id) if mem_session else None,
                memory_context=memory_context,
                learner_profile_block=learner_profile_block,
                socratic_stage=socratic_state_rec.socratic_stage if socratic_state_rec else "",
                socratic_focus=socratic_state_rec.current_focus if socratic_state_rec else "",
                socratic_understanding=(
                    socratic_state_rec.student_understanding if socratic_state_rec else ""
                ),
                socratic_next_question=(
                    socratic_state_rec.next_question if socratic_state_rec else ""
                ),
                messages=conversation_messages,
                db_session_factory=async_session_factory,
                token_queue=queue,
            )
        )

        text_buffer: list[str] = []

        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                if chunk.error:
                    yield f"data: {chunk.model_dump_json()}\n\n"
                    return
                if chunk.done:
                    break
                if chunk.delta and not chunk.status:
                    text_buffer.append(chunk.delta)
                yield f"data: {chunk.model_dump_json()}\n\n"

            try:
                result = await graph_task
            except Exception as exc:
                chunk = TokenChunk(delta="", done=True, error=str(exc))
                yield f"data: {chunk.model_dump_json()}\n\n"
                return

            answer_text = "".join(text_buffer).strip()

            try:
                tts_result = await _speech_registry.synthesize(
                    answer_text,
                    language=(
                        effective_language.value
                        if hasattr(effective_language, "value")
                        else str(effective_language)
                    ),
                )
                audio = tts_result.audio_bytes
                chunk_size = 15 * 1024
                for i in range(0, len(audio), chunk_size):
                    b64 = base64.b64encode(audio[i : i + chunk_size]).decode()
                    chunk = TokenChunk(delta="", node="audio", audio_b64=b64)
                    yield f"data: {chunk.model_dump_json()}\n\n"
            except Exception as tts_e:
                logger.warning("voice_turn_tts_failed", error=str(tts_e))

            gamification = await self._persist_history(
                user_id=request.user_id,
                transcript=request.transcript,
                answer=answer_text,
                topic=topic,
                socratic_mode=socratic_mode,
                session=session,
                mem_session=mem_session,
                socratic_state_rec=socratic_state_rec,
                conversation_messages=conversation_messages,
                result=result,
            )

            final_meta = {
                "model_used": result.model_used,
                "confidence": result.confidence,
                "sources": result.sources,
                "session_id": result.session_id,
                **gamification,
                "status": result.status,
            }
            chunk = TokenChunk(delta="", done=True, metadata=final_meta)
            yield f"data: {chunk.model_dump_json()}\n\n"
        except Exception as e:
            chunk = TokenChunk(delta="", done=True, error=str(e))
            yield f"data: {chunk.model_dump_json()}\n\n"
        finally:
            if not graph_task.done():
                graph_task.cancel()
                await asyncio.gather(graph_task, return_exceptions=True)

    async def _resolve_language(
        self,
        language: Optional[str],
        user_id: str,
        session: AsyncSession,
    ) -> LanguageEnum:
        effective_language = LanguageEnum(language) if language else LanguageEnum.EN
        if user_id and effective_language == LanguageEnum.EN:
            result = await session.execute(
                select(User.language_preference).where(User.id == UUID(user_id))
            )
            db_lang = result.scalar_one_or_none()
            if db_lang and db_lang != "en":
                effective_language = LanguageEnum(db_lang)
        return effective_language

    async def _build_context(
        self,
        user_id: Optional[str],
        topic: Optional[str],
        socratic_mode: bool,
        session: AsyncSession,
    ) -> dict:
        mem_session = None
        socratic_state_rec = None
        conversation_messages: list[dict] = []
        memory_context = ""
        learner_profile_block = ""
        uid = UUID(user_id) if user_id else None

        if uid:
            mem_session = await session_manager.get_or_create_active_session(
                uid,
                topic=topic,
                db=session,
            )
            if mem_session:
                conversation_messages = session_manager.get_messages(mem_session)

            if socratic_mode and topic and mem_session:
                socratic_state_rec = await socratic_manager.get_state(uid, topic, session)

        if uid and mem_session:
            memory_context = await context_assembler.assemble(
                user_id=user_id,
                topic=topic,
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

        if uid:
            try:
                package = await context_adapter.build(
                    session,
                    uid,
                    current_topic=topic,
                )
                learner_profile_block = package.formatted_block
            except Exception:
                logger.warning("tutor_context_build_failed", user_id=str(user_id))

        return {
            "mem_session": mem_session,
            "socratic_state_rec": socratic_state_rec,
            "conversation_messages": conversation_messages,
            "memory_context": memory_context,
            "learner_profile_block": learner_profile_block,
        }

    async def _persist_history(
        self,
        user_id: Optional[str],
        transcript: str,
        answer: str,
        topic: Optional[str],
        socratic_mode: bool,
        session: AsyncSession,
        mem_session,
        socratic_state_rec,
        conversation_messages: list,
        result,
    ) -> dict:
        if not (user_id and mem_session):
            return {}
        uid = UUID(user_id)
        gamification = {}
        try:
            if socratic_mode and topic and uid:
                await socratic_manager.update_state(
                    user_id=uid,
                    topic=topic,
                    db=session,
                    updates={
                        "socratic_stage": result.socratic_stage,
                        "current_focus": result.socratic_focus,
                        "student_understanding": result.socratic_understanding,
                        "next_question": result.socratic_next_question,
                    },
                )

            conversation_messages.append({"role": "user", "content": transcript})
            if answer:
                conversation_messages.append({"role": "assistant", "content": answer})
            session_manager.set_messages(mem_session, conversation_messages[-20:])

            await session.flush()
            mem_session.unresolved_questions = [
                getattr(result, attr, "")
                for attr in ("guiding_question",)
                if getattr(result, "guiding_question", "")
            ]
            await session_manager.heartbeat(mem_session.session_id, session)

            if uid:
                await event_logger.log(uid, "tutor_interaction", topic=topic, db=session)

            await update_streak(user_id, session)
            xp_amount = XP_SOURCES.get("tutor_interaction", 5)
            gam, _, level_up = await award_xp(
                user_id,
                "tutor_interaction",
                xp_amount,
                {"question_topic": topic or ""},
                session,
            )
            await check_achievements(user_id, gam, session)
            await session.commit()

            gamification = {
                "xp_awarded": xp_amount,
                "level_up": level_up,
                "new_level": gam.level if level_up else 0,
            }

            try:
                turn_factory = async_session_factory()
                async with turn_factory() as turn_session:
                    await CrossSessionRecall().record_turns(
                        user_id=user_id,
                        session_id=mem_session.session_id,
                        turns=conversation_messages[-2:],
                        topic=topic,
                        db=turn_session,
                    )
                    await turn_session.commit()
            except Exception as turn_e:
                logger.warning("record_turns_async_error", error=str(turn_e))
        except Exception as e:
            logger.error("persist_history_failed", error=str(e))
            await session.rollback()

        return gamification
