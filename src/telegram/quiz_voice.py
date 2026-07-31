import structlog
from sqlalchemy import select
from telegram.ext import ContextTypes, ConversationHandler

from src.config import settings
from src.core.audio_storage import AudioStorageService
from src.database.models import User
from src.database.session import async_session_factory
from src.telegram.i18n import t
from src.telegram.keyboards import (
    answer_options_keyboard,
    quiz_next_keyboard,
    quiz_result_keyboard,
)
from src.voice.providers import SpeechProviderRegistry
from telegram import Update

logger = structlog.get_logger(__name__)

_registry = SpeechProviderRegistry()
_audio_storage = AudioStorageService()

QUIZ_ANSWERING = 4


async def handle_quiz_voice_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    if not message or not message.voice:
        return QUIZ_ANSWERING

    user = update.effective_user
    if not user:
        return QUIZ_ANSWERING

    session = context.user_data.get("quiz_session", {})
    qs = session.get("questions", [])
    idx = session.get("current", 0)

    if idx >= len(qs):
        await _show_quiz_result(update, context, session)
        return ConversationHandler.END

    q = qs[idx]
    qtype = q.get("question_type", "")

    processing = await message.reply_text("Processing your voice answer...")

    try:
        audio_bytes = await _download_voice(message)
        language = await _resolve_language(user.id, context)
        transcript = await _registry.transcribe(audio_bytes, language=language)
        effective_language = language or transcript.language or "en"
    except Exception as e:
        logger.error("quiz_voice_stt_failed", error=str(e))
        await processing.edit_text("Sorry, could not process your voice.")
        return QUIZ_ANSWERING

    async with async_session_factory()() as db:
        await _audio_storage.save(
            audio_bytes=audio_bytes,
            transcript=transcript.text,
            session=db,
            user_id=str(user.id),
            language=effective_language,
            mime_type="audio/ogg",
            direction="user",
            modality="quiz_answer",
        )

    if qtype == "short_answer":
        return await _process_short_answer(
            message, processing, context, q, session, transcript.text
        )
    return await _reject_non_short_answer(message, context, q)


async def _download_voice(message) -> bytes:
    voice = message.voice
    file = await voice.get_file()
    if file.file_size and file.file_size > settings.telegram_voice_max_size:
        raise ValueError(f"Voice file too large: {file.file_size} bytes")
    raw = await file.download_as_bytearray()
    return bytes(raw)


async def _resolve_language(telegram_id: int, context) -> str:
    session_lang = context.user_data.get("language")
    if session_lang:
        return "" if session_lang == "both" else session_lang
    async with async_session_factory()() as db:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
    if user and user.language:
        lang = user.language
        return "" if lang == "both" else lang
    return ""


async def _process_short_answer(
    message, processing, context, q: dict, session: dict, user_answer: str,
) -> int:
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

    await processing.edit_text(
        feedback, reply_markup=quiz_next_keyboard(language=_lang(context)), parse_mode="HTML"
    )
    return QUIZ_ANSWERING


async def _reject_non_short_answer(message, context, q: dict) -> int:
    msg = "Voice answers are only supported for short-answer questions."
    if q.get("options"):
        await message.reply_text(
            msg,
            reply_markup=answer_options_keyboard(q["options"], language=_lang(context)),
        )
    else:
        await message.reply_text(msg)
    return QUIZ_ANSWERING


async def _show_quiz_result(update: Update, context, session: dict) -> None:
    total = session.get("total", 0)
    correct = session.get("correct", 0)
    score_pct = round(correct / total * 100) if total else 0
    stars = ":star:" * min(score_pct // 20, 5)
    await update.effective_message.reply_text(
        t(
            "quiz.result",
            _lang(context),
            correct=correct,
            total=total,
            score=score_pct,
            stars=stars,
        ),
        reply_markup=quiz_result_keyboard(language=_lang(context)),
    )


def _lang(context) -> str:
    return context.user_data.get("language", "en")
