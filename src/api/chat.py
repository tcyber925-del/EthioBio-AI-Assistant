import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.gamification import XP_SOURCES, award_xp, check_achievements, update_streak
from src.core.learning_intelligence.tutor.tutor_context_adapter import TutorContextAdapter
from src.core.memory.context_assembler import ContextAssembler
from src.core.memory.cross_session_recall import CrossSessionRecall
from src.core.memory.session_manager import SessionManager
from src.database.models import User
from src.database.session import async_session_factory, get_session
from src.graph.orchestrator import run_graph
from src.guardrails.input.conversation_context import ConversationTracker
from src.guardrails.input.prompt_injection import PromptInjectionDetector
from src.guardrails.input.sanitizer import InputSanitizer
from src.guardrails.output import OutputGuardrailRunner
from src.schemas.chat import TutorRequest, TutorResponse
from src.schemas.common import LanguageEnum

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["Chat"])

session_manager = SessionManager()
context_assembler = ContextAssembler()
context_adapter = TutorContextAdapter()

input_sanitizer = InputSanitizer()
prompt_injection_detector = PromptInjectionDetector()
conversation_tracker = ConversationTracker()
output_guardrails = OutputGuardrailRunner()


@router.post("", response_model=TutorResponse)
async def chat_tutor(request: TutorRequest, session: AsyncSession = Depends(get_session)):
    # Input guardrails — sanitize, injection detect, conversation context
    sanitized = input_sanitizer.sanitize(request.question)
    if not input_sanitizer.validate_length(sanitized):
        raise HTTPException(status_code=400, detail="Message is empty after sanitization")

    inj_result = prompt_injection_detector.check(sanitized)
    if request.user_id:
        conv_ctx = conversation_tracker.get_or_create(str(request.user_id))
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

    effective_language = request.language
    if request.user_id and effective_language == LanguageEnum.EN:
        result = await session.execute(
            select(User.language_preference).where(User.id == request.user_id)
        )
        db_lang = result.scalar_one_or_none()
        if db_lang and db_lang != "en":
            effective_language = LanguageEnum(db_lang)

    try:
        mem_session = None
        memory_context = ""
        conversation_messages: list[dict] = []
        if request.user_id:
            mem_session = await session_manager.get_or_create_active_session(
                request.user_id,
                topic=request.topic,
                db=session,
            )
            if mem_session:
                memory_context = await context_assembler.assemble(
                    user_id=request.user_id,
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
                    socratic_state=None,
                )
                conversation_messages = session_manager.get_messages(mem_session)

        learner_profile_block = ""
        if request.user_id:
            try:
                package = await context_adapter.build(
                    session,
                    request.user_id,
                    current_topic=request.topic,
                )
                learner_profile_block = package.formatted_block
            except Exception:
                logger.warning("tutor_context_build_failed", user_id=str(request.user_id))

        result = await run_graph(
            user_message=sanitized,
            user_id=request.user_id,
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
            messages=conversation_messages,
            db_session_factory=async_session_factory,
        )

        output_check = output_guardrails.check(result.answer or "", topic=request.topic)
        if output_check.blocked:
            logger.warning("output_guardrail_triggered", reasons=output_check.reasons)
            raise HTTPException(status_code=422, detail="Response blocked by output safety filter")

        if mem_session:
            conversation_messages.append({"role": "user", "content": request.question})
            if result.answer:
                conversation_messages.append({"role": "assistant", "content": result.answer})
            session_manager.set_messages(mem_session, conversation_messages[-20:])
            await CrossSessionRecall().record_turns(
                user_id=request.user_id,
                session_id=mem_session.session_id,
                turns=conversation_messages[-2:],
                topic=request.topic,
                db=session,
            )

        diagram_data: dict = {}
        if request.topic and request.grade_level:
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
        if request.user_id:
            await update_streak(request.user_id, session)
            xp_amount = XP_SOURCES.get("tutor_interaction", 5)
            gam, _, level_up = await award_xp(
                request.user_id,
                "tutor_interaction",
                xp_amount,
                {"question_topic": request.topic or ""},
                session,
            )
            xp_awarded = xp_amount
            new_level = gam.level if level_up else 0
            await check_achievements(request.user_id, gam, session)
        return TutorResponse(
            answer=result.answer,
            language=effective_language.value
            if hasattr(effective_language, "value")
            else str(effective_language),
            sources=result.sources,
            model_used=result.model_used,
            confidence=result.confidence,
            socratic_mode=result.socratic_mode,
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
    except Exception as e:
        logger.error("chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
