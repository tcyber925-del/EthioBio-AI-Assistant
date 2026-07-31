import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.telegram import quiz_voice, voice_handler
from src.voice.providers.types import normalize_language_code


class TestNormalizeLanguageCode:
    def test_whisper_full_names(self):
        assert normalize_language_code("english") == "en"
        assert normalize_language_code("amharic") == "am"

    def test_known_codes_pass_through(self):
        assert normalize_language_code("en") == "en"
        assert normalize_language_code("am") == "am"
        assert normalize_language_code("both") == "both"

    def test_locale_tags(self):
        assert normalize_language_code("en-US") == "en"
        assert normalize_language_code("am-ET") == "am"

    def test_case_insensitive(self):
        assert normalize_language_code("ENGLISH") == "en"
        assert normalize_language_code("Amharic") == "am"

    def test_none_or_empty(self):
        assert normalize_language_code(None) is None
        assert normalize_language_code("") is None

    def test_unknown_language(self):
        assert normalize_language_code("swahili") is None


class TestResolveLanguage:
    @pytest.mark.asyncio
    async def test_voice_handler_defaults_to_empty_for_auto_detect(self, monkeypatch):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_factory = MagicMock(return_value=mock_session)
        monkeypatch.setattr(
            voice_handler, "async_session_factory", MagicMock(return_value=mock_factory)
        )
        mock_exec = MagicMock()
        mock_exec.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_exec)

        context = SimpleNamespace(user_data={})
        assert await voice_handler._resolve_language(12345, context) == ""

    @pytest.mark.asyncio
    async def test_voice_handler_uses_session_language(self):
        context = SimpleNamespace(user_data={"language": "am"})
        assert await voice_handler._resolve_language(12345, context) == "am"

    @pytest.mark.asyncio
    async def test_voice_handler_both_means_auto_detect(self):
        context = SimpleNamespace(user_data={"language": "both"})
        assert await voice_handler._resolve_language(12345, context) == ""

    @pytest.mark.asyncio
    async def test_quiz_voice_defaults_to_empty_for_auto_detect(self, monkeypatch):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_factory = MagicMock(return_value=mock_session)
        monkeypatch.setattr(
            quiz_voice, "async_session_factory", MagicMock(return_value=mock_factory)
        )
        mock_exec = MagicMock()
        mock_exec.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_exec)

        context = SimpleNamespace(user_data={})
        assert await quiz_voice._resolve_language(12345, context) == ""


class TestStreamVoiceTurn:
    @pytest.mark.asyncio
    async def test_reassembles_text_audio_and_session_id(self, monkeypatch):
        audio_bytes = b"\xff\xfb\x90\x00" * 64
        b64 = base64.b64encode(audio_bytes).decode()

        async def fake_stream(conv_request, db):
            yield f"data: {json.dumps({'delta': '', 'node': 'stt', 'done': False, 'error': None, 'status': False, 'metadata': {'transcript': 'What is DNA?'}})}\n\n"
            yield f"data: {json.dumps({'delta': 'DNA is ', 'node': 'tutor', 'done': False, 'error': None, 'status': False})}\n\n"
            yield f"data: {json.dumps({'delta': 'a molecule.', 'node': 'tutor', 'done': False, 'error': None, 'status': False})}\n\n"
            yield f"data: {json.dumps({'delta': '', 'node': 'audio', 'done': False, 'error': None, 'status': False, 'audio_b64': b64})}\n\n"
            yield f"data: {json.dumps({'delta': '', 'done': True, 'error': None, 'status': False, 'metadata': {'session_id': 'sess-1', 'status': 'approved'}})}\n\n"

        monkeypatch.setattr(voice_handler._conversation_service, "voice_turn_stream", fake_stream)

        processing = SimpleNamespace(edit_text=AsyncMock())
        text, audio, session_id = await voice_handler._stream_voice_turn("req", None, processing)
        assert text == "DNA is a molecule."
        assert audio == audio_bytes
        assert session_id == "sess-1"

    @pytest.mark.asyncio
    async def test_skips_status_events(self, monkeypatch):
        async def fake_stream(conv_request, db):
            yield f"data: {json.dumps({'delta': 'Analyzing...', 'node': 'orchestrator', 'done': False, 'error': None, 'status': True})}\n\n"
            yield f"data: {json.dumps({'delta': 'Answer', 'node': 'tutor', 'done': False, 'error': None, 'status': False})}\n\n"
            yield f"data: {json.dumps({'delta': '', 'done': True, 'error': None, 'status': False, 'metadata': {}})}\n\n"

        monkeypatch.setattr(voice_handler._conversation_service, "voice_turn_stream", fake_stream)

        processing = SimpleNamespace(edit_text=AsyncMock())
        text, audio, session_id = await voice_handler._stream_voice_turn("req", None, processing)
        assert text == "Answer"
        assert audio == b""
        assert session_id == ""

    @pytest.mark.asyncio
    async def test_raises_on_stream_error(self, monkeypatch):
        async def fake_stream(conv_request, db):
            yield f"data: {json.dumps({'delta': '', 'done': True, 'error': 'LLM timeout', 'status': False})}\n\n"

        monkeypatch.setattr(voice_handler._conversation_service, "voice_turn_stream", fake_stream)

        processing = SimpleNamespace(edit_text=AsyncMock())
        with pytest.raises(RuntimeError, match="LLM timeout"):
            await voice_handler._stream_voice_turn("req", None, processing)


class TestHandleVoiceMessage:
    @pytest.mark.asyncio
    async def test_streams_transcribes_and_replies(self, monkeypatch):
        transcript = SimpleNamespace(text="What is DNA?", language="en")
        monkeypatch.setattr(voice_handler, "_download_voice", AsyncMock(return_value=b"audio"))
        monkeypatch.setattr(voice_handler, "_resolve_language", AsyncMock(return_value=""))
        monkeypatch.setattr(
            voice_handler._registry, "transcribe", AsyncMock(return_value=transcript)
        )
        monkeypatch.setattr(voice_handler._audio_storage, "save", AsyncMock())

        audio_bytes = b"\xff\xfb\x90\x00" * 64
        b64 = base64.b64encode(audio_bytes).decode()

        async def fake_stream(conv_request, db):
            yield f"data: {json.dumps({'delta': 'DNA is a molecule.', 'node': 'tutor', 'done': False, 'error': None, 'status': False})}\n\n"
            yield f"data: {json.dumps({'delta': '', 'node': 'audio', 'done': False, 'error': None, 'status': False, 'audio_b64': b64})}\n\n"
            yield f"data: {json.dumps({'delta': '', 'done': True, 'error': None, 'status': False, 'metadata': {'session_id': 's1'}})}\n\n"

        monkeypatch.setattr(voice_handler._conversation_service, "voice_turn_stream", fake_stream)
        monkeypatch.setattr(voice_handler, "_reply_text", AsyncMock())
        monkeypatch.setattr(voice_handler, "_reply_audio", AsyncMock())

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_factory = MagicMock(return_value=mock_session)
        monkeypatch.setattr(
            voice_handler, "async_session_factory", MagicMock(return_value=mock_factory)
        )

        processing = SimpleNamespace(edit_text=AsyncMock())
        message = SimpleNamespace(
            voice=SimpleNamespace(),
            reply_text=AsyncMock(return_value=processing),
            reply_voice=AsyncMock(),
        )
        update = SimpleNamespace(
            effective_message=message, effective_user=SimpleNamespace(id=12345)
        )
        context = SimpleNamespace(user_data={})

        await voice_handler.handle_voice_message(update, context)

        voice_handler._reply_text.assert_awaited_once()
        voice_handler._reply_audio.assert_awaited_once()
        assert context.user_data[voice_handler.VOICE_SESSION_KEY] == "s1"

    @pytest.mark.asyncio
    async def test_uses_detected_language_when_no_hint(self, monkeypatch):
        transcript = SimpleNamespace(text="ሰላም", language="am")
        monkeypatch.setattr(voice_handler, "_download_voice", AsyncMock(return_value=b"audio"))
        monkeypatch.setattr(voice_handler, "_resolve_language", AsyncMock(return_value=""))
        monkeypatch.setattr(
            voice_handler._registry, "transcribe", AsyncMock(return_value=transcript)
        )
        monkeypatch.setattr(voice_handler._audio_storage, "save", AsyncMock())

        captured = {}

        async def fake_stream(conv_request, db):
            captured["language"] = conv_request.language
            yield f"data: {json.dumps({'delta': '', 'done': True, 'error': None, 'status': False, 'metadata': {}})}\n\n"

        monkeypatch.setattr(voice_handler._conversation_service, "voice_turn_stream", fake_stream)
        monkeypatch.setattr(voice_handler, "_reply_text", AsyncMock())
        monkeypatch.setattr(voice_handler, "_reply_audio", AsyncMock())

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_factory = MagicMock(return_value=mock_session)
        monkeypatch.setattr(
            voice_handler, "async_session_factory", MagicMock(return_value=mock_factory)
        )

        processing = SimpleNamespace(edit_text=AsyncMock())
        message = SimpleNamespace(
            voice=SimpleNamespace(),
            reply_text=AsyncMock(return_value=processing),
            reply_voice=AsyncMock(),
        )
        update = SimpleNamespace(
            effective_message=message, effective_user=SimpleNamespace(id=12345)
        )
        context = SimpleNamespace(user_data={})

        await voice_handler.handle_voice_message(update, context)

        assert captured["language"] == "am"
        save_call = voice_handler._audio_storage.save.await_args
        assert save_call.kwargs["language"] == "am"

    @pytest.mark.asyncio
    async def test_error_path_edits_processing_message(self, monkeypatch):
        monkeypatch.setattr(
            voice_handler, "_download_voice", AsyncMock(side_effect=RuntimeError("boom"))
        )

        processing = SimpleNamespace(edit_text=AsyncMock())
        message = SimpleNamespace(
            voice=SimpleNamespace(),
            reply_text=AsyncMock(return_value=processing),
            reply_voice=AsyncMock(),
        )
        update = SimpleNamespace(
            effective_message=message, effective_user=SimpleNamespace(id=12345)
        )
        context = SimpleNamespace(user_data={})

        await voice_handler.handle_voice_message(update, context)

        processing.edit_text.assert_awaited_once()
        assert "couldn't process" in processing.edit_text.await_args.args[0]
