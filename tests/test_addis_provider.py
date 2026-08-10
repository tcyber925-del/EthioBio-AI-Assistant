import json

import httpx
import pytest

from src.config import settings
from src.voice.providers import AddisProvider, SpeechProviderRegistry

ADDIS_BASE = "https://api.addisassistant.com"
ADDIS_STT_ENDPOINT = f"{ADDIS_BASE}/api/v2/stt"
ADDIS_TTS_ENDPOINT = f"{ADDIS_BASE}/api/v1/voice/generations"

AUDIO_BYTES = b"\x00\x01\x02\x03"


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        return self._responses.pop(0)

    async def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return self._responses.pop(0)


def _install_fake_client(monkeypatch, responses):
    fake = _FakeClient(responses)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: fake)
    return fake


def _stt_response(text="ሰላም", confidence=0.982, duration="15s"):
    return httpx.Response(
        200,
        json={
            "status": "success",
            "data": {
                "transcription": text,
                "usage_metadata": {"totalBilledDuration": duration, "requestId": "req-1"},
            },
            "confidence": confidence,
        },
    )


def _set_key(monkeypatch, key="sk_test"):
    monkeypatch.setattr(settings, "addis_api_key", key)


@pytest.fixture
def provider():
    return AddisProvider()


# ── STT ──────────────────────────────────────────────────────────────────


class TestTranscribe:
    async def test_posts_multipart_and_returns_transcript(self, monkeypatch, provider):
        fake = _install_fake_client(monkeypatch, [_stt_response()])
        _set_key(monkeypatch)

        result = await provider.transcribe(AUDIO_BYTES, language="am", mime_type="audio/wav")

        assert result.text == "ሰላም"
        assert result.language == "am"
        assert result.language_confidence == pytest.approx(0.982)
        assert result.duration_seconds == pytest.approx(15.0)

        method, url, kwargs = fake.calls[0]
        assert method == "post"
        assert url == ADDIS_STT_ENDPOINT
        assert kwargs["headers"] == {"x-api-key": "sk_test"}
        assert kwargs["files"]["audio"] == ("audio.wav", AUDIO_BYTES, "audio/wav")
        assert json.loads(kwargs["data"]["request_data"]) == {"language_code": "am"}

    async def test_omits_language_code_for_auto_detect(self, monkeypatch, provider):
        fake = _install_fake_client(monkeypatch, [_stt_response()])
        _set_key(monkeypatch)

        result = await provider.transcribe(AUDIO_BYTES, mime_type="audio/webm")

        _, _, kwargs = fake.calls[0]
        assert json.loads(kwargs["data"]["request_data"]) == {}
        assert result.language == "am"

    async def test_raises_runtime_error_on_api_error(self, monkeypatch, provider):
        _install_fake_client(monkeypatch, [httpx.Response(500, text="boom")])
        _set_key(monkeypatch)

        with pytest.raises(RuntimeError, match="500"):
            await provider.transcribe(AUDIO_BYTES, language="am")

    async def test_raises_when_not_configured(self, provider):
        with pytest.raises(RuntimeError, match="not configured"):
            await provider.transcribe(AUDIO_BYTES, language="am")


# ── TTS ──────────────────────────────────────────────────────────────────


class TestSynthesize:
    def _generation_response(self, audio_url="https://cdn.example/clip.mp3"):
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {"id": "clip_1", "audio_url": audio_url, "usage": {}},
            },
        )

    async def test_generates_clip_then_fetches_audio(self, monkeypatch, provider):
        fake = _install_fake_client(
            monkeypatch, [self._generation_response(), httpx.Response(200, content=b"\xff" * 100)]
        )
        _set_key(monkeypatch)

        result = await provider.synthesize("ሰላም", language="am")

        assert result.format == "mp3"
        assert result.audio_bytes == b"\xff" * 100

        method, url, kwargs = fake.calls[0]
        assert method == "post"
        assert url == ADDIS_TTS_ENDPOINT
        assert kwargs["headers"] == {"x-api-key": "sk_test"}
        body = kwargs["json"]
        assert body["text"] == "ሰላም"
        assert body["voice_id"] == "am-hamen"
        assert body["language"] == "am"
        assert body["output_format"] == "mp3_44100"
        assert body["client_request_id"]

        method, url, _ = fake.calls[1]
        assert method == "get"
        assert url == "https://cdn.example/clip.mp3"

    async def test_voice_param_overrides_default(self, monkeypatch, provider):
        fake = _install_fake_client(
            monkeypatch, [self._generation_response(), httpx.Response(200, content=b"x")]
        )
        _set_key(monkeypatch)

        await provider.synthesize("ሰላም", voice="am-nejat", language="am")

        _, _, kwargs = fake.calls[0]
        assert kwargs["json"]["voice_id"] == "am-nejat"

    async def test_english_raises_not_implemented(self, monkeypatch, provider):
        _set_key(monkeypatch)

        with pytest.raises(NotImplementedError, match="Amharic"):
            await provider.synthesize("Hello", language="en")

    async def test_raises_on_generation_error(self, monkeypatch, provider):
        _install_fake_client(monkeypatch, [httpx.Response(401, json={"status": "error"})])
        _set_key(monkeypatch)

        with pytest.raises(RuntimeError, match="401"):
            await provider.synthesize("ሰላም", language="am")

    async def test_raises_when_audio_url_missing(self, monkeypatch, provider):
        _install_fake_client(
            monkeypatch,
            [httpx.Response(200, json={"data": {"id": "clip_1", "audio_url": None}})],
        )
        _set_key(monkeypatch)

        with pytest.raises(RuntimeError, match="audio_url"):
            await provider.synthesize("ሰላም", language="am")

    async def test_raises_when_not_configured(self, provider):
        with pytest.raises(RuntimeError, match="not configured"):
            await provider.synthesize("ሰላም", language="am")


# ── Availability / info ──────────────────────────────────────────────────


class TestAvailability:
    async def test_is_available_requires_key(self, monkeypatch, provider):
        monkeypatch.setattr(settings, "addis_api_key", "")
        assert await provider.is_available() is False
        _set_key(monkeypatch)
        assert await provider.is_available() is True

    def test_get_info(self, monkeypatch, provider):
        _set_key(monkeypatch)
        info = provider.get_info()
        assert info.name == "addis"
        assert info.provider_type == "addis"
        assert "am" in info.supported_languages
        assert info.stt_supported is True
        assert info.tts_supported is True


# ── Registry integration ─────────────────────────────────────────────────


class TestRegistry:
    def test_registers_addis_when_key_set(self, monkeypatch):
        _set_key(monkeypatch)
        registry = SpeechProviderRegistry()

        assert "addis" in registry.get_stt_providers()
        assert "addis" in registry.get_tts_providers()
        assert registry.get_provider_status()["stt_fallback_chain"][0] == "addis"
        assert registry.get_provider_status()["tts_fallback_chain"][0] == "addis"

    def test_skips_addis_without_key(self, monkeypatch):
        monkeypatch.setattr(settings, "addis_api_key", "")
        registry = SpeechProviderRegistry()

        assert "addis" not in registry.get_stt_providers()
        assert "addis" not in registry.get_tts_providers()

    async def test_transcribe_routes_through_addis(self, monkeypatch):
        _set_key(monkeypatch)
        _install_fake_client(monkeypatch, [_stt_response(text="ሰላም ዓለም")])
        registry = SpeechProviderRegistry()

        result = await registry.transcribe(AUDIO_BYTES, language="am", mime_type="audio/wav")

        assert result.text == "ሰላም ዓለም"

    async def test_english_tts_falls_back_without_tripping_breaker(
        self, monkeypatch, provider
    ):
        class _FakeCommunicate:
            def __init__(self, text, voice, **kwargs):
                pass

            async def stream(self):
                yield {"type": "audio", "data": b"\xff" * 16000}

        monkeypatch.setattr(
            "src.voice.providers.edge_tts.edge_tts.Communicate", _FakeCommunicate
        )
        _set_key(monkeypatch)
        registry = SpeechProviderRegistry()

        result = await registry.synthesize("Hello world", language="en")

        assert result.format == "mp3"
        breaker = registry._breakers["addis"]
        assert breaker.failure_count == 0
        assert breaker.state == "closed"
