import base64
import binascii
import io
import json
import time

import structlog
from sqlalchemy import select
from telegram.ext import ContextTypes

from src.config import settings
from src.core.audio_storage import AudioStorageService
from src.core.conversation.service import ConversationService as _ConversationService
from src.database.models import User
from src.database.session import async_session_factory
from src.voice.gateways import TelegramVoiceAdapter
from src.voice.gateways.telegram import VOICE_SESSION_KEY
from src.voice.providers import SpeechProviderRegistry
from telegram import Update

logger = structlog.get_logger(__name__)

_registry = SpeechProviderRegistry()
_conversation_service = _ConversationService()
_audio_storage = AudioStorageService()

MAX_TTS_LENGTH = 2000
MAX_TEXT_REPLY = 4096
EDIT_THROTTLE_CHARS = 120
EDIT_MIN_CHARS = 120
EDIT_MAX_PREVIEW = 2000


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.voice:
        return

    user = update.effective_user
    if not user:
        return

    processing_msg = await message.reply_text("Processing your voice message...")

    try:
        audio_bytes = await _download_voice(message)

        language = await _resolve_language(user.id, context)
        db_user = await _resolve_db_user(user.id)

        transcript = await _registry.transcribe(audio_bytes, language=language)
        effective_language = language or transcript.language or "en"

        async with async_session_factory()() as db:
            await _audio_storage.save(
                audio_bytes=audio_bytes,
                transcript=transcript.text,
                session=db,
                user_id=str(db_user.id) if db_user else None,
                language=effective_language,
                mime_type="audio/ogg",
                direction="user",
            )

            adapter = TelegramVoiceAdapter(context, effective_language)
            conv_request = adapter.build_request((audio_bytes, transcript.text))

            reply_text, audio_out, session_id = await _stream_voice_turn(
                conv_request, db, processing_msg
            )

        if session_id and context.user_data is not None:
            context.user_data[VOICE_SESSION_KEY] = session_id

        if reply_text:
            await _reply_text(message, reply_text, processing_msg)
        if audio_out:
            await _reply_audio(message, audio_out, reply_text, effective_language)
    except Exception as e:
        logger.error("voice_handler_error", error=str(e), exc_info=True)
        await processing_msg.edit_text(
            "Sorry, I couldn't process that voice message. "
            "Please try again or type your question instead."
        )


async def _stream_voice_turn(
    conv_request,
    db,
    processing_msg,
) -> tuple[str, bytes, str]:
    """Consume the streaming voice pipeline (STT → tokens → TTS audio).

    Mirrors the web app's voice-turn SSE flow: accumulates answer text and
    reassembles base64 audio chunks, throttling live edits to the
    "Processing..." message. Returns (answer_text, audio_bytes, session_id).
    """
    text_parts: list[str] = []
    audio_chunks: list[bytes] = []
    session_id = ""
    last_edit_at = 0.0
    last_edit_len = 0

    async for raw_line in _conversation_service.voice_turn_stream(conv_request, db):
        if not raw_line.startswith("data: "):
            continue
        try:
            chunk = json.loads(raw_line[6:])
        except json.JSONDecodeError:
            continue

        if chunk.get("error"):
            raise RuntimeError(chunk["error"])

        if chunk.get("audio_b64"):
            try:
                audio_chunks.append(base64.b64decode(chunk["audio_b64"]))
            except (ValueError, binascii.Error):
                logger.warning("voice_stream_audio_decode_failed")
            continue

        if chunk.get("status"):
            continue

        delta = chunk.get("delta")
        if delta:
            text_parts.append(delta)

        if chunk.get("metadata") and chunk["metadata"].get("session_id"):
            session_id = chunk["metadata"]["session_id"]

        accumulated = "".join(text_parts)
        now = time.monotonic()
        if (
            accumulated
            and len(accumulated) >= EDIT_MIN_CHARS
            and len(accumulated) - last_edit_len >= EDIT_THROTTLE_CHARS
            and now - last_edit_at >= 1.0
        ):
            last_edit_at = now
            last_edit_len = len(accumulated)
            try:
                await processing_msg.edit_text(accumulated[:EDIT_MAX_PREVIEW] + "...")
            except Exception as edit_e:
                logger.debug("voice_stream_preview_edit_failed", error=str(edit_e))

        if chunk.get("done"):
            break

    return "".join(text_parts).strip(), b"".join(audio_chunks), session_id


async def _download_voice(message) -> bytes:
    voice = message.voice
    file = await voice.get_file()

    if file.file_size and file.file_size > settings.telegram_voice_max_size:
        raise ValueError(f"Voice file too large: {file.file_size} bytes")

    raw = await file.download_as_bytearray()
    return bytes(raw)


async def _resolve_db_user(telegram_id: int):
    """Resolve the linked dashboard account (users.id UUID) for a Telegram user."""
    async with async_session_factory()() as db:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def _resolve_language(telegram_id: int, context) -> str:
    session_lang = context.user_data.get("language")
    if session_lang:
        return "" if session_lang == "both" else session_lang
    user = await _resolve_db_user(telegram_id)
    if user and user.language:
        lang = user.language
        return "" if lang == "both" else lang
    return ""


async def _reply_text(message, response: str, processing_msg) -> None:
    if len(response) > MAX_TEXT_REPLY:
        await processing_msg.edit_text(response[:MAX_TEXT_REPLY] + "...")
    else:
        await processing_msg.edit_text(response)


async def _reply_audio(message, audio_bytes: bytes, text: str, language: str) -> None:
    try:
        audio = io.BytesIO(audio_bytes)
        audio.name = "reply.mp3"
        await message.reply_voice(voice=audio)

        async with async_session_factory()() as db:
            await _audio_storage.save(
                audio_bytes=audio_bytes,
                transcript=text[:MAX_TTS_LENGTH],
                session=db,
                language=language,
                mime_type="audio/mp3",
                direction="assistant",
            )
    except Exception as e:
        logger.warning("tts_synthesis_failed", error=str(e))
