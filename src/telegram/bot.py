import asyncio
import html
import random
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.agents.diagram import DiagramAgent
from src.agents.lesson_planner import LessonPlannerAgent
from src.agents.quiz import QuizAgent
from src.api.gamification import award_xp, check_achievements, update_streak
from src.config import settings
from src.core.conversation.service import ConversationService as _ConversationService
from src.core.learning_intelligence.tutor.tutor_context_adapter import TutorContextAdapter
from src.core.memory.context_assembler import ContextAssembler
from src.core.memory.cross_session_recall import CrossSessionRecall
from src.core.memory.session_manager import SessionManager
from src.database.models import (
    MemorySession,
    NotificationPreference,
    ParentChild,
    ProgressRecord,
    QuizAttempt,
    StudentMastery,
    StudentProfile,
    User,
    UserGamification,
    UserRole,
)
from src.database.session import async_session_factory
from src.graph.orchestrator import run_graph
from src.llm.router import ModelRouter
from src.redis_client import get_redis
from src.schemas.conversation import ConversationRequest
from src.schemas.streaming import TokenChunk
from src.telegram.formatter import format_for_telegram, sanitize_for_telegram, strip_markdown
from src.telegram.i18n import t
from src.telegram.keyboards import (
    answer_options_keyboard,
    back_keyboard,
    grade_keyboard,
    hint_keyboard,
    language_keyboard,
    lesson_features_keyboard,
    main_menu_keyboard,
    model_providers_keyboard,
    provider_models_keyboard,
    quiz_next_keyboard,
    quiz_result_keyboard,
    quiz_type_keyboard,
    subject_keyboard,
    teacher_tools_keyboard,
    tf_keyboard,
)
from src.telegram.quiz_voice import handle_quiz_voice_answer
from src.telegram.voice_handler import handle_voice_message
from src.utils.svg_render import render_svg_to_png
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

logger = structlog.get_logger()
conversation_service = _ConversationService()


def _api_client(**kwargs):
    headers = kwargs.pop("headers", {})
    if settings.internal_api_key:
        headers.setdefault("X-API-Key", settings.internal_api_key)
    return httpx.AsyncClient(headers=headers, **kwargs)


(
    TUTOR,
    QUIZ_TYPE,
    QUIZ_GRADE,
    QUIZ_TOPIC,
    QUIZ_ANSWERING,
    LESSON_GRADE,
    LESSON_FEATURES,
    LESSON_TOPIC,
    TUTOR_GRADE,
    DIAGRAM_GRADE,
    DIAGRAM_TOPIC,
    LINK_OTP,
    COPILOT,
    TUTOR_SUBJECT,
    QUIZ_SUBJECT,
    LESSON_SUBJECT,
    DIAGRAM_SUBJECT,
) = range(17)


async def _db_try(action, fallback=None):
    import asyncio

    try:
        return await asyncio.wait_for(action(), timeout=5.0)
    except Exception as e:
        logger.warning("db_skipped", error=str(e))
        return fallback


def _lang(context) -> str:
    return context.user_data.get("language", "en")


async def _try_register_user(telegram_id: int):
    from sqlalchemy import select

    async def _register():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                user = User(
                    telegram_id=telegram_id, role=UserRole.student, language_preference="en"
                )
                session.add(user)
                await session.flush()
                profile = StudentProfile(user_id=user.id)
                session.add(profile)
                await session.commit()

    await _db_try(_register)


async def _set_user_subject(telegram_id: int, subject: str):
    from sqlalchemy import select

    async def _update():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if user:
                user.subject = subject
                await session.commit()

    await _db_try(_update)


async def start(update: Update, context):
    await _try_register_user(update.effective_user.id)
    if "language" not in context.user_data:
        async def _load_lang():
            from sqlalchemy import select

            from src.database.models import User

            factory = async_session_factory()
            async with factory() as session:
                result = await session.execute(
                    select(User.language_preference).where(
                        User.telegram_id == update.effective_user.id
                    )
                )
                row = result.scalar_one_or_none()
                if row:
                    context.user_data["language"] = row

        await _db_try(_load_lang)
    if "subject" not in context.user_data:

        async def _load_subject():
            from sqlalchemy import select

            factory = async_session_factory()
            async with factory() as session:
                result = await session.execute(
                    select(User.subject).where(
                        User.telegram_id == update.effective_user.id
                    )
                )
                row = result.scalar_one_or_none()
                if row:
                    context.user_data["subject"] = row

        await _db_try(_load_subject)
        context.user_data.setdefault("subject", "biology")
    socratic = context.user_data.get("socratic_mode", False)
    await update.message.reply_text(
        t("start.welcome", _lang(context)),
        reply_markup=main_menu_keyboard(socratic, language=_lang(context)),
    )


async def dashboard_login_command(update: Update, context):
    await _try_register_user(update.effective_user.id)
    user_id = str(update.effective_user.id)
    code = f"{random.randint(100000, 999999)}"
    redis_conn = await get_redis()
    await redis_conn.setex(f"otp:{user_id}", 300, code)
    await update.message.reply_text(
        t("start.dashboard_login", _lang(context), code=code),
        parse_mode="HTML",
    )


async def register_parent(update: Update, context):
    email = (context.args[0] if context.args else "").strip().lower()
    if not email:
        await update.message.reply_text(
            t("parent.usage", _lang(context)),
            parse_mode="HTML",
        )
        return

    async def _link():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(User).where(
                    User.email == email,
                    User.role == UserRole.parent,
                    User.is_active.is_(True),
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                await update.message.reply_text(t("parent.no_account", _lang(context)))
                return
            if user.telegram_id and user.telegram_id != update.effective_user.id:
                await update.message.reply_text(t("parent.already_linked", _lang(context)))
                return
            user.telegram_id = update.effective_user.id
            await session.commit()
            await update.message.reply_text(t("parent.linked", _lang(context)))

    await _db_try(_link)


async def list_children(update: Update, context):
    telegram_id = update.effective_user.id

    async def _fetch():
        factory = async_session_factory()
        async with factory() as session:
            user_result = await session.execute(
                select(User).where(
                    User.telegram_id == telegram_id,
                    User.is_active.is_(True),
                )
            )
            user = user_result.scalar_one_or_none()
            if not user or user.role != UserRole.parent:
                await update.message.reply_text(t("parent.need_register", _lang(context)))
                return

            children_result = await session.execute(
                select(User)
                .join(ParentChild, User.id == ParentChild.student_id)
                .where(ParentChild.parent_id == user.id)
            )
            children = list(children_result.scalars().all())

            if not children:
                await update.message.reply_text(t("parent.no_children", _lang(context)))
                return

            keyboard = []
            lines = [f"<b>{t('parent.your_children', _lang(context))}</b>\n"]
            for child in children:
                profile_result = await session.execute(
                    select(StudentProfile).where(StudentProfile.user_id == child.id)
                )
                profile = profile_result.scalar_one_or_none()
                grade = child.grade_level or (profile.grade_level if profile else None)
                name = child.email or f"Student {str(child.id)[:8]}"
                lines.append(f"👤 {name} {f'(Grade {grade})' if grade else ''}")
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"🔍 {name}",
                            callback_data=f"parent_child_{child.id}",
                        )
                    ]
                )
            keyboard.append(
                [InlineKeyboardButton(t("back_to_menu", _lang(context)), callback_data="menu")]
            )

            await update.message.reply_text(
                "\n".join(lines),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    await _db_try(_fetch)


async def _send_child_progress(session, child_id, telegram_id, update, query=None, context=None):
    child_result = await session.execute(select(User).where(User.id == child_id))
    child = child_result.scalar_one_or_none()
    if not child:
        text = t("parent.no_student", _lang(context))
        (query.edit_message_text if query else update.message.reply_text)(text)
        return

    data = await fetch_progress_overview(child.id, session)
    gam = data["gam"]
    recent_quizzes = data["recent_quizzes"]
    mastery_records = data["mastery_records"]

    score = (
        sum((q.score or 0.0) for q in recent_quizzes) / len(recent_quizzes)
        if recent_quizzes
        else 0.0
    )

    name = child.email or f"Student {str(child.id)[:8]}"
    lines = [f"<b>📚 {name}'s Progress</b>\n"]
    lines.append(f"🎯 Readiness: {score:.0f}%")
    lines.append(f"🔥 Streak: {gam.current_streak if gam else 0} days")
    lines.append(f"💎 XP: {gam.total_xp if gam else 0}\n")

    if mastery_records:
        lines.append("<b>Topic Mastery:</b>")
        for m in mastery_records[:5]:
            lines.append(f"• {m.topic}: {m.average_score:.0f}%")
        lines.append("")

    if recent_quizzes:
        lines.append("<b>Recent Quizzes:</b>")
        for q in recent_quizzes:
            pct = q.score or 0.0
            dt = q.completed_at or q.started_at
            date_str = dt.strftime("%b %d") if dt else "recent"
            lines.append(f"• Quiz — {pct:.0f}% ({date_str})")

    keyboard = [
        [
            InlineKeyboardButton(
                t("parent.weekly_summary", _lang(context)),
                callback_data=f"parent_summary_{child.id}",
            )
        ],
        [InlineKeyboardButton(t("parent.back_children", _lang(context)), callback_data="children")],
    ]
    reply = "\n".join(lines)
    if query:
        await query.edit_message_text(
            reply, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            reply, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def handle_parent_child_progress(update: Update, context):
    query = update.callback_query
    await query.answer()
    child_id = query.data.replace("parent_child_", "")

    async def _fetch():
        factory = async_session_factory()
        async with factory() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            parent = user_result.scalar_one_or_none()
            if not parent:
                await query.edit_message_text(t("parent.no_parent", _lang(context)))
                return

            ownership = await session.execute(
                select(ParentChild).where(
                    ParentChild.parent_id == parent.id,
                    ParentChild.student_id == child_id,
                )
            )
            if not ownership.scalar_one_or_none():
                await query.edit_message_text(t("parent.no_child", _lang(context)))
                return

            await _send_child_progress(
                session, child_id, update.effective_user.id, update, query, context
            )

    await _db_try(_fetch)


async def child_progress(update: Update, context):
    telegram_id = update.effective_user.id

    async def _fetch():
        factory = async_session_factory()
        async with factory() as session:
            user_result = await session.execute(
                select(User).where(
                    User.telegram_id == telegram_id,
                    User.is_active.is_(True),
                )
            )
            user = user_result.scalar_one_or_none()
            if not user or user.role != UserRole.parent:
                await update.message.reply_text(t("parent.need_register", _lang(context)))
                return

            children_result = await session.execute(
                select(User)
                .join(ParentChild, User.id == ParentChild.student_id)
                .where(ParentChild.parent_id == user.id)
            )
            children = list(children_result.scalars().all())

            if not children:
                await update.message.reply_text(t("parent.no_children_short", _lang(context)))
                return

            if len(children) == 1:
                await _send_child_progress(
                    session, str(children[0].id), telegram_id, update, context=context
                )
                return

            keyboard = []
            lines = [f"<b>{t('parent.your_children', _lang(context))}</b>\n"]
            for child in children:
                name = child.email or f"Student {str(child.id)[:8]}"
                grade = child.grade_level or ""
                lines.append(f"👤 {name} {f'(Grade {grade})' if grade else ''}")
                keyboard.append(
                    [InlineKeyboardButton(f"🔍 {name}", callback_data=f"parent_child_{child.id}")]
                )
            keyboard.append([InlineKeyboardButton("← Back to Menu", callback_data="menu")])

            await update.message.reply_text(
                "\n".join(lines),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    await _db_try(_fetch)


async def handle_parent_summary(update: Update, context):
    query = update.callback_query
    await query.answer()
    child_id = query.data.replace("parent_summary_", "")

    async def _fetch():
        factory = async_session_factory()
        async with factory() as session:
            user_result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            parent = user_result.scalar_one_or_none()
            if not parent:
                await query.edit_message_text(t("parent.no_parent", _lang(context)))
                return

            ownership = await session.execute(
                select(ParentChild).where(
                    ParentChild.parent_id == parent.id,
                    ParentChild.student_id == child_id,
                )
            )
            if not ownership.scalar_one_or_none():
                await query.edit_message_text(t("parent.no_child", _lang(context)))
                return

            child_result = await session.execute(select(User).where(User.id == child_id))
            child = child_result.scalar_one_or_none()
            if not child:
                await query.edit_message_text(t("parent.no_student", _lang(context)))
                return

            profile_result = await session.execute(
                select(StudentProfile).where(StudentProfile.user_id == child.id)
            )
            profile = profile_result.scalar_one_or_none()

            week_end = datetime.now(timezone.utc)
            week_start = week_end - timedelta(days=7)

            records_result = await session.execute(
                select(ProgressRecord).where(
                    ProgressRecord.student_id == child.id,
                    ProgressRecord.created_at >= week_start,
                    ProgressRecord.created_at <= week_end,
                )
            )
            records = list(records_result.scalars().all())

            from src.agents.parent_summary import ParentSummaryAgent
            from src.llm.router import ModelRouter

            agent = ParentSummaryAgent(ModelRouter())
            summary = await agent.generate_summary(
                student_name=child.email or "Student",
                grade_level=child.grade_level,
                records=records,
                profile=profile,
                week_start=week_start,
                week_end=week_end,
                language="en",
                session=session,
            )

            text = f"<b>Weekly Summary</b>\n\n{summary['summary_text']}"
            if summary.get("summary_amharic"):
                text += f"\n\n———\n{summary['summary_amharic']}"

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                t("parent.back_progress", _lang(context)),
                                callback_data=f"parent_child_{child_id}",
                            )
                        ],
                    ]
                ),
            )

    await _db_try(_fetch)


async def handle_children_back(update: Update, context):
    query = update.callback_query
    await query.answer()
    await list_children(update, context)


async def help_command(update: Update, context):
    await update.message.reply_text(
        t("help.text", _lang(context)),
        reply_markup=main_menu_keyboard(
            context.user_data.get("socratic_mode", False), language=_lang(context)
        ),
    )


async def cancel(update: Update, context):
    context.user_data.clear()
    await update.message.reply_text(
        t("common.cancelled", _lang(context)),
        reply_markup=main_menu_keyboard(language=_lang(context)),
    )
    return ConversationHandler.END


async def grade_command(update: Update, context):
    args = context.args
    if args and args[0].isdigit():
        grade = int(args[0])
        if 7 <= grade <= 12:
            context.user_data["grade_level"] = grade
            await update.message.reply_text(t("grade.set", _lang(context), grade=grade))
            return
    await update.message.reply_text(
        t("grade.usage", _lang(context)),
        reply_markup=main_menu_keyboard(
            context.user_data.get("socratic_mode", False), language=_lang(context)
        ),
    )


async def subject_command(update: Update, context):
    await update.message.reply_text(
        t("subject.command", _lang(context)),
        reply_markup=subject_keyboard("subject", language=_lang(context)),
    )


async def handle_subject(update: Update, context):
    query = update.callback_query
    await query.answer()
    code = query.data.split("_", 1)[1]
    lang = _lang(context)
    context.user_data["subject"] = code
    await _set_user_subject(update.effective_user.id, code)
    label = t(f"subject.{code}", lang)
    if code == "biology":
        await query.edit_message_text(t("subject.set", lang, subject=label))
    else:
        await query.edit_message_text(
            t("subject.set", lang, subject=label)
            + "\n\n"
            + t("subject.coming_soon_reply", lang, subject=label)
        )


async def language_command(update: Update, context):
    args = context.args
    lang_map = {"en": "English", "am": "Amharic", "both": "Bilingual"}
    if args and args[0] in lang_map:
        context.user_data["language"] = args[0]
        await update.message.reply_text(
            t("language.set_cmd", _lang(context), name=lang_map[args[0]])
        )
    else:
        await update.message.reply_text(
            t("language.usage", _lang(context)),
            reply_markup=language_keyboard(language=_lang(context)),
        )


async def reveal_command(update: Update, context):
    question = context.user_data.get("ask_question", "")
    if not question:
        await update.message.reply_text(
            t("tutor.no_question", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )
        return
    hint_level = context.user_data.get("hint_level", 0)
    context.user_data["reveal_answer"] = True
    await update.message.reply_text(t("tutor.revealing_answer", _lang(context)))
    try:
        telegram_id = update.effective_user.id if update.effective_user else None
        async with async_session_factory()() as _mem_db:
            memory_user_id, memory_session_id, memory_context, conversation_messages = (
                await _build_memory_context(
                    telegram_id,
                    context.user_data.get("tutor_grade") or context.user_data.get("grade_level"),
                    _mem_db,
                )
                if telegram_id
                else (None, None, "", [])
            )

            result = await run_graph(
                user_message=question,
                user_id=memory_user_id,
                grade_level=context.user_data.get("grade_level"),
                subject=context.user_data.get("tutor_subject") or context.user_data.get("subject"),
                language=context.user_data.get("language", "en"),
                socratic_mode=False,
                hint_level=hint_level,
                reveal_answer=True,
                memory_context=memory_context,
                messages=conversation_messages,
                db_session_factory=async_session_factory,
            )

            if memory_user_id and memory_session_id:
                try:
                    mem_session = (
                        await _mem_db.execute(
                            select(MemorySession).where(
                                MemorySession.session_id == memory_session_id
                            )
                        )
                    ).scalar_one_or_none()
                    if mem_session:
                        conversation_messages.append({"role": "user", "content": question})
                        conversation_messages.append(
                            {"role": "assistant", "content": result.answer}
                        )
                        SessionManager().set_messages(mem_session, conversation_messages[-20:])
                        await CrossSessionRecall().record_turns(
                            user_id=memory_user_id,
                            session_id=mem_session.session_id,
                            turns=conversation_messages[-2:],
                            topic=mem_session.active_topic,
                            db=_mem_db,
                        )
                        await _mem_db.commit()
                except Exception as e:
                    logger.warning("memory_turns_save_error", error=str(e))

        attempt_msg = (
            t("tutor.hint_usage", _lang(context), count=hint_level) if hint_level > 0 else ""
        )
        response = result.answer + attempt_msg
        await _reply_long(
            update.message,
            response,
            reply_markup=hint_keyboard(hint_level, True, language=_lang(context)),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("reveal_command_error", error=str(e))
        await update.message.reply_text(
            t("common.error", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )


async def socratic_command(update: Update, context):
    current = context.user_data.get("socratic_mode", False)
    context.user_data["socratic_mode"] = not current
    await update.message.reply_text(
        t(
            "tutor.socratic_on" if context.user_data["socratic_mode"] else "tutor.socratic_off",
            _lang(context),
        ),
        reply_markup=main_menu_keyboard(
            context.user_data["socratic_mode"], language=_lang(context)
        ),
    )


async def hint_command(update: Update, context):
    hint_level = context.user_data.get("hint_level", 0)
    reveal = context.user_data.get("reveal_answer", False)
    if reveal:
        await update.message.reply_text(
            t("tutor.hint_revealed", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )
        return
    next_level = hint_level + 1
    if next_level > 3:
        await update.message.reply_text(
            t("tutor.hint_exhausted", _lang(context)),
            reply_markup=hint_keyboard(hint_level, reveal, language=_lang(context)),
        )
        return
    context.user_data["hint_level"] = next_level
    question = context.user_data.get("ask_question", "")
    if not question:
        await update.message.reply_text(
            t("tutor.no_question", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )
        return
    await update.message.reply_text(t("tutor.hint_level", _lang(context), level=next_level))
    try:
        telegram_id = update.effective_user.id if update.effective_user else None
        async with async_session_factory()() as _mem_db:
            memory_user_id, memory_session_id, memory_context, conversation_messages = (
                await _build_memory_context(
                    telegram_id,
                    context.user_data.get("tutor_grade") or context.user_data.get("grade_level"),
                    _mem_db,
                )
                if telegram_id
                else (None, None, "", [])
            )

            learner_profile_block = (
                await _build_learner_profile(memory_user_id, _mem_db) if memory_user_id else ""
            )
            result = await run_graph(
                user_message=question,
                user_id=memory_user_id,
                grade_level=context.user_data.get("grade_level"),
                subject=context.user_data.get("subject"),
                language=context.user_data.get("language", "en"),
                socratic_mode=False,
                hint_level=hint_level,
                reveal_answer=False,
                memory_context=memory_context,
                learner_profile_block=learner_profile_block,
                messages=conversation_messages,
                db_session_factory=async_session_factory,
            )

        if memory_user_id and memory_session_id:
            try:
                mem_session = (
                    await _mem_db.execute(
                        select(MemorySession).where(MemorySession.session_id == memory_session_id)
                    )
                ).scalar_one_or_none()
                if mem_session:
                    conversation_messages.append({"role": "user", "content": question})
                    conversation_messages.append({"role": "assistant", "content": result.answer})
                    SessionManager().set_messages(mem_session, conversation_messages[-20:])
                    await CrossSessionRecall().record_turns(
                        user_id=memory_user_id,
                        session_id=mem_session.session_id,
                        turns=conversation_messages[-2:],
                        topic=mem_session.active_topic,
                        db=_mem_db,
                    )
                    await _mem_db.commit()
            except Exception as e:
                logger.warning("memory_turns_save_error", error=str(e))

        response = result.answer
        if result.misconception_detected:
            response += t("tutor.misconception", _lang(context))
        await _reply_long(
            update.message,
            response,
            reply_markup=hint_keyboard(next_level, False, language=_lang(context)),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("hint_command_error", error=str(e))
        await update.message.reply_text(
            t("common.error", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )


async def ask_command(update: Update, context):
    question = " ".join(context.args) if context.args else ""
    if question:
        context.user_data["ask_question"] = question
        context.user_data["hint_level"] = 0
        context.user_data["reveal_answer"] = False
        await update.message.reply_text(t("common.thinking", _lang(context)))
        try:
            telegram_id = update.effective_user.id if update.effective_user else None
            user_id = ""
            if telegram_id:
                async with async_session_factory()() as _lookup_db:
                    result = await _lookup_db.execute(
                        select(User).where(User.telegram_id == telegram_id)
                    )
                    user = result.scalar_one_or_none()
                    if user:
                        user_id = str(user.id)

            conv_request = ConversationRequest(
                user_id=user_id,
                conversation_id="",
                session_id="",
                transcript=question,
                language=context.user_data.get("language", "en"),
                modality="text",
                metadata={
                    "topic": context.user_data.get("tutor_grade")
                    or context.user_data.get("grade_level"),
                    "grade_level": context.user_data.get("grade_level"),
                    "socratic_mode": context.user_data.get("socratic_mode", False),
                    "hint_level": 0,
                    "reveal_answer": False,
                },
            )

            async with async_session_factory()() as _mem_db:
                conv_response = await conversation_service.process(conv_request, _mem_db)

            response = conv_response.answer
            meta = conv_response.metadata or {}

            if meta.get("misconception_detected"):
                response += t("tutor.misconception", _lang(context))
            if conv_response.sources:
                response += t(
                    "tutor.sources", _lang(context), sources=", ".join(conv_response.sources[:3])
                )
            if telegram_id:
                await _save_tutor_rewards(telegram_id, context)
                xp_awarded = meta.get("xp_awarded", 0)
                level_up = meta.get("level_up", False)
                if xp_awarded:
                    response += t("gamification.xp_earned", _lang(context), xp=xp_awarded)
                if level_up:
                    new_level = meta.get("new_level", 1)
                    response += t("gamification.level_up", _lang(context), level=new_level)
                notifications = context.user_data.pop("last_notifications", None)
                if notifications:
                    response += "\n\n" + "\n".join(notifications)
            socratic = context.user_data.get("socratic_mode", False)
            reply_markup = (
                hint_keyboard(0, False, language=_lang(context))
                if socratic
                else main_menu_keyboard(socratic, language=_lang(context))
            )
            await _reply_long(
                update.message, response, reply_markup=reply_markup, parse_mode="HTML"
            )
        except Exception as e:
            logger.error("ask_command_error", error=str(e))
            await update.message.reply_text(
                t("common.error", _lang(context)),
                reply_markup=main_menu_keyboard(
                    context.user_data.get("socratic_mode", False), language=_lang(context)
                ),
            )
    else:
        await update.message.reply_text(
            t("common.usage_ask", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )


async def quiz_command(update: Update, context):
    args = context.args
    grade = context.user_data.get("grade_level", 10)
    topic = "Science"
    if args:
        if args[0].isdigit():
            grade = int(args[0])
            topic = " ".join(args[1:]) if args[1:] else topic
        else:
            topic = " ".join(args)
    if 7 <= grade <= 12:
        context.user_data["quiz_grade"] = grade
        await update.message.reply_text(
            t("quiz.quiz_type_prompt", _lang(context)),
            reply_markup=quiz_type_keyboard(language=_lang(context)),
        )
        return QUIZ_TYPE
    else:
        await update.message.reply_text(
            t("quiz.usage", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )
        return ConversationHandler.END


async def menu(update: Update, context):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            logger.warning("menu_ans_fail", user_id=update.effective_user.id, exc_info=True)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            logger.warning("menu_edit_fail", user_id=update.effective_user.id, exc_info=True)
        msg = query.message
    else:
        msg = update.message
    await msg.reply_text(
        t("common.choose_option", _lang(context)),
        reply_markup=main_menu_keyboard(
            context.user_data.get("socratic_mode", False), language=_lang(context)
        ),
    )
    if not query:
        return ConversationHandler.END


async def _get_user_role(telegram_id: int) -> str | None:
    async def _fetch():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            return user.role.value if user else None

    return await _db_try(_fetch)


async def handle_teacher_tools(update: Update, context):
    query = update.callback_query
    await query.answer()
    role = await _get_user_role(update.effective_user.id)
    if role != "teacher":
        await query.message.reply_text(t("copilot.not_linked", _lang(context)))
        return
    await query.message.reply_text(
        t("common.teacher_tools", _lang(context)),
        reply_markup=teacher_tools_keyboard(language=_lang(context)),
    )


async def handle_open_quizzes(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        t("quiz.teacher_list", _lang(context), dashboard_url=settings.dashboard_url),
        reply_markup=teacher_tools_keyboard(language=_lang(context)),
    )


async def handle_open_dashboard(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        t("quiz.teacher_dashboard", _lang(context), dashboard_url=settings.dashboard_url),
        reply_markup=teacher_tools_keyboard(language=_lang(context)),
    )


async def handle_tutor(update: Update, context):
    if update.callback_query:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            logger.warning("tutor_ans_fail", user_id=update.effective_user.id, exc_info=True)
        await query.message.reply_text(
            t("tutor.grade_select", _lang(context)),
            reply_markup=grade_keyboard("tutor_grade", language=_lang(context)),
        )
    else:
        await update.message.reply_text(
            t("tutor.grade_select", _lang(context)),
            reply_markup=grade_keyboard("tutor_grade", language=_lang(context)),
        )
    return TUTOR_GRADE


async def handle_tutor_grade(update: Update, context):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        logger.warning("tutor_grade_ans_fail", user_id=update.effective_user.id, exc_info=True)
    grade = int(query.data.split("_")[-1])
    context.user_data["tutor_grade"] = grade
    await query.edit_message_text(
        t("tutor.subject_prompt", _lang(context), grade=grade),
        reply_markup=subject_keyboard("tutor_subject", language=_lang(context)),
    )
    return TUTOR_SUBJECT


async def handle_tutor_subject(update: Update, context):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        logger.warning("tutor_subject_ans_fail", user_id=update.effective_user.id, exc_info=True)
    code = query.data.split("_")[-1]
    context.user_data["tutor_subject"] = code
    await query.edit_message_text(
        t("tutor.grade_prompt", _lang(context), grade=context.user_data.get("tutor_grade")),
        reply_markup=back_keyboard(language=_lang(context)),
    )
    return TUTOR


async def end_conversation(update: Update, context):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        logger.warning("end_conv_ans_fail", user_id=update.effective_user.id, exc_info=True)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        logger.warning("end_conv_edit_fail", user_id=update.effective_user.id, exc_info=True)
    await query.message.reply_text(
        t("common.choose_option", _lang(context)),
        reply_markup=main_menu_keyboard(
            context.user_data.get("socratic_mode", False), language=_lang(context)
        ),
    )
    return ConversationHandler.END


async def _build_memory_context(telegram_id: int, topic: str | None, db):
    """Look up user, create/get active session, build memory context."""
    topic = str(topic) if topic is not None else None
    session_mgr = SessionManager()
    assembler = ContextAssembler()
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        return None, None, "", []
    mem_session = await session_mgr.get_or_create_active_session(
        user.id,
        topic=topic,
        db=db,
    )
    ctx = await assembler.assemble(
        user_id=user.id,
        topic=topic,
        db=db,
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
    messages = session_mgr.get_messages(mem_session) if mem_session else []
    return user.id, mem_session.session_id if mem_session else None, ctx, messages


_context_adapter = TutorContextAdapter()


async def _build_learner_profile(user_id, db):
    try:
        package = await _context_adapter.build(db, user_id)
        return package.formatted_block
    except Exception:
        logger.warning("learner_profile_build_failed", user_id=user_id, exc_info=True)
        return ""


async def handle_question(update: Update, context):
    question = update.message.text
    context.user_data["ask_question"] = question
    context.user_data["hint_level"] = 0
    context.user_data["reveal_answer"] = False
    thinking_msg = await update.message.reply_text(t("common.thinking", _lang(context)))

    result = None
    memory_user_id = None
    memory_session_id = None
    memory_context = None
    conversation_messages = []
    try:
        telegram_id = update.effective_user.id if update.effective_user else None
        async with async_session_factory()() as _mem_db:
            if telegram_id:
                (
                    memory_user_id,
                    memory_session_id,
                    memory_context,
                    conversation_messages,
                ) = await _build_memory_context(
                    telegram_id,
                    context.user_data.get("tutor_grade") or context.user_data.get("grade_level"),
                    _mem_db,
                )

            socratic = context.user_data.get("socratic_mode", False)
            hint_level = context.user_data.get("hint_level", 0)
            reveal = context.user_data.get("reveal_answer", False)
            learner_profile_block = (
                await _build_learner_profile(memory_user_id, _mem_db) if memory_user_id else ""
            )

            token_queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

            graph_task = asyncio.create_task(
                run_graph(
                    user_message=question,
                    user_id=memory_user_id,
                    grade_level=context.user_data.pop("tutor_grade", None)
                    or context.user_data.get("grade_level"),
                    subject=context.user_data.get("tutor_subject")
                    or context.user_data.get("subject"),
                    language=context.user_data.get("language", "en"),
                    socratic_mode=socratic,
                    hint_level=hint_level,
                    reveal_answer=reveal,
                    memory_context=memory_context or "",
                    learner_profile_block=learner_profile_block,
                    messages=conversation_messages,
                    db_session_factory=async_session_factory,
                    token_queue=token_queue,
                )
            )

            response = await _stream_and_edit(
                thinking_msg,
                token_queue,
                graph_task,
                parse_mode="HTML",
            )

            result = await graph_task

            if response and not result.answer:
                result.answer = response

            if memory_user_id and memory_session_id:
                try:
                    mem_session = (
                        await _mem_db.execute(
                            select(MemorySession).where(
                                MemorySession.session_id == memory_session_id
                            )
                        )
                    ).scalar_one_or_none()
                    if mem_session:
                        conversation_messages.append({"role": "user", "content": question})
                        conversation_messages.append(
                            {"role": "assistant", "content": result.answer}
                        )
                        SessionManager().set_messages(mem_session, conversation_messages[-20:])
                        await CrossSessionRecall().record_turns(
                            user_id=memory_user_id,
                            session_id=mem_session.session_id,
                            turns=conversation_messages[-2:],
                            topic=mem_session.active_topic,
                            db=_mem_db,
                        )
                        await _mem_db.commit()
                except Exception as e:
                    logger.warning("memory_turns_save_error", error=str(e))

        if result.misconception_detected:
            response += t("tutor.misconception", _lang(context))
        if result.sources:
            response += t("tutor.sources", _lang(context), sources=", ".join(result.sources[:3]))
        telegram_id = update.effective_user.id if update.effective_user else None
        if telegram_id:
            await _save_tutor_rewards(telegram_id, context)
            xp_awarded = context.user_data.get("last_xp_awarded", 0)
            level_up = context.user_data.get("last_level_up", False)
            if xp_awarded:
                response += t("gamification.xp_earned", _lang(context), xp=xp_awarded)
            if level_up:
                new_level = context.user_data.get("last_new_level", 1)
                response += t("gamification.level_up", _lang(context), level=new_level)
            notifications = context.user_data.pop("last_notifications", None)
            if notifications:
                response += "\n\n" + "\n".join(notifications)
        reply_markup = (
            hint_keyboard(hint_level, reveal, language=_lang(context))
            if socratic
            else main_menu_keyboard(socratic, language=_lang(context))
        )
        try:
            display = sanitize_for_telegram(format_for_telegram(response))[:4096]
            await thinking_msg.edit_text(display, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            logger.warning("final_edit_failed", user_id=update.effective_user.id, exc_info=True)

        diagram_keywords = frozenset(
            [
                "diagram",
                "draw",
                "label",
                "structure",
                "parts",
                "organ",
                "cell",
                "heart",
                "flower",
                "photosynthesis",
                "mitosis",
                "meiosis",
                "dna",
                "chromosome",
                "neuron",
                "eye",
                "ear",
                "leaf",
                "flower",
            ]
        )
        if any(kw in question.lower() for kw in diagram_keywords):
            try:
                from src.agents.diagram_tutor_integration import (
                    generate_tutor_diagram,
                )
                from src.utils.svg_render import render_svg_to_png
                from telegram import InputFile

                tutor_grade = context.user_data.get("tutor_grade") or context.user_data.get(
                    "grade_level"
                )
                diagram_data = await generate_tutor_diagram(
                    question=question,
                    topic=question,
                    grade_level=tutor_grade,
                    db_session=None,
                )
                if diagram_data.get("diagram_svg"):
                    png_bytes = render_svg_to_png(diagram_data["diagram_svg"], 800, 600)
                    await update.message.reply_photo(
                        photo=InputFile(png_bytes, filename="diagram.png"),
                        caption=f"📐 {diagram_data.get('diagram_title', diagram_data.get('title', ''))}",  # noqa: E501
                    )
            except Exception as e:
                logger.warning("tutor_diagram_bot_failed", error=str(e)[:200])
    except Exception as e:
        logger.error("tutor_error", error=str(e))
        try:
            await thinking_msg.edit_text(
                t("common.error_try_again", _lang(context)),
                reply_markup=main_menu_keyboard(
                    context.user_data.get("socratic_mode", False), language=_lang(context)
                ),
            )
        except Exception:
            logger.warning(
                "error_edit_failed",
                user_id=update.effective_user.id if update.effective_user else None,
                exc_info=True,
            )
        return ConversationHandler.END

    if memory_user_id:
        from src.database.models import MessageThread

        async def _save():
            factory = async_session_factory()
            async with factory() as session:
                session.add(
                    MessageThread(
                        user_id=memory_user_id,
                        channel="telegram",
                        messages=[
                            {"role": "user", "content": question},
                            {"role": "assistant", "content": result.answer},
                        ],
                        topic=context.user_data.get("tutor_subject")
                        or context.user_data.get("subject", "biology"),
                    )
                )
                await session.commit()

        await _db_try(_save)

    return ConversationHandler.END


async def handle_quiz_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        t("quiz.quiz_type_prompt", _lang(context)),
        reply_markup=quiz_type_keyboard(language=_lang(context)),
    )
    return QUIZ_TYPE


async def handle_quiz_type(update: Update, context):
    query = update.callback_query
    await query.answer()
    type_map = {
        "quiztype_mc": "multiple_choice",
        "quiztype_tf": "true_false",
        "quiztype_mixed": "mixed",
    }
    context.user_data["quiz_type"] = type_map.get(query.data, "multiple_choice")
    await query.edit_message_text(
        t("quiz.grade_prompt", _lang(context)),
        reply_markup=grade_keyboard("quiz_grade", language=_lang(context)),
    )
    return QUIZ_GRADE


async def handle_quiz_grade(update: Update, context):
    query = update.callback_query
    await query.answer()
    grade = int(query.data.split("_")[-1])
    context.user_data["quiz_grade"] = grade
    await query.edit_message_text(
        t("quiz.subject_prompt", _lang(context), grade=grade),
        reply_markup=subject_keyboard("quiz_subject", language=_lang(context)),
    )
    return QUIZ_SUBJECT


async def handle_quiz_subject(update: Update, context):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        logger.warning("quiz_subject_ans_fail", user_id=update.effective_user.id, exc_info=True)
    code = query.data.split("_")[-1]
    context.user_data["quiz_subject"] = code
    await query.edit_message_text(
        t("quiz.topic_prompt", _lang(context), grade=context.user_data.get("quiz_grade")),
        reply_markup=back_keyboard(language=_lang(context)),
    )
    return QUIZ_TOPIC


async def handle_quiz_topic(update: Update, context):
    topic = update.message.text
    grade = context.user_data.get("quiz_grade", 10)
    qtype = context.user_data.get("quiz_type", "multiple_choice")
    types = qtype.split("_") if qtype == "mixed" else [qtype]
    msg = await update.message.reply_text(t("quiz.generating", _lang(context)))

    try:
        router_llm = ModelRouter()
        agent = QuizAgent(llm_router=router_llm)
        result = await agent.generate(
            grade_level=grade,
            topic=topic,
            question_count=5,
            types=types,
            subject=context.user_data.get("quiz_subject") or context.user_data.get("subject"),
        )

        if not result.get("questions"):
            await msg.edit_text(t("quiz.generate_failed", _lang(context)))
            await router_llm.close()
            return ConversationHandler.END

        context.user_data["quiz_session"] = {
            "questions": result["questions"],
            "current": 0,
            "answers": [],
            "correct": 0,
            "total": len(result["questions"]),
            "grade": grade,
            "topic": topic,
            "title": result.get("title", f"Grade {grade} - {topic}"),
        }
        await router_llm.close()
        await _send_quiz_question(update, context, msg)

    except Exception as e:
        logger.error("quiz_error", error=str(e))
        await update.message.reply_text(
            t("quiz.error", _lang(context)),
            reply_markup=main_menu_keyboard(language=_lang(context)),
        )
        return ConversationHandler.END

    return QUIZ_ANSWERING


STREAM_FLUSH_INTERVAL = 0.4
STREAM_TIMEOUT = 120.0


async def _stream_and_edit(
    msg,
    token_queue: asyncio.Queue[TokenChunk | None],
    graph_task: asyncio.Task,
    final_markup=None,
    parse_mode=None,
):
    """Read tokens from queue and progressively update the Telegram message.

    Exits when:
    - done:true received from the graph (normal completion)
    - graph task fails (exception raised during streaming)
    - overall STREAM_TIMEOUT reached (safety valve)
    """
    buffer = ""
    last_edit = ""
    last_update = 0.0
    done = False
    start = asyncio.get_event_loop().time()

    while True:
        if asyncio.get_event_loop().time() - start > STREAM_TIMEOUT:
            logger.warning("stream_timeout_reached")
            break

        try:
            chunk = await asyncio.wait_for(token_queue.get(), timeout=STREAM_FLUSH_INTERVAL)
        except asyncio.TimeoutError:
            chunk = None

        now = asyncio.get_event_loop().time()

        if chunk is not None:
            if chunk.error:
                buffer += f"\n\n❌ {chunk.error}"
                done = True
            elif chunk.done:
                done = True
            elif not chunk.status:
                buffer += chunk.delta

        should_flush = done or (buffer != last_edit and now - last_update >= STREAM_FLUSH_INTERVAL)

        if should_flush and buffer and buffer != last_edit:
            try:
                display = sanitize_for_telegram(format_for_telegram(buffer))[:4096]
                await msg.edit_text(display, parse_mode=parse_mode)
            except Exception:
                logger.warning("stream_flush_edit_failed", exc_info=True)
            last_edit = buffer
            last_update = now

        if done or (chunk is None and buffer != last_edit):
            break

        # If the graph task failed while we were waiting, no more tokens will come
        if chunk is None and graph_task.done() and graph_task.exception() is not None:
            logger.warning("stream_aborted_graph_failed")
            break

    # Flush any remaining text
    try:
        display = sanitize_for_telegram(format_for_telegram(buffer))[:4096]
        await msg.edit_text(display, reply_markup=final_markup, parse_mode=parse_mode)
    except Exception:
        logger.warning("stream_final_flush_edit_failed", exc_info=True)

    return buffer


async def _reply_long(
    update_or_msg_or_query,
    text: str,
    reply_markup=None,
    parse_mode=None,
    max_len: int = 4096,
    force_new=False,
):
    """Split text into chunks and send as multiple messages if needed."""
    html_text = sanitize_for_telegram(format_for_telegram(text)) if parse_mode == "HTML" else text
    plain_text = strip_markdown(text) if parse_mode == "HTML" else text

    for i in range(0, len(html_text), max_len):
        chunk = html_text[i : i + max_len]
        plain_chunk = plain_text[i : i + max_len] if parse_mode == "HTML" else chunk
        if i == 0:
            if not force_new and hasattr(update_or_msg_or_query, "edit_text"):
                try:
                    await update_or_msg_or_query.edit_text(
                        chunk, reply_markup=reply_markup, parse_mode=parse_mode
                    )
                    continue
                except Exception:
                    logger.warning("reply_long_edit_failed", exc_info=True)
            try:
                await update_or_msg_or_query.reply_text(
                    chunk, reply_markup=reply_markup, parse_mode=parse_mode
                )
            except Exception as e:
                if "parse" in str(e).lower():
                    logger.warning("html_parse_failed", error=str(e))
                    await update_or_msg_or_query.reply_text(plain_chunk, reply_markup=reply_markup)
                else:
                    raise
        else:
            try:
                await update_or_msg_or_query.reply_text(chunk, parse_mode=parse_mode)
            except Exception as e:
                if "parse" in str(e).lower():
                    logger.warning("html_parse_failed", error=str(e))
                    await update_or_msg_or_query.reply_text(plain_chunk)
                else:
                    raise


async def _send_quiz_question(update: Update, context, msg=None, new_message=False):
    session = context.user_data.get("quiz_session", {})
    qs = session.get("questions", [])
    idx = session.get("current", 0)
    if idx >= len(qs):
        await _show_quiz_result(update, context)
        return

    q = qs[idx]
    qtype = q.get("question_type", "multiple_choice")
    text = t(
        "quiz.question",
        _lang(context),
        title=session.get("title", "Quiz"),
        current=idx + 1,
        total=session.get("total", len(qs)),
        qtype=qtype.replace("_", " "),
        qtext=q["question_text"],
    )

    if qtype == "multiple_choice" and q.get("options"):
        letters = ["A", "B", "C", "D", "E", "F"]
        opt_lines = []
        for i, opt in enumerate(q["options"]):
            if i < len(letters):
                opt_lines.append(f"{letters[i]}) {opt.split(') ')[-1]}")
        text += "\n\n" + "\n".join(opt_lines)

    reply_markup = None
    if qtype == "true_false" or qtype == "true/false":
        reply_markup = tf_keyboard(language=_lang(context))
    elif q.get("options"):
        reply_markup = answer_options_keyboard(q["options"], language=_lang(context))
    elif qtype == "short_answer":
        text += t("quiz.short_answer", _lang(context))
        reply_markup = quiz_next_keyboard(language=_lang(context))
    else:
        reply_markup = quiz_next_keyboard(language=_lang(context))

    if msg:
        await _reply_long(
            msg, text, reply_markup=reply_markup, parse_mode="HTML", force_new=new_message
        )
    else:
        await _reply_long(
            update.effective_message, text, reply_markup=reply_markup, parse_mode="HTML"
        )


def _calculate_quiz_xp(pct: int) -> int:
    xp = 10
    if pct >= 80:
        xp += 10
    if pct >= 100:
        xp += 15
    return xp


async def _fetch_recovery_notifications(user_id, session):
    from sqlalchemy import select

    from src.database.models import RecoveryNotification

    result = await session.execute(
        select(RecoveryNotification)
        .where(
            RecoveryNotification.user_id == user_id,
            RecoveryNotification.is_read.is_(False),
        )
        .order_by(RecoveryNotification.created_at.desc())
        .limit(5)
    )
    return list(result.scalars().all())


async def _format_notification_messages(notifications):
    messages = []
    for n in notifications:
        icon = (
            "📈"
            if n.event_type == "mastery_improvement"
            else "🎯"
            if n.event_type == "severity_upgrade"
            else "🎉"
        )
        messages.append(f"{icon} {n.message}")
    return messages


async def _save_quiz_rewards(telegram_id, correct, total, context):
    from sqlalchemy import select

    async def _save():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            pct = round(correct / max(total, 1) * 100)
            xp_amount = _calculate_quiz_xp(pct)
            meta = {"correct": correct, "total": total, "source": "telegram_bot"}
            gam_result, _, level_up = await award_xp(
                user.id, "quiz_completion", xp_amount, meta, session
            )
            await update_streak(user.id, session)
            await check_achievements(user.id, gam_result, session)
            await session.commit()
            context.user_data["last_xp_awarded"] = xp_amount
            context.user_data["last_level_up"] = level_up
            context.user_data["last_new_level"] = gam_result.level
            notifications = await _fetch_recovery_notifications(user.id, session)
            if notifications:
                context.user_data["last_notifications"] = await _format_notification_messages(
                    notifications
                )

    await _db_try(_save)


async def _save_tutor_rewards(telegram_id, context):
    from sqlalchemy import select

    from src.api.gamification import XP_SOURCES

    async def _save():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            xp_amount = XP_SOURCES.get("tutor_interaction", 5)
            meta = {"source": "telegram_bot"}
            gam_result, _, level_up = await award_xp(
                user.id, "tutor_interaction", xp_amount, meta, session
            )
            await update_streak(user.id, session)
            await check_achievements(user.id, gam_result, session)
            await session.commit()
            context.user_data["last_xp_awarded"] = xp_amount
            context.user_data["last_level_up"] = level_up
            context.user_data["last_new_level"] = gam_result.level
            notifications = await _fetch_recovery_notifications(user.id, session)
            if notifications:
                context.user_data["last_notifications"] = await _format_notification_messages(
                    notifications
                )

    await _db_try(_save)


async def _show_quiz_result(update: Update, context, msg=None):
    session = context.user_data.get("quiz_session", {})
    correct = session.get("correct", 0)
    total = session.get("total", 0)
    pct = round(correct / max(total, 1) * 100)
    qs = session.get("questions", [])
    ans = session.get("answers", [])

    telegram_id = update.effective_user.id if update.effective_user else None
    if telegram_id:
        await _save_quiz_rewards(telegram_id, correct, total, context)

    xp_awarded = context.user_data.get("last_xp_awarded", _calculate_quiz_xp(pct))
    level_up = context.user_data.pop("last_level_up", False)
    lines = [t("quiz.complete", _lang(context), correct=correct, total=total, pct=pct)]
    if xp_awarded:
        lines.append(t("gamification.xp_quiz", _lang(context), xp=xp_awarded))
    if level_up:
        new_level = context.user_data.get("last_new_level", 1)
        lines.append(t("gamification.level_up_quiz", _lang(context), level=new_level))
    notifications = context.user_data.pop("last_notifications", None)
    if notifications:
        lines.append("")
        lines.extend(notifications)
    lines.append("")
    for i, q in enumerate(qs):
        icon = "✅" if i < len(ans) and ans[i] == q.get("correct_answer", "") else "❌"
        lines.append(f"{icon} Q{i + 1}: {q.get('question_text', '')[:50]}")
    text = "\n".join(lines)

    dest = msg or update.effective_message
    reply_markup = quiz_result_keyboard(language=_lang(context))
    try:
        from sqlalchemy import select

        from src.database.models import RecoveryPlan

        telegram_id = update.effective_user.id if update.effective_user else None
        if telegram_id:
            factory = async_session_factory()
            async with factory() as session:
                result = await session.execute(select(User).where(User.telegram_id == telegram_id))
                user = result.scalar_one_or_none()
                if user:
                    plans_result = await session.execute(
                        select(RecoveryPlan)
                        .where(
                            RecoveryPlan.user_id == user.id,
                            RecoveryPlan.status == "active",
                        )
                        .limit(1)
                    )
                    plan = plans_result.scalar_one_or_none()
                    if plan:
                        from telegram import InlineKeyboardButton

                        recovery_row = [
                            InlineKeyboardButton(
                                t("view_recovery", _lang(context)), callback_data="recovery_view"
                            )
                        ]
                        from telegram import InlineKeyboardMarkup

                        new_buttons = list(reply_markup.inline_keyboard) + [tuple(recovery_row)]
                        reply_markup = InlineKeyboardMarkup(new_buttons)
    except Exception:
        logger.warning(
            "quiz_recovery_plan_fail",
            user_id=update.effective_user.id if update.effective_user else None,
            exc_info=True,
        )
    await dest.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def handle_quiz_answer(update: Update, context):
    query = update.callback_query
    await query.answer()
    session = context.user_data.get("quiz_session", {})
    qs = session.get("questions", [])
    idx = session.get("current", 0)

    if idx >= len(qs):
        await _show_quiz_result(update, context)
        return ConversationHandler.END

    q = qs[idx]
    selected = query.data.replace("ans_", "")
    correct_answer = q.get("correct_answer", "")

    is_correct = False
    if q.get("question_type") == "multiple_choice" and q.get("options"):
        letters = ["A", "B", "C", "D", "E", "F"]
        try:
            opt_idx = letters.index(selected)
            chosen = q["options"][opt_idx]
            chosen_text = chosen.split(") ")[-1] if ") " in chosen else chosen
            correct_text = (
                correct_answer.split(") ")[-1] if ") " in correct_answer else correct_answer
            )
            is_correct = chosen_text.strip().lower() == correct_text.strip().lower()
        except (ValueError, IndexError):
            is_correct = False
    else:
        is_correct = selected.strip().lower() == correct_answer.strip().lower()

    session["answers"].append(selected)
    if is_correct:
        session["correct"] += 1
    session["current"] += 1

    if is_correct:
        feedback = t("quiz.correct", _lang(context))
    else:
        feedback = t("quiz.wrong", _lang(context), answer=correct_answer)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        logger.warning("quiz_ans_edit_fail", user_id=update.effective_user.id, exc_info=True)
    await query.message.reply_text(
        f"{feedback}\n\n{_get_explanation(q)}",
        reply_markup=quiz_next_keyboard(language=_lang(context)),
        parse_mode="HTML",
    )
    return QUIZ_ANSWERING


def _get_explanation(q: dict) -> str:
    exp = q.get("explanation", "")
    if exp:
        return f"<i>{exp[:200]}</i>"
    return ""


async def handle_quiz_short_answer(update: Update, context):
    session = context.user_data.get("quiz_session", {})
    qs = session.get("questions", [])
    idx = session.get("current", 0)

    if idx >= len(qs):
        await _show_quiz_result(update, context)
        return ConversationHandler.END

    q = qs[idx]
    qtype = q.get("question_type", "")

    if qtype != "short_answer":
        msg = "Please use the buttons below to answer."
        if q.get("options"):
            await update.message.reply_text(
                msg, reply_markup=answer_options_keyboard(q["options"], language=_lang(context))
            )
        else:
            await update.message.reply_text(msg)
        return QUIZ_ANSWERING

    user_answer = update.message.text.strip()
    correct_answer = q.get("correct_answer", "").strip()
    is_correct = user_answer.lower() == correct_answer.lower()

    session["answers"].append(user_answer)
    if is_correct:
        session["correct"] += 1
    session["current"] += 1

    if is_correct:
        feedback = t("quiz.correct", _lang(context))
    else:
        feedback = t("quiz.wrong", _lang(context), answer=correct_answer)
    if q.get("explanation"):
        feedback += f"\n\n<i>{q['explanation'][:200]}</i>"

    await update.message.reply_text(
        feedback, reply_markup=quiz_next_keyboard(language=_lang(context)), parse_mode="HTML"
    )
    return QUIZ_ANSWERING


async def handle_quiz_next(update: Update, context):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        logger.warning("quiz_next_edit_failed", user_id=update.effective_user.id, exc_info=True)
    await _send_quiz_question(update, context, query.message, new_message=True)
    return QUIZ_ANSWERING


async def handle_quiz_end(update: Update, context):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        logger.warning("quiz_end_edit_failed", user_id=update.effective_user.id, exc_info=True)
    await _show_quiz_result(update, context, query.message)
    context.user_data.pop("quiz_session", None)
    return ConversationHandler.END


async def handle_quiz_retry(update: Update, context):
    query = update.callback_query
    await query.answer()
    session = context.user_data.get("quiz_session", {})
    session["current"] = 0
    session["answers"] = []
    session["correct"] = 0
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        logger.warning("quiz_retry_edit_failed", user_id=update.effective_user.id, exc_info=True)
    await _send_quiz_question(update, context, query.message, new_message=True)
    return QUIZ_ANSWERING


async def handle_lesson_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        t("lesson.grade_prompt", _lang(context)),
        reply_markup=grade_keyboard("lesson_grade", language=_lang(context)),
    )
    return LESSON_GRADE


async def handle_lesson_grade(update: Update, context):
    query = update.callback_query
    await query.answer()
    grade = int(query.data.split("_")[-1])
    context.user_data["lesson_grade"] = grade
    await query.edit_message_text(
        t("lesson.subject_prompt", _lang(context), grade=grade),
        reply_markup=subject_keyboard("lesson_subject", language=_lang(context)),
    )
    return LESSON_SUBJECT


async def handle_lesson_subject(update: Update, context):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        logger.warning("lesson_subject_ans_fail", user_id=update.effective_user.id, exc_info=True)
    code = query.data.split("_")[-1]
    context.user_data["lesson_subject"] = code
    # Reset feature selections
    context.user_data["lesson_features"] = {
        "exit_ticket": False,
        "differentiation": False,
        "diagram_suggestions": False,
        "misconception_activities": False,
    }
    await query.edit_message_text(
        t("lesson.features_prompt", _lang(context), grade=context.user_data.get("lesson_grade")),
        reply_markup=lesson_features_keyboard(
            context.user_data["lesson_features"], language=_lang(context)
        ),
    )
    return LESSON_FEATURES


async def handle_lesson_features(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "lesson_features_done":
        grade = context.user_data.get("lesson_grade", 10)
        await query.edit_message_text(
            t("lesson.topic_prompt", _lang(context), grade=grade),
            reply_markup=back_keyboard(language=_lang(context)),
        )
        return LESSON_TOPIC
    # Toggle a feature
    feature_map = {
        "lesson_feature_exit_ticket": "exit_ticket",
        "lesson_feature_differentiation": "differentiation",
        "lesson_feature_diagrams": "diagram_suggestions",
        "lesson_feature_misconceptions": "misconception_activities",
    }
    feature_key = feature_map.get(data)
    if feature_key:
        features = context.user_data.setdefault("lesson_features", {})
        features[feature_key] = not features.get(feature_key, False)
        await query.edit_message_reply_markup(
            reply_markup=lesson_features_keyboard(features, language=_lang(context)),
        )
    return LESSON_FEATURES


async def handle_lesson_topic(update: Update, context):
    topic = update.message.text
    grade = context.user_data.get("lesson_grade", 10)
    features = context.user_data.get("lesson_features", {})
    await update.message.reply_text(t("lesson.generating", _lang(context)))

    try:
        router_llm = ModelRouter()
        agent = LessonPlannerAgent(llm_router=router_llm)
        result = await agent.generate(
            grade_level=grade,
            topic=topic,
            subject=context.user_data.get("lesson_subject") or context.user_data.get("subject"),
            generate_exit_ticket=features.get("exit_ticket", False),
            generate_differentiation=features.get("differentiation", False),
            generate_diagram_suggestions=features.get("diagram_suggestions", False),
            generate_misconception_activities=features.get("misconception_activities", False),
        )
        response = (
            f"Lesson Plan: {topic} (Grade {grade})\n\n"
            f"Objective:\n{result['objective']}\n\n"
            f"Explanation:\n{result['explanation'][:800]}...\n\n"
        )
        if result.get("activities"):
            response += "Activities:\n"
            for a in result["activities"]:
                response += f"  * {a.get('name', '')} ({a.get('duration_minutes', '')}min)\n"
        if result.get("assessment"):
            response += f"\nAssessment:\n{result['assessment'][:400]}"
        if result.get("homework"):
            response += f"\n\nHomework:\n{result['homework'][:400]}"
        if result.get("exit_ticket"):
            response += "\n\n📝 Exit Ticket:"
            for q in result["exit_ticket"][:3]:
                response += f"\n• {q['question_text'][:200]}"
        if result.get("differentiation"):
            response += "\n\n🎯 Differentiation:"
            for d in result["differentiation"][:3]:
                response += f"\n• {d['group']}: {d['description'][:150]}"
        if result.get("diagram_suggestions"):
            response += "\n\n📊 Diagrams:"
            for d in result["diagram_suggestions"][:3]:
                response += f"\n• {d['title']} ({d['diagram_type']})"
        if result.get("misconception_activities"):
            response += "\n\n🔬 Misconception Activities:"
            for a in result["misconception_activities"][:2]:
                response += f"\n• {a['activity_name']}"
        await _reply_long(
            update.message,
            response,
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
            parse_mode="HTML",
        )
        await router_llm.close()
    except Exception as e:
        logger.error("lesson_error", error=str(e))
        await update.message.reply_text(
            t("lesson.error", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )

    return ConversationHandler.END


async def diagram_command(update: Update, context):
    await update.message.reply_text(
        t("diagram.grade_prompt", _lang(context)),
        reply_markup=grade_keyboard("diagram_grade", language=_lang(context)),
    )
    return DIAGRAM_GRADE


async def handle_diagram_grade(update: Update, context):
    query = update.callback_query
    await query.answer()
    grade = int(query.data.split("_")[-1])
    context.user_data["diagram_grade"] = grade
    await query.edit_message_text(
        t("diagram.subject_prompt", _lang(context), grade=grade),
        reply_markup=subject_keyboard("diagram_subject", language=_lang(context)),
    )
    return DIAGRAM_SUBJECT


async def handle_diagram_subject(update: Update, context):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        logger.warning("diagram_subject_ans_fail", user_id=update.effective_user.id, exc_info=True)
    code = query.data.split("_")[-1]
    context.user_data["diagram_subject"] = code
    await query.edit_message_text(
        t("diagram.topic_prompt", _lang(context), grade=context.user_data.get("diagram_grade")),
        reply_markup=back_keyboard(language=_lang(context)),
    )
    return DIAGRAM_TOPIC


async def handle_diagram_topic(update: Update, context):
    try:
        topic = update.message.text
    except AttributeError:
        topic = ""
    grade = context.user_data.get("diagram_grade", 10)
    lang = _lang(context)
    try:
        await update.message.reply_text(t("diagram.generating", lang))
        router_llm = ModelRouter()
        agent = DiagramAgent(llm_router=router_llm)
        result = await agent.generate(
            prompt=topic,
            topic=topic,
            difficulty="beginner",
            grade=grade,
            subject=context.user_data.get("diagram_subject") or context.user_data.get("subject"),
        )

        svg = result.get("diagram_svg", "")
        labels = result.get("labels", [])
        title = result.get("title", topic)

        png_bytes = render_svg_to_png(svg, width=800, height=600)

        label_lines = (
            "\n".join(f"{i + 1}. {label['text']}" for i, label in enumerate(labels))
            if labels
            else t("diagram.no_labels", lang)
        )

        caption = (
            f"📐 {title}\n"
            f"{t('diagram.grade_label', lang)}: {grade}\n"
            f"{t('diagram.labels_count', lang, count=len(labels))}: {len(labels)}\n\n"
            f"{label_lines}"
        )

        from telegram import InputFile

        telegram_id = update.effective_user.id if update.effective_user else None
        if telegram_id:
            try:
                await _save_diagram_rewards(telegram_id, context)
            except Exception:
                logger.warning("diagram_rewards_fail", telegram_id=telegram_id, exc_info=True)

        xp_text = ""
        xp_awarded = context.user_data.get("last_xp_awarded")
        level_up = context.user_data.pop("last_level_up", False)
        if xp_awarded:
            xp_text += f"\n\n⭐ +{xp_awarded} XP"
        if level_up:
            new_level = context.user_data.get("last_new_level", 1)
            xp_text += f"\n🎉 LEVEL UP! Now Level {new_level}!"

        await update.message.reply_photo(
            photo=InputFile(png_bytes, filename="diagram.png"),
            caption=(caption + xp_text)[:1024],
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False),
                language=lang,
            ),
        )
        await router_llm.close()
    except Exception as e:
        logger.error("diagram_error", error=str(e), topic=topic)
        await update.message.reply_text(
            t("diagram.error", lang),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False),
                language=lang,
            ),
        )

    return ConversationHandler.END


async def _save_diagram_rewards(telegram_id, context):
    from sqlalchemy import select

    from src.api.gamification import XP_SOURCES

    async def _save():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            xp_amount = XP_SOURCES.get("diagram_completion", 10)
            meta = {"source": "telegram_bot"}
            gam_result, _, level_up = await award_xp(
                user.id,
                "diagram_completion",
                xp_amount,
                meta,
                session,
            )
            await update_streak(user.id, session)
            await check_achievements(user.id, gam_result, session)
            await session.commit()
            context.user_data["last_xp_awarded"] = xp_amount
            context.user_data["last_level_up"] = level_up
            context.user_data["last_new_level"] = gam_result.level

    await _db_try(_save)


def _format_progress_overview(data: dict, language: str = "en") -> str:
    gam = data["gam"]
    quizzes = data["recent_quizzes"]
    masteries = data["mastery_records"]

    readiness = sum((q.score or 0.0) for q in quizzes) / len(quizzes) if quizzes else 0.0

    lines = [f"<b>{t('progress.title', language)}</b>", ""]
    lines.append(f"🎯 {t('progress.readiness', language)}: <b>{readiness:.0f}%</b>")
    best = gam.longest_streak if gam else 0
    lines.append(
        f"🔥 {t('progress.streak', language)}: {gam.current_streak if gam else 0}"
        f" ({t('progress.best', language)}: {best})"
    )
    lines.append(
        f"💎 {t('progress.level', language)} {gam.level if gam else 1}"
        f" · {gam.total_xp if gam else 0} XP"
    )

    if masteries:
        lines += ["", f"<b>{t('progress.topic_mastery', language)}</b>"]
        for m in masteries[:5]:
            score = max(0, min(round(m.average_score), 100))
            filled = int(score // 10)
            bar = "█" * filled + "░" * (10 - filled)
            icon = "🔴" if score < 40 else "🟡" if score < 60 else "🟢" if score < 80 else "💚"
            lines.append(f"{icon} {html.escape(str(m.topic))} {bar} {score}%")

    weakest = min(masteries, key=lambda m: m.average_score) if masteries else None
    if weakest:
        topic = html.escape(str(weakest.topic))
        lines += ["", f"👉 {t('progress.focus_next', language)}: <b>{topic}</b>"]
    return "\n".join(lines)


async def handle_progress(update: Update, context):
    query = update.callback_query
    if query:
        await query.answer()
    language = _lang(context)
    telegram_id = update.effective_user.id

    async def _show():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            keyboard = main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=language
            )
            if not user:
                text = t("progress.need_start", language)
            else:
                data = await fetch_progress_overview(user.id, session)
                if not data["has_data"]:
                    text = t("progress.empty", language)
                    keyboard = InlineKeyboardMarkup(
                        [[InlineKeyboardButton(t("take_quiz", language), callback_data="quiz")]]
                    )
                else:
                    text = _format_progress_overview(data, language)

            if query:
                try:
                    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
                except Exception:
                    logger.warning("progress_edit_failed", user_id=telegram_id, exc_info=True)
                    await query.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
            else:
                await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

    await _db_try(_show)


async def fetch_progress_overview(user_id: uuid.UUID, session: AsyncSession) -> dict:
    """Fetch gamification, recent quizzes, and mastery rows for the progress overview."""
    gam = (
        await session.execute(select(UserGamification).where(UserGamification.user_id == user_id))
    ).scalar_one_or_none()
    quizzes = list(
        (
            await session.execute(
                select(QuizAttempt)
                .where(QuizAttempt.user_id == user_id)
                .order_by(QuizAttempt.started_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    masteries = list(
        (
            await session.execute(
                select(StudentMastery)
                .where(StudentMastery.user_id == user_id)
                .order_by(StudentMastery.average_score.desc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "gam": gam,
        "recent_quizzes": quizzes,
        "mastery_records": masteries,
        "has_data": bool(quizzes or masteries),
    }


async def handle_language(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        t("choose_language", _lang(context)),
        reply_markup=language_keyboard(language=_lang(context)),
    )


async def handle_language_select(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang_map = {
        "lang_en": ("en", "English"),
        "lang_am": ("am", "Amharic"),
        "lang_both": ("both", "Bilingual"),
    }
    code, name = lang_map.get(query.data, ("en", "English"))
    context.user_data["language"] = code

    async def _sync_language():
        async with _api_client() as client:
            api_base = settings.api_base_url
            await client.patch(
                f"{api_base}/users/{update.effective_user.id}/language",
                params={"language": code},
            )

    await _db_try(_sync_language)
    await query.message.reply_text(
        t("language.set", _lang(context), name=name),
        reply_markup=main_menu_keyboard(
            context.user_data.get("socratic_mode", False), language=_lang(context)
        ),
    )


async def handle_socratic_toggle(update: Update, context):
    query = update.callback_query
    await query.answer()
    current = context.user_data.get("socratic_mode", False)
    context.user_data["socratic_mode"] = not current
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        logger.warning("soc_toggle_edit_fail", user_id=update.effective_user.id, exc_info=True)
    await query.message.reply_text(
        t(
            "tutor.socratic_on" if context.user_data["socratic_mode"] else "tutor.socratic_off",
            _lang(context),
        ),
        reply_markup=main_menu_keyboard(not current, language=_lang(context)),
    )


async def model_command(update: Update, context):
    api_base = settings.api_base_url
    try:
        async with _api_client() as client:
            resp = await client.get(f"{api_base}/models")
            models = resp.json()
        await update.message.reply_text(
            "Select a provider:",
            reply_markup=InlineKeyboardMarkup(model_providers_keyboard(models)),
        )
    except Exception as e:
        logger.error("model_command_error", error=str(e))
        await update.message.reply_text(
            t("model.no_models", _lang(context)),
            reply_markup=main_menu_keyboard(language=_lang(context)),
        )


async def handle_model_selection(update: Update, context):
    query = update.callback_query
    await query.answer()
    data: str = query.data or ""
    api_base = settings.api_base_url

    if data == "model:back":
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            logger.warning("model_back_edit_fail", user_id=update.effective_user.id, exc_info=True)
        await query.message.reply_text(
            t("common.main_menu", _lang(context)),
            reply_markup=main_menu_keyboard(language=_lang(context)),
        )
        return

    if data == "model:back_providers":
        try:
            async with _api_client() as client:
                resp = await client.get(f"{api_base}/models")
                models = resp.json()
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                logger.warning(
                    "model_bproviders_edit_fail",
                    user_id=update.effective_user.id,
                    exc_info=True,
                )
            await query.message.reply_text(
                "Select a provider:",
                reply_markup=InlineKeyboardMarkup(model_providers_keyboard(models)),
            )
        except Exception as e:
            logger.error("model_providers_error", error=str(e))
            await query.message.reply_text(
                t("model.no_providers", _lang(context)),
                reply_markup=main_menu_keyboard(language=_lang(context)),
            )
        return

    if data == "model:refresh":
        try:
            async with _api_client() as client:
                await client.post(f"{api_base}/models/refresh")
                resp = await client.get(f"{api_base}/models")
                models = resp.json()
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                logger.warning(
                    "model_refresh_edit_fail",
                    user_id=update.effective_user.id,
                    exc_info=True,
                )
            await query.message.reply_text(
                "Select a provider:",
                reply_markup=InlineKeyboardMarkup(model_providers_keyboard(models)),
            )
        except Exception as e:
            logger.error("model_refresh_error", error=str(e))
            await query.message.reply_text(
                t("model.refresh_failed", _lang(context)),
                reply_markup=main_menu_keyboard(language=_lang(context)),
            )
        return

    if data.startswith("model:provider:"):
        provider = data[len("model:provider:") :]
        try:
            async with _api_client() as client:
                resp = await client.get(f"{api_base}/models")
                all_models: list[dict] = resp.json()
                resp2 = await client.get(f"{api_base}/models/active")
                data2: dict = resp2.json()
                active = data2.get("model", "")
            filtered = [m for m in all_models if m.get("provider") == provider]
            context.user_data["provider_models"] = filtered
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                logger.warning(
                    "model_prov_models_edit_fail",
                    user_id=update.effective_user.id,
                    exc_info=True,
                )
            await query.message.reply_text(
                f"Models from {provider.capitalize()}:",
                reply_markup=InlineKeyboardMarkup(provider_models_keyboard(filtered, active)),
            )
        except Exception as e:
            logger.error("model_provider_models_error", error=str(e))
            await query.message.reply_text(
                t("model.no_models", _lang(context)),
                reply_markup=main_menu_keyboard(language=_lang(context)),
            )
        return

    if data.startswith("m:"):
        idx_str = data[2:]
        try:
            idx = int(idx_str)
        except ValueError:
            return
        provider_models = context.user_data.get("provider_models", [])
        if idx < 0 or idx >= len(provider_models):
            return
        model_id = provider_models[idx]["id"]
        try:
            async with _api_client() as client:
                await client.post(f"{api_base}/models/active", json={"model": model_id})
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                logger.warning(
                    "model_set_edit_fail",
                    user_id=update.effective_user.id,
                    exc_info=True,
                )
            await query.message.reply_text(
                f"✅ Active model is now: {model_id}",
                reply_markup=main_menu_keyboard(language=_lang(context)),
            )
        except Exception as e:
            logger.error("model_set_error", error=str(e))
            await query.message.reply_text(
                t("model.set_failed", _lang(context), model=model_id),
                reply_markup=main_menu_keyboard(language=_lang(context)),
            )
        return


async def handle_hint(update: Update, context):
    query = update.callback_query
    await query.answer()
    hint_level = int(query.data.split("_")[-1])
    reveal = context.user_data.get("reveal_answer", False)
    if reveal:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            logger.warning(
                "hint_revealed_edit_fail",
                user_id=update.effective_user.id,
                exc_info=True,
            )
        await query.message.reply_text(
            t("tutor.hint_revealed", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )
        return
    question = context.user_data.get("ask_question", "")
    if not question:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            logger.warning("hint_no_q_edit_fail", user_id=update.effective_user.id, exc_info=True)
        await query.message.reply_text(
            t("tutor.no_question", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )
        return
    context.user_data["hint_level"] = hint_level
    hint_msg = await query.message.reply_text(
        t("tutor.hint_level", _lang(context), level=hint_level)
    )
    try:
        telegram_id = update.effective_user.id if update.effective_user else None
        async with async_session_factory()() as _mem_db:
            memory_user_id, memory_session_id, memory_context, conversation_messages = (
                await _build_memory_context(
                    telegram_id,
                    context.user_data.get("tutor_grade") or context.user_data.get("grade_level"),
                    _mem_db,
                )
                if telegram_id
                else (None, None, "", [])
            )

            result = await run_graph(
                user_message=question,
                user_id=memory_user_id,
                grade_level=context.user_data.get("grade_level"),
                subject=context.user_data.get("tutor_subject") or context.user_data.get("subject"),
                language=context.user_data.get("language", "en"),
                socratic_mode=context.user_data.get("socratic_mode", False),
                hint_level=hint_level,
                reveal_answer=False,
                memory_context=memory_context,
                messages=conversation_messages,
                db_session_factory=async_session_factory,
            )

        if memory_user_id and memory_session_id:
            try:
                mem_session = (
                    await _mem_db.execute(
                        select(MemorySession).where(MemorySession.session_id == memory_session_id)
                    )
                ).scalar_one_or_none()
                if mem_session:
                    conversation_messages.append({"role": "user", "content": question})
                    conversation_messages.append({"role": "assistant", "content": result.answer})
                    SessionManager().set_messages(mem_session, conversation_messages[-20:])
                    await CrossSessionRecall().record_turns(
                        user_id=memory_user_id,
                        session_id=mem_session.session_id,
                        turns=conversation_messages[-2:],
                        topic=mem_session.active_topic,
                        db=_mem_db,
                    )
                    await _mem_db.commit()
            except Exception as e:
                logger.warning("memory_turns_save_error", error=str(e))

        response = result.answer
        if result.misconception_detected:
            response += t("tutor.misconception", _lang(context))
        await _reply_long(
            hint_msg,
            response,
            reply_markup=hint_keyboard(hint_level, False, language=_lang(context)),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("hint_callback_error", error=str(e))
        await hint_msg.edit_text(
            t("common.error", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )


async def handle_reveal_answer(update: Update, context):
    query = update.callback_query
    await query.answer()
    question = context.user_data.get("ask_question", "")
    if not question:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            logger.warning("reveal_no_q_edit_fail", user_id=update.effective_user.id, exc_info=True)
        await query.message.reply_text(
            t("tutor.no_question", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )
        return
    hint_level = context.user_data.get("hint_level", 0)
    context.user_data["reveal_answer"] = True
    reveal_msg = await query.message.reply_text(t("tutor.revealing_answer", _lang(context)))
    try:
        telegram_id = update.effective_user.id if update.effective_user else None
        async with async_session_factory()() as _mem_db:
            memory_user_id, memory_session_id, memory_context, conversation_messages = (
                await _build_memory_context(
                    telegram_id,
                    context.user_data.get("tutor_grade") or context.user_data.get("grade_level"),
                    _mem_db,
                )
                if telegram_id
                else (None, None, "", [])
            )

            result = await run_graph(
                user_message=question,
                user_id=memory_user_id,
                grade_level=context.user_data.get("grade_level"),
                subject=context.user_data.get("tutor_subject") or context.user_data.get("subject"),
                language=context.user_data.get("language", "en"),
                socratic_mode=False,
                hint_level=hint_level,
                reveal_answer=True,
                memory_context=memory_context,
                messages=conversation_messages,
                db_session_factory=async_session_factory,
            )

            if memory_user_id and memory_session_id:
                try:
                    mem_session = (
                        await _mem_db.execute(
                            select(MemorySession).where(
                                MemorySession.session_id == memory_session_id
                            )
                        )
                    ).scalar_one_or_none()
                    if mem_session:
                        conversation_messages.append({"role": "user", "content": question})
                        conversation_messages.append(
                            {"role": "assistant", "content": result.answer}
                        )
                        SessionManager().set_messages(mem_session, conversation_messages[-20:])
                        await CrossSessionRecall().record_turns(
                            user_id=memory_user_id,
                            session_id=mem_session.session_id,
                            turns=conversation_messages[-2:],
                            topic=mem_session.active_topic,
                            db=_mem_db,
                        )
                        await _mem_db.commit()
                except Exception as e:
                    logger.warning("memory_turns_save_error", error=str(e))

        attempt_msg = (
            t("tutor.hint_usage", _lang(context), count=hint_level) if hint_level > 0 else ""
        )
        response = result.answer + attempt_msg
        await _reply_long(
            reveal_msg,
            response,
            reply_markup=hint_keyboard(hint_level, True, language=_lang(context)),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error("reveal_answer_error", error=str(e))
        await reveal_msg.edit_text(
            t("common.error", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False), language=_lang(context)
            ),
        )


async def handle_general_message(update: Update, context):
    message_text = update.message.text
    try:
        router = ModelRouter()
        from src.agents.orchestrator import OrchestratorAgent

        orchestrator = OrchestratorAgent(llm_router=router)
        intent = await orchestrator.classify_intent(message_text)
        await router.close()

        if intent["intent"] in ("tutor", "general"):
            return await handle_question(update, context)
        elif intent["intent"] in ("quiz", "lesson_plan"):
            await update.message.reply_text(
                f'I understood: "{intent["intent"]}" (confidence: {intent["confidence"]:.0%})\n\n'
                f"Use the 📝 Quiz or 📋 Lesson Plan buttons in the menu.",
                reply_markup=main_menu_keyboard(
                    context.user_data.get("socratic_mode", False), language=_lang(context)
                ),
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                f'I understood: "{intent["intent"]}" (confidence: {intent["confidence"]:.0%})\n\n'
                f"Use the menu buttons to access specific features.",
                reply_markup=main_menu_keyboard(
                    context.user_data.get("socratic_mode", False), language=_lang(context)
                ),
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error("general_message_error", error=str(e))
        return await handle_question(update, context)


async def error_handler(update: Update, context):
    logger.error("telegram_error", error=str(context.error))
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Sorry, something went wrong. Please try again or use /help.",
            )
    except Exception as e:
        logger.error("error_handler_failed", error=str(e))


async def recovery_command(update: Update, context):
    from sqlalchemy import select

    async def _handle():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            user = result.scalar_one_or_none()
            if not user:
                await _reply_long(update, "❌ You need to /start first to use this command.")
                return

            from src.database.models import RecoveryPlan, RecoveryTask

            plans_result = await session.execute(
                select(RecoveryPlan)
                .where(RecoveryPlan.user_id == user.id, RecoveryPlan.status == "active")
                .order_by(RecoveryPlan.created_at.desc())
            )
            plans = list(plans_result.scalars().all())

            if not plans:
                await _reply_long(
                    update, t("recovery.no_plans", _lang(context)), parse_mode="Markdown"
                )
                return

            from src.agents.weak_topic_detection import get_weak_topics

            weak_topics = await get_weak_topics(user.id, session)

            lines = ["📋 *Recovery Plans*"]
            if weak_topics:
                lines.append(f"\n🔍 *Weak Topics:* {len(weak_topics)} identified")
                for wt in weak_topics[:3]:
                    icon = (
                        "🔴"
                        if wt["severity"] == "critical"
                        else "🟡"
                        if wt["severity"] == "moderate"
                        else "🔵"
                    )
                    lines.append(f"{icon} {wt['topic']} — {wt['average_score']:.0f}%")

            from src.api.gamification import _get_recovery_progress

            rp = await _get_recovery_progress(user.id, session)
            if rp:
                lines.append(
                    f"\n📊 *Overall Progress:* {rp.completed_tasks}/{rp.total_tasks} tasks ({rp.overall_progress_pct:.0f}%)"  # noqa: E501
                )

            for plan in plans:
                progress_pct = round(plan.completed_tasks / max(plan.total_tasks, 1) * 100, 1)
                lines.append(f"\n*Plan: {plan.topic}*")
                lines.append(
                    f"Progress: {plan.completed_tasks}/{plan.total_tasks} ({progress_pct:.0f}%)"
                )
                tasks_result = await session.execute(
                    select(RecoveryTask)
                    .where(RecoveryTask.plan_id == plan.id)
                    .order_by(RecoveryTask.created_at)
                )
                tasks = list(tasks_result.scalars().all())
                for task in tasks:
                    status = "✅" if task.is_completed else "⬜"
                    lines.append(f"{status} {task.title}")

            await _reply_long(update, "\n".join(lines), parse_mode="Markdown")

    await _db_try(_handle)


async def handle_recovery_complete_task(update: Update, context):
    query = update.callback_query
    await query.answer()
    task_id = query.data.replace("recovery_complete_", "")

    from datetime import datetime, timezone

    from sqlalchemy import select

    from src.api.gamification import RECOVERY_MILESTONE_THRESHOLDS, XP_SOURCES
    from src.database.models import RecoveryTask

    async def _handle():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == update.effective_user.id)
            )
            user = result.scalar_one_or_none()
            if not user:
                await query.edit_message_text(t("recovery.user_not_found", _lang(context)))
                return

            task_result = await session.execute(
                select(RecoveryTask).where(RecoveryTask.id == task_id)
            )
            task = task_result.scalar_one_or_none()
            if not task:
                await query.edit_message_text(t("recovery.task_not_found", _lang(context)))
                return
            if task.is_completed:
                await query.edit_message_text(
                    t("recovery.task_done", _lang(context), title=task.title), parse_mode="Markdown"
                )
                return

            task.is_completed = True
            task.completed_at = datetime.now(timezone.utc)

            xp_amount = XP_SOURCES.get("recovery_task_completion", 40)
            task.xp_awarded = xp_amount

            plan = task.plan
            plan.completed_tasks += 1
            if plan.completed_tasks >= plan.total_tasks:
                plan.status = "completed"

            gam, _, level_up = await award_xp(
                user.id,
                "recovery_task_completion",
                xp_amount,
                {"task_id": str(task_id), "plan_id": str(plan.id), "topic": plan.topic},
                session,
            )

            completed = plan.completed_tasks
            if completed in RECOVERY_MILESTONE_THRESHOLDS:
                milestone_bonus = RECOVERY_MILESTONE_THRESHOLDS[completed]
                await award_xp(
                    user.id,
                    "recovery_milestone",
                    milestone_bonus,
                    {"plan_id": str(plan.id), "completed_tasks": completed, "topic": plan.topic},
                    session,
                )

            await update_streak(user.id, session)
            await check_achievements(user.id, gam, session)

            await session.commit()

            await query.edit_message_text(
                f"✅ *Task Completed!*\n\n{task.title}\n\n+{xp_amount} XP",
                parse_mode="Markdown",
            )

    await _db_try(_handle)


async def handle_recovery_view(update: Update, context):
    query = update.callback_query
    await query.answer()
    await recovery_command(update, context)


async def progress_command(update: Update, context):
    telegram_id = update.effective_user.id
    language = _lang(context)
    menu = main_menu_keyboard(context.user_data.get("socratic_mode", False), language=language)

    async def _handle():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                await update.message.reply_text(
                    t("progress.need_start", language), reply_markup=menu
                )
                return
            data = await fetch_progress_overview(user.id, session)
            if not data["has_data"]:
                quiz_keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton(t("take_quiz", language), callback_data="quiz")]]
                )
                await update.message.reply_text(
                    t("progress.empty", language),
                    parse_mode="HTML",
                    reply_markup=quiz_keyboard,
                )
                return
            await update.message.reply_text(
                _format_progress_overview(data, language), parse_mode="HTML", reply_markup=menu
            )

    await _db_try(_handle)


async def settings_command(update: Update, context):
    telegram_id = update.effective_user.id

    async def _handle():
        from sqlalchemy import select

        from telegram import InlineKeyboardButton

        async with async_session_factory() as session:
            user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = user_result.scalar_one_or_none()
            if not user:
                await update.message.reply_text(t("progress.need_start", _lang(context)))
                return

            prefs_result = await session.execute(
                select(NotificationPreference).where(NotificationPreference.user_id == user.id)
            )
            prefs = prefs_result.scalar_one_or_none()

            milestone = "✅ On" if prefs and prefs.milestone_alerts else "⬜ Off"
            reminders = "✅ On" if prefs and prefs.review_reminders else "⬜ Off"
            digest = prefs.digest_frequency.capitalize() if prefs else "Never"

            text = t(
                "settings.text",
                _lang(context),
                milestone=milestone,
                reminder=reminders,
                digest=digest,
            )

            buttons = []
            row = []
            if prefs and prefs.milestone_alerts:
                row.append(
                    InlineKeyboardButton(
                        "📊 Disable Milestones", callback_data="settings_toggle_milestone"
                    )
                )
            else:
                row.append(
                    InlineKeyboardButton(
                        "📊 Enable Milestones", callback_data="settings_toggle_milestone"
                    )
                )
            buttons.append(row)
            row2 = []
            if prefs and prefs.review_reminders:
                row2.append(
                    InlineKeyboardButton(
                        "🔔 Disable Reminders", callback_data="settings_toggle_reminders"
                    )
                )
            else:
                row2.append(
                    InlineKeyboardButton(
                        "🔔 Enable Reminders", callback_data="settings_toggle_reminders"
                    )
                )
            buttons.append(row2)
            buttons.append(
                [
                    InlineKeyboardButton("📬 Digest: Daily", callback_data="settings_digest_daily"),
                    InlineKeyboardButton(
                        "📬 Digest: Weekly", callback_data="settings_digest_weekly"
                    ),
                ]
            )
            buttons.append(
                [
                    InlineKeyboardButton("📬 Digest: Off", callback_data="settings_digest_never"),
                ]
            )

            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown",
            )

    await _db_try(_handle)


async def email_command(update: Update, context):
    args = context.args
    if not args:
        await update.message.reply_text(
            t("common.email_usage", _lang(context)), parse_mode="Markdown"
        )
        return
    email = args[0].strip()
    if "@" not in email or "." not in email:
        await update.message.reply_text(t("common.email_invalid", _lang(context)))
        return

    telegram_id = update.effective_user.id

    async def _handle():
        from sqlalchemy import select

        async with async_session_factory() as session:
            user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = user_result.scalar_one_or_none()
            if not user:
                await update.message.reply_text(t("common.need_start", _lang(context)))
                return

            prefs_result = await session.execute(
                select(NotificationPreference).where(NotificationPreference.user_id == user.id)
            )
            prefs = prefs_result.scalar_one_or_none()

            if prefs:
                prefs.email = email
                prefs.email_verified = False
                prefs.verification_code = None
                prefs.verification_expires = None
            else:
                prefs = NotificationPreference(user_id=user.id, email=email)
                session.add(prefs)
            await session.commit()

        await update.message.reply_text(
            t("common.email_set", _lang(context), email=email), parse_mode="Markdown"
        )

    await _db_try(_handle)


async def handle_settings_toggle(update: Update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    telegram_id = update.effective_user.id

    async def _handle():
        from sqlalchemy import select

        async with async_session_factory() as session:
            user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = user_result.scalar_one_or_none()
            if not user:
                await query.edit_message_text("User not found. Please /start first.")
                return

            prefs_result = await session.execute(
                select(NotificationPreference).where(NotificationPreference.user_id == user.id)
            )
            prefs = prefs_result.scalar_one_or_none()
            if not prefs:
                await query.edit_message_text(
                    "No notification preferences found. Use /settings first."
                )
                return

            if data == "settings_toggle_milestone":
                prefs.milestone_alerts = not prefs.milestone_alerts
            elif data == "settings_toggle_reminders":
                prefs.review_reminders = not prefs.review_reminders
            elif data == "settings_digest_daily":
                prefs.digest_frequency = "daily"
            elif data == "settings_digest_weekly":
                prefs.digest_frequency = "weekly"
            elif data == "settings_digest_never":
                prefs.digest_frequency = "never"

            await session.commit()

        await query.edit_message_text("✅ Settings updated! Use /settings to see changes.")

    await _db_try(_handle)


async def link_command(update: Update, context):
    email = (context.args[0] if context.args else "").strip().lower()
    if not email:
        await update.message.reply_text(t("link.usage", _lang(context)))
        return

    async def _verify_email():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(User).where(
                    User.email == email,
                    User.role == UserRole.teacher,
                    User.is_active.is_(True),
                )
            )
            teacher = result.scalar_one_or_none()
            if not teacher:
                await update.message.reply_text(t("link.not_found", _lang(context)))
                return

            if teacher.telegram_id == update.effective_user.id:
                await update.message.reply_text(t("link.already_linked", _lang(context)))
                return

            code = f"{random.randint(100000, 999999)}"
            redis_conn = await get_redis()
            await redis_conn.setex(
                f"link:{update.effective_user.id}",
                300,
                f"{email}:{code}",
            )
            await update.message.reply_text(
                t("link.otp_sent", _lang(context), code=code),
                parse_mode="HTML",
            )

    await _db_try(_verify_email)
    return LINK_OTP


async def handle_link_otp(update: Update, context):
    telegram_id = update.effective_user.id
    user_code = update.message.text.strip()

    async def _link():
        redis_conn = await get_redis()
        stored = await redis_conn.get(f"link:{telegram_id}")
        if not stored:
            await update.message.reply_text(t("link.wrong_otp", _lang(context)))
            return

        stored_str = stored.decode() if isinstance(stored, bytes) else stored
        if ":" not in stored_str:
            await update.message.reply_text(t("link.wrong_otp", _lang(context)))
            return

        email, expected_code = stored_str.split(":", 1)
        if user_code != expected_code:
            await update.message.reply_text(t("link.wrong_otp", _lang(context)))
            return

        await redis_conn.delete(f"link:{telegram_id}")

        factory = async_session_factory()
        async with factory() as session:
            teacher = await session.execute(
                select(User).where(
                    User.email == email,
                    User.role == UserRole.teacher,
                    User.is_active.is_(True),
                )
            )
            teacher_user = teacher.scalar_one_or_none()
            if not teacher_user:
                await update.message.reply_text(t("link.not_found", _lang(context)))
                return

            old = await session.execute(select(User).where(User.telegram_id == telegram_id))
            old_user = old.scalar_one_or_none()
            if old_user and old_user.id != teacher_user.id:
                old_user.telegram_id = None

            teacher_user.telegram_id = telegram_id
            await session.commit()

        await update.message.reply_text(
            t("link.verified", _lang(context)),
            reply_markup=main_menu_keyboard(
                context.user_data.get("socratic_mode", False),
                language=_lang(context),
            ),
        )

    await _db_try(_link)
    return ConversationHandler.END


async def handle_copilot_start(update: Update, context):
    query = update.callback_query
    await query.answer()

    role = await _get_user_role(update.effective_user.id)
    if role != "teacher":
        await query.message.reply_text(t("copilot.not_teacher", _lang(context)))
        return ConversationHandler.END

    await query.message.reply_text(
        t("copilot.prompt", _lang(context)),
        reply_markup=back_keyboard(language=_lang(context)),
    )
    return COPILOT


async def handle_copilot_query(update: Update, context):
    question = update.message.text.strip()
    if not question:
        return COPILOT

    await update.message.reply_text(t("copilot.analyzing", _lang(context)))

    result = await _run_copilot(update.effective_user.id, question)
    if result is None:
        await update.message.reply_text(t("copilot.not_teacher", _lang(context)))
        return ConversationHandler.END

    if result.get("error"):
        await update.message.reply_text(t("copilot.error", _lang(context)))
        return ConversationHandler.END

    text = _format_copilot_response(result, _lang(context))
    await _reply_long(update, text, parse_mode="HTML")
    return ConversationHandler.END


async def _run_copilot(telegram_id: int, question: str) -> dict | None:
    from src.core.teacher_copilot.pipeline import build_teacher_pipeline
    from src.core.teacher_copilot.state import TeacherCopilotState

    async def _fetch_user():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            return result.scalar_one_or_none()

    user = await _db_try(_fetch_user)
    if not user or user.role != UserRole.teacher:
        return None

    try:
        router = ModelRouter()
        pipeline = build_teacher_pipeline(router=router)
        state = TeacherCopilotState(
            user_message=question,
            teacher_id=user.id,
        )
        final = await pipeline.ainvoke(state)
        await router.close()
        return {
            "intent": final.intent,
            "response_text": final.response_text or final.reasoning,
            "evidence": final.evidence,
            "confidence": final.confidence,
            "error": final.error,
        }
    except Exception as e:
        logger.exception("copilot_run_error", telegram_id=telegram_id, error=str(e))
        return {"error": str(e)}


def _format_copilot_response(result: dict, language: str) -> str:
    intent = result.get("intent", "")
    text = result.get("response_text", "")

    intent_icons = {
        "student_analysis": "🎯",
        "classroom_analysis": "🏫",
        "intervention_guidance": "💡",
        "curriculum_analysis": "📚",
        "lesson_planning": "📋",
        "assessment_creation": "📝",
    }
    icon = intent_icons.get(intent, "🤖")
    label = intent.replace("_", " ").title()
    header = f"{icon} {label}\n\n"

    lines = [header + text]

    evidence = result.get("evidence", [])
    if evidence:
        lines.append(f"\n📋 {t('copilot.evidence_label', language)}:")
        from src.core.teacher_copilot.evidence_engine import EvidenceEngine

        citations = EvidenceEngine.format_citations(evidence)
        lines.append(f"<code>{citations}</code>")

    full = "\n".join(lines)

    if len(full) > 4000:
        full = full[:3997] + "..."

    return full


async def assignments_command(update: Update, context):
    api_base = settings.api_base_url
    user_id = update.effective_user.id
    async with _api_client(timeout=30.0) as client:
        try:
            user_resp = await client.get(f"{api_base}/users/by_telegram/{user_id}")
        except httpx.RequestError:
            await _reply_long(update, "❌ Could not reach the server. Please try again later.")
            return
        if user_resp.status_code != 200:
            await _reply_long(update, "❌ You need to /start first.")
            return
        user_data = user_resp.json()
        role = user_data.get("role", "student")

        if role in ("admin", "teacher"):
            try:
                ws_resp = await client.get(
                    f"{api_base}/api/v1/workspaces/?user_id={user_data['id']}"
                )
            except httpx.RequestError:
                await _reply_long(update, "❌ Could not reach the server. Please try again later.")
                return
            if ws_resp.status_code != 200 or not ws_resp.json():
                await _reply_long(update, "No workspace found. Create one in the dashboard first.")
                return
            ws_id = ws_resp.json()[0]["id"]
            try:
                resp = await client.get(f"{api_base}/api/v1/assignments/?workspace_id={ws_id}")
            except httpx.RequestError:
                await _reply_long(update, "❌ Could not reach the server. Please try again later.")
                return
        else:
            try:
                resp = await client.get(
                    f"{api_base}/api/v1/assignments/my?student_id={user_data['id']}"
                )
            except httpx.RequestError:
                await _reply_long(update, "❌ Could not reach the server. Please try again later.")
                return

        if resp.status_code != 200:
            await _reply_long(update, "❌ Failed to load assignments.")
            return
        assignments = resp.json()
        if not assignments:
            await _reply_long(update, "📋 No assignments found.")
            return

        lines = ["📋 *Assignments*"]
        for a in assignments[:10]:
            status_icon = {
                "draft": "📝",
                "published": "📢",
                "completed": "✅",
                "archived": "📦",
            }.get(a["status"], "📄")
            due = f" 📅 {a['due_date'][:10]}" if a.get("due_date") else ""
            lines.append(
                f"\n{status_icon} *{a['title']}*\n  `{a['id']}` | {a['assignment_type']}{due}"
            )
        await _reply_long(update, "\n".join(lines), parse_mode="Markdown")


async def submit_command(update: Update, context):
    api_base = settings.api_base_url
    args = context.args
    if len(args) < 2:
        await _reply_long(
            update,
            "Usage: /submit <assignment_id> <your answer>\nExample: /submit abc12345 My homework answer",  # noqa: E501
        )
        return

    assignment_id = args[0]
    answer = " ".join(args[1:])

    try:
        uuid.UUID(assignment_id)
    except ValueError:
        await _reply_long(update, "❌ Invalid assignment ID. Use the full UUID from /assignments.")
        return

    async with _api_client(timeout=30.0) as client:
        try:
            user_resp = await client.get(f"{api_base}/users/by_telegram/{update.effective_user.id}")
        except httpx.RequestError:
            await _reply_long(update, "❌ Could not reach the server. Please try again later.")
            return
        if user_resp.status_code != 200:
            await _reply_long(update, "❌ You need to /start first.")
            return
        user_data = user_resp.json()

        try:
            resp = await client.post(
                f"{api_base}/api/v1/assignments/{assignment_id}/submissions?student_id={user_data['id']}",
                json={"content_text": answer},
            )
        except httpx.RequestError:
            await _reply_long(update, "❌ Could not reach the server. Please try again later.")
            return
        if resp.status_code == 201:
            await _reply_long(update, "✅ Your answer has been submitted successfully!")
        elif resp.status_code == 404:
            await _reply_long(update, "❌ Assignment not found or max attempts exceeded.")
        else:
            await _reply_long(update, "❌ Submission failed. Please try again later.")


ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_UPLOAD_SIZE = 20 * 1024 * 1024


async def handle_document_upload(update: Update, context):
    doc = update.message.document
    if not doc:
        return

    file_name = doc.file_name or ""
    ext = "." + file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        await _reply_long(
            update, f"❌ Unsupported file format `{ext}`. Accepted: pdf, docx, txt, md"
        )
        return

    if doc.file_size and doc.file_size > MAX_UPLOAD_SIZE:
        await _reply_long(update, "❌ File too large. Maximum size is 20 MB.")
        return

    user_id = update.effective_user.id
    api_base = settings.api_base_url

    async with _api_client(timeout=30.0) as client:
        try:
            user_resp = await client.get(f"{api_base}/users/by_telegram/{user_id}")
        except httpx.RequestError:
            await _reply_long(update, "❌ Could not reach the server. Please try again later.")
            return
        if user_resp.status_code != 200:
            await _reply_long(update, "❌ You need to /start first.")
            return
        user_data = user_resp.json()

        if user_data.get("role") not in ("admin", "teacher"):
            await _reply_long(update, "❌ Only teachers and admins can upload materials.")
            return

        try:
            ws_resp = await client.get(f"{api_base}/api/v1/workspaces/?user_id={user_data['id']}")
        except httpx.RequestError:
            await _reply_long(update, "❌ Could not reach the server. Please try again later.")
            return
        if ws_resp.status_code != 200 or not ws_resp.json():
            await _reply_long(update, "❌ No workspace found. Create one in the dashboard first.")
            return
        workspace_id = ws_resp.json()[0]["id"]

    status_msg = await update.message.reply_text("⏳ Downloading and processing your file...")

    file = await update.message.effective_attachment.get_file()
    try:
        file_bytes = await file.download_as_bytearray()
    except Exception:
        await status_msg.edit_text("❌ Failed to download the file. Please try again.")
        return

    await status_msg.edit_text("⏳ Uploading to knowledge platform...")

    title = file_name.rsplit(".", 1)[0] if "." in file_name else file_name

    async with _api_client(timeout=120.0) as client:
        files = {"file": (file_name, file_bytes, doc.mime_type or "application/octet-stream")}
        params = {
            "workspace_id": workspace_id,
            "owner_id": user_data["id"],
            "title": title,
        }
        try:
            resp = await client.post(
                f"{api_base}/api/v1/knowledge/upload",
                files=files,
                params=params,
            )
        except httpx.RequestError:
            await status_msg.edit_text("❌ Upload failed. Could not reach the server.")
            return

    if resp.status_code == 201:
        ko_id = resp.json().get("id", "")
        await status_msg.edit_text(
            f"✅ *File uploaded successfully!*\n\n"
            f"📄 `{file_name}`\n"
            f"🆔 `{ko_id}`\n\n"
            f"It will be processed and indexed shortly.",
            parse_mode="Markdown",
        )
    else:
        await status_msg.edit_text(
            f"❌ Upload failed (HTTP {resp.status_code}). Please try again later."
        )


async def handle_upload_hint(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang = _lang(context)
    await query.message.reply_text(
        t("upload.hint", lang),
        parse_mode="Markdown",
    )


def build_app() -> Application:
    from telegram.request import HTTPXRequest

    _request = HTTPXRequest(
        read_timeout=60.0,
        write_timeout=60.0,
        connect_timeout=30.0,
        pool_timeout=5.0,
    )
    app = Application.builder().token(settings.telegram_bot_token).request(_request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("grade", grade_command))
    app.add_handler(CommandHandler("subject", subject_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("socratic", socratic_command))
    app.add_handler(CommandHandler("hint", hint_command))
    app.add_handler(CommandHandler("reveal", reveal_command))
    app.add_handler(CommandHandler("recovery", recovery_command))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("email", email_command))
    app.add_handler(CommandHandler("dashboard_login", dashboard_login_command))
    app.add_handler(CommandHandler("parent_register", register_parent))
    app.add_handler(CommandHandler("children", list_children))
    app.add_handler(CommandHandler("child_progress", child_progress))
    app.add_handler(CommandHandler("assignments", assignments_command))
    app.add_handler(CommandHandler("submit", submit_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document_upload))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    link_handler = ConversationHandler(
        entry_points=[CommandHandler("link", link_command)],
        states={
            LINK_OTP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link_otp),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu),
            CallbackQueryHandler(end_conversation, pattern="^menu$"),
        ],
        per_user=True,
    )
    app.add_handler(link_handler)

    copilot_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_copilot_start, pattern="^copilot$")],
        states={
            COPILOT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_copilot_query),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu),
            CallbackQueryHandler(end_conversation, pattern="^menu$"),
        ],
        per_user=True,
    )
    app.add_handler(copilot_handler)

    quiz_handler = ConversationHandler(
        entry_points=[
            CommandHandler("quiz", quiz_command),
            CallbackQueryHandler(handle_quiz_start, pattern="^quiz$"),
        ],
        states={
            QUIZ_TYPE: [
                CallbackQueryHandler(handle_quiz_type, pattern="^quiztype_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            QUIZ_GRADE: [
                CallbackQueryHandler(handle_quiz_grade, pattern="^quiz_grade_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            QUIZ_SUBJECT: [
                CallbackQueryHandler(handle_quiz_subject, pattern="^quiz_subject_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            QUIZ_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_topic),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            QUIZ_ANSWERING: [
                CallbackQueryHandler(handle_quiz_answer, pattern="^ans_"),
                CallbackQueryHandler(handle_quiz_next, pattern="^quiz_next$"),
                CallbackQueryHandler(handle_quiz_end, pattern="^quiz_end$"),
                CallbackQueryHandler(handle_quiz_retry, pattern="^quiz_retry$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_short_answer),
                MessageHandler(filters.VOICE, handle_quiz_voice_answer),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu),
            CallbackQueryHandler(end_conversation, pattern="^menu$"),
        ],
        per_user=True,
    )
    app.add_handler(quiz_handler)

    lesson_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_lesson_start, pattern="^lesson_plan$")],
        states={
            LESSON_GRADE: [
                CallbackQueryHandler(handle_lesson_grade, pattern="^lesson_grade_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            LESSON_SUBJECT: [
                CallbackQueryHandler(handle_lesson_subject, pattern="^lesson_subject_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            LESSON_FEATURES: [
                CallbackQueryHandler(handle_lesson_features, pattern="^lesson_feature_"),
                CallbackQueryHandler(handle_lesson_features, pattern="^lesson_features_done$"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            LESSON_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lesson_topic),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu),
            CallbackQueryHandler(end_conversation, pattern="^menu$"),
        ],
        per_user=True,
    )
    app.add_handler(lesson_handler)

    diagram_handler = ConversationHandler(
        entry_points=[CommandHandler("diagram", diagram_command)],
        states={
            DIAGRAM_GRADE: [
                CallbackQueryHandler(handle_diagram_grade, pattern="^diagram_grade_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            DIAGRAM_SUBJECT: [
                CallbackQueryHandler(handle_diagram_subject, pattern="^diagram_subject_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            DIAGRAM_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_diagram_topic),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu),
            CallbackQueryHandler(end_conversation, pattern="^menu$"),
        ],
        per_user=True,
    )
    app.add_handler(diagram_handler)

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_tutor, pattern="^tutor$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_message),
        ],
        states={
            TUTOR_GRADE: [
                CallbackQueryHandler(handle_tutor_grade, pattern="^tutor_grade_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            TUTOR_SUBJECT: [
                CallbackQueryHandler(handle_tutor_subject, pattern="^tutor_subject_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            TUTOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu),
            CallbackQueryHandler(end_conversation, pattern="^menu$"),
            CallbackQueryHandler(handle_tutor, pattern="^tutor$"),
            CallbackQueryHandler(handle_tutor_grade, pattern="^tutor_grade_"),
        ],
        per_user=True,
    )
    app.add_handler(conv_handler)

    app.add_handler(CallbackQueryHandler(handle_model_selection, pattern=r"^(model:|m:)"))
    app.add_handler(CallbackQueryHandler(handle_socratic_toggle, pattern="^socratic_toggle$"))
    app.add_handler(CallbackQueryHandler(handle_hint, pattern="^hint_"))
    app.add_handler(CallbackQueryHandler(handle_reveal_answer, pattern="^reveal_answer$"))
    app.add_handler(CallbackQueryHandler(handle_teacher_tools, pattern="^teacher_tools$"))
    app.add_handler(CallbackQueryHandler(handle_open_quizzes, pattern="^open_quizzes$"))
    app.add_handler(CallbackQueryHandler(handle_open_dashboard, pattern="^open_dashboard$"))
    app.add_handler(CallbackQueryHandler(handle_upload_hint, pattern="^upload_hint$"))
    app.add_handler(CallbackQueryHandler(handle_progress, pattern="^progress$"))
    app.add_handler(CallbackQueryHandler(handle_language, pattern="^language$"))
    app.add_handler(CallbackQueryHandler(handle_language_select, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(handle_subject, pattern="^subject_"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(menu, pattern="^menu$"))
    app.add_handler(
        CallbackQueryHandler(handle_recovery_complete_task, pattern=r"^recovery_complete_")
    )
    app.add_handler(CallbackQueryHandler(handle_recovery_view, pattern="^recovery_view$"))
    app.add_handler(CallbackQueryHandler(handle_settings_toggle, pattern=r"^settings_"))
    app.add_handler(CallbackQueryHandler(handle_parent_child_progress, pattern=r"^parent_child_"))
    app.add_handler(CallbackQueryHandler(handle_parent_summary, pattern=r"^parent_summary_"))
    app.add_handler(CallbackQueryHandler(handle_children_back, pattern="^children$"))
    app.add_error_handler(error_handler)

    return app


async def _set_bot_profile(app):
    profile = [
        ("name", "EthioSci AI Assistant", None),
        (
            "description",
            "EthioSci AI Assistant — your science learning assistant for Ethiopian Grades 7–12. "
            "Covers biology, chemistry, physics, and mathematics: ask questions, take quizzes, "
            "get lesson plans and diagrams, and track your progress.",
            None,
        ),
        (
            "description",
            "EthioSci AI Assistant — ለኢትዮጵያ 7–12ኛ ክፍል ተማሪዎች የሳይንስ ትምህርት ረዳት። "
            "ባዮሎጂ፣ ኬሚስትሪ፣ ፊዚክስ እና ሂሳብን ይሸፍናል።",
            "am",
        ),
        (
            "short_description",
            "Science learning assistant for Ethiopian Grades 7–12 "
            "(biology, chemistry, physics, math).",
            None,
        ),
        (
            "short_description",
            "ለኢትዮጵያ 7–12ኛ ክፍል የሳይንስ ትምህርት ረዳት "
            "(ባዮሎጂ፣ ኬሚስትሪ፣ ፊዚክስ፣ ሂሳብ)።",
            "am",
        ),
    ]
    for kind, text, language_code in profile:
        try:
            if kind == "name":
                await app.bot.set_my_name(text)
            elif kind == "description":
                await app.bot.set_my_description(text, language_code=language_code)
            else:
                await app.bot.set_my_short_description(text, language_code=language_code)
        except Exception:
            logger.warning(
                "bot_profile_set_failed", kind=kind, language=language_code, exc_info=True
            )


async def main():
    app = build_app()
    await app.initialize()

    from telegram import BotCommand

    commands = [
        BotCommand("start", "Show menu"),
        BotCommand("help", "Show help"),
        BotCommand("ask", "Ask a science question"),
        BotCommand("quiz", "Generate a quiz"),
        BotCommand("grade", "Set your grade (7-12)"),
        BotCommand("subject", "Set your subject (biology/chemistry/physics/mathematics)"),
        BotCommand("language", "Set language (en/am/both)"),
        BotCommand("socratic", "Toggle Socratic mode"),
        BotCommand("hint", "Get a hint"),
        BotCommand("reveal", "Reveal the answer"),
        BotCommand("diagram", "Generate a science diagram"),
        BotCommand("recovery", "View recovery plans"),
        BotCommand("progress", "View your progress"),
        BotCommand("settings", "Notification settings"),
        BotCommand("email", "Set your email"),
        BotCommand("model", "Manage AI models"),
        BotCommand("link", "Link teacher dashboard account"),
        BotCommand("cancel", "Cancel current operation"),
        BotCommand("menu", "Show main menu"),
        BotCommand("assignments", "View your assignments"),
        BotCommand("submit", "Submit answer to an assignment"),
    ]
    await app.bot.set_my_commands(commands)

    await _set_bot_profile(app)

    if settings.telegram_webhook_url:
        await app.bot.set_webhook(
            url=settings.telegram_webhook_url,
            secret_token=settings.telegram_webhook_secret,
        )
        await app.start()
        logger.info("webhook_set", url=settings.telegram_webhook_url)
    else:
        logger.info("starting_polling")
        await app.updater.start_polling(
            allowed_updates=["message", "callback_query"], drop_pending_updates=True
        )
        await app.start()
        logger.info("bot_polling_started")
        try:
            import asyncio

            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            await app.shutdown()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
