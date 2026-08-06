import pytest

from src.config import settings
from src.voice.providers import EdgeTTSProvider


class _FakeCommunicate:
    def __init__(self, text, voice, **kwargs):
        self.text = text
        self.voice = voice
        self.kwargs = kwargs

    async def stream(self):
        yield {"type": "audio", "data": b"\xff" * 16000}


@pytest.fixture
def captured():
    return {}


@pytest.fixture
def patch_communicate(monkeypatch, captured):
    def fake_communicate(text, voice, **kwargs):
        captured["text"] = text
        captured["voice"] = voice
        captured["kwargs"] = kwargs
        return _FakeCommunicate(text, voice, **kwargs)

    monkeypatch.setattr("src.voice.providers.edge_tts.edge_tts.Communicate", fake_communicate)
    return captured


async def test_english_uses_configured_en_voice(patch_communicate):
    result = await EdgeTTSProvider().synthesize("Hello", language="en")
    assert patch_communicate["voice"] == "en-US-AriaNeural"
    assert result.format == "mp3"


async def test_amharic_uses_ameha_voice(patch_communicate):
    await EdgeTTSProvider().synthesize("ሰላም", language="am")
    assert patch_communicate["voice"] == "am-ET-AmehaNeural"


async def test_voice_is_env_configurable(patch_communicate, monkeypatch):
    monkeypatch.setattr(settings, "edge_tts_en_voice", "en-US-GuyNeural")
    await EdgeTTSProvider().synthesize("Hello", language="en")
    assert patch_communicate["voice"] == "en-US-GuyNeural"


async def test_prosody_kwargs_passed(patch_communicate, monkeypatch):
    monkeypatch.setattr(settings, "edge_tts_rate", "+8%")
    monkeypatch.setattr(settings, "edge_tts_pitch", "-2Hz")
    monkeypatch.setattr(settings, "edge_tts_volume", "+10%")
    await EdgeTTSProvider().synthesize("Hello", language="en")
    assert patch_communicate["kwargs"] == {"rate": "+8%", "pitch": "-2Hz", "volume": "+10%"}


async def test_is_available_uses_configured_en_voice(patch_communicate):
    await EdgeTTSProvider().is_available()
    assert patch_communicate["voice"] == "en-US-AriaNeural"
