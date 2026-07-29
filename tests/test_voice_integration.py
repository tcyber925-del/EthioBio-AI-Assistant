"""Integration tests for STT/TTS providers with real API calls.

Run with:  pytest tests/test_voice_integration.py -v --run-slow
Requires:  GROQ_API_KEY env var for Groq tests (edge-tts needs none)
Skipped in CI: pytest -k "not slow"
"""

import os

import pytest
import pytest_asyncio

from src.voice.providers import EdgeTTSProvider, GroqSTTProvider, speech_registry
from src.voice.streaming import AudioChunk, VoiceStreamManager

pytestmark = pytest.mark.slow


def _groq_available() -> bool:
    return bool(os.environ.get("GROQ_API_KEY"))


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="module")
async def english_audio():
    """Generate a known English phrase via edge-tts for STT testing."""
    provider = EdgeTTSProvider()
    result = await provider.synthesize(
        "Hello this is a test of the speech to text system", language="en"
    )
    return result.audio_bytes


@pytest_asyncio.fixture(scope="module")
async def amharic_audio():
    """Generate a known Amharic phrase via edge-tts for STT testing."""
    provider = EdgeTTSProvider()
    result = await provider.synthesize(
        "ሰላም ይህ የድምጽ ሙከራ ነው", language="am"
    )
    return result.audio_bytes


@pytest_asyncio.fixture(scope="module")
async def short_english_chunks():
    """Two short English audio chunks simulating a streaming session."""
    provider = EdgeTTSProvider()
    r1 = await provider.synthesize("Hello", language="en")
    r2 = await provider.synthesize("this is a test", language="en")
    return [
        (r1.audio_bytes, "audio/mpeg"),
        (r2.audio_bytes, "audio/mpeg"),
    ]


# ── Groq STT ────────────────────────────────────────────────────────────


class TestGroqSTT:
    async def test_transcribes_english(self, english_audio):
        if not _groq_available():
            pytest.skip("GROQ_API_KEY not set")
        provider = GroqSTTProvider()
        result = await provider.transcribe(english_audio, language="en", mime_type="audio/mpeg")
        assert result.text
        assert "hello" in result.text.lower() or "test" in result.text.lower()
        assert result.language == "en"

    async def test_transcribes_amharic(self, amharic_audio):
        if not _groq_available():
            pytest.skip("GROQ_API_KEY not set")
        provider = GroqSTTProvider()
        result = await provider.transcribe(amharic_audio, language="am", mime_type="audio/mpeg")
        assert result.text
        assert result.language == "am"

    async def test_handles_webm_mime(self, english_audio):
        """MIME type threading: WebM content type should not break Groq."""
        if not _groq_available():
            pytest.skip("GROQ_API_KEY not set")
        provider = GroqSTTProvider()
        result = await provider.transcribe(
            english_audio, language="en", mime_type="audio/webm;codecs=opus"
        )
        assert result.text
        assert "hello" in result.text.lower()


# ── edge-tts ────────────────────────────────────────────────────────────


class TestEdgeTTS:
    async def test_synthesizes_english(self):
        provider = EdgeTTSProvider()
        result = await provider.synthesize("Hello world", language="en")
        assert result.audio_bytes
        assert len(result.audio_bytes) > 1000
        assert result.format == "mp3"
        assert result.duration_seconds > 0

    async def test_synthesizes_amharic(self):
        provider = EdgeTTSProvider()
        result = await provider.synthesize("ሰላም ዓለም", language="am")
        assert result.audio_bytes
        assert len(result.audio_bytes) > 1000
        assert result.format == "mp3"

    async def test_is_available(self):
        provider = EdgeTTSProvider()
        assert await provider.is_available() is True


# ── Registry fallback chain ─────────────────────────────────────────────


class TestSpeechRegistry:
    async def test_synthesize_via_registry(self):
        """Verify the registry can route a TTS request."""
        result = await speech_registry.synthesize("Hello from registry", language="en")
        assert result.audio_bytes
        assert len(result.audio_bytes) > 1000

    async def test_transcribe_via_registry(self, english_audio):
        """Verify the registry can route an STT request."""
        if not _groq_available():
            pytest.skip("GROQ_API_KEY not set")
        result = await speech_registry.transcribe(
            english_audio, language="en", mime_type="audio/mpeg"
        )
        assert result.text


# ── Streaming session + real transcribe ─────────────────────────────────


class TestStreamingIntegration:
    async def test_stream_session_buffer_and_transcribe(self, short_english_chunks):
        """Simulate a streaming session: buffer chunks, then assemble + transcribe."""
        if not _groq_available():
            pytest.skip("GROQ_API_KEY not set")

        manager = VoiceStreamManager(ttl_seconds=300)
        session = manager.get_or_create("test-session-1", language="en")
        provider = GroqSTTProvider()

        for i, (data, mime) in enumerate(short_english_chunks):
            session.buffer.append(
                AudioChunk(data=data, sequence=i, mime_type=mime, is_final=(i == 1))
            )

        assembled = session.buffer.assemble()
        assert len(assembled) > 0

        result = await provider.transcribe(assembled, language="en", mime_type="audio/mpeg")
        assert result.text
        assert "hello" in result.text.lower() or "test" in result.text.lower()

    async def test_partial_chunk_transcribe(self, short_english_chunks):
        """Transcribe a single partial chunk (simulates live partial STT)."""
        if not _groq_available():
            pytest.skip("GROQ_API_KEY not set")

        provider = GroqSTTProvider()
        data, mime = short_english_chunks[0]
        result = await provider.transcribe(data, language="en", mime_type=mime)
        assert result.text
