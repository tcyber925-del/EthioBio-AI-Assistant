import io

import structlog
from sqlalchemy import select
from telegram.ext import ContextTypes

from src.config import settings
from src.core.audio_storage import AudioStorageService
from src.core.conversation.service import ConversationService as _ConversationService
from src.database.models import User
from src.database.session import async_session_factory
from src.voice.gateways import TelegramVoiceAdapter
from src.voice.providers import SpeechProviderRegistry
from telegram import Update

logger = structlog.get_logger(__name__)

_registry = SpeechProviderRegistry()
_conversation_service = _ConversationService()
_audio_storage = AudioStorageService()

MAX_TTS_LENGTH = 2000


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

        transcript = await _registry.transcribe(audio_bytes, language=language)

        async with async_session_factory()() as db:
            await _audio_storage.save(
                audio_bytes=audio_bytes,
                transcript=transcript.text,
                session=db,
                user_id=str(user.id),
                language=language,
                mime_type="audio/ogg",
                direction="user",
            )

            adapter = TelegramVoiceAdapter(context, language)
            conv_request = adapter.build_request((audio_bytes, transcript.text))

            conv_response = await _conversation_service.process(conv_request, db)

        reply_text = adapter.extract_response(conv_response)
        await _reply_text(message, reply_text, processing_msg)
        if conv_response.response:
            await _reply_audio(message, reply_text, language)
    except Exception as e:
        logger.error("voice_handler_error", error=str(e), exc_info=True)
        await processing_msg.edit_text(
            "Sorry, I couldn't process that voice message. "
            "Please try again or type your question instead."
        )


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
    return "am"


async def _reply_text(message, response: str, processing_msg) -> None:
    if len(response) > 4096:
        await processing_msg.edit_text(response[:4096] + "...")
    else:
        await processing_msg.edit_text(response)


async def _reply_audio(message, text: str, language: str) -> None:
    if len(text) > MAX_TTS_LENGTH:
        text = text[: MAX_TTS_LENGTH - 3] + "..."
    try:
        synthesis = await _registry.synthesize(text, language=language)
        audio = io.BytesIO(synthesis.audio_bytes)
        audio.name = "reply.mp3"
        await message.reply_voice(voice=audio)

        async with async_session_factory()() as db:
            await _audio_storage.save(
                audio_bytes=synthesis.audio_bytes,
                transcript=text,
                session=db,
                language=language,
                mime_type="audio/mp3",
                direction="assistant",
            )
    except Exception as e:
        logger.warning("tts_synthesis_failed", error=str(e))
