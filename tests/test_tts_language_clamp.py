"""Regression tests: TTS output language must always be clamped to am/en.

Bug: TTS output language could be None/"both"/arbitrary, so providers
(especially Gemini, which auto-detects text language) could speak any
language even though the platform only supports Amharic and English.
"""

import pytest

from src.voice.providers.registry import SpeechProviderRegistry
from src.voice.providers.types import (
    SynthesisResult,
    normalize_language_code,
    resolve_tts_language,
)

AMHARIC_TEXT = "ሰላም ዓለም ይህ የባዮሎጂ ጥያቄ ነው"
ENGLISH_TEXT = "Hello, this is a biology question"


class TestResolveTtsLanguage:
    """resolve_tts_language() must always return exactly 'am' or 'en'."""

    def test_explicit_am(self):
        assert resolve_tts_language("am") == "am"

    def test_explicit_en(self):
        assert resolve_tts_language("en") == "en"

    def test_locale_tags(self):
        assert resolve_tts_language("am-ET") == "am"
        assert resolve_tts_language("en-US") == "en"

    def test_whisper_full_names(self):
        assert resolve_tts_language("amharic") == "am"
        assert resolve_tts_language("english") == "en"

    def test_none_with_amharic_text(self):
        assert resolve_tts_language(None, AMHARIC_TEXT) == "am"

    def test_none_with_english_text(self):
        assert resolve_tts_language(None, ENGLISH_TEXT) == "en"

    def test_none_without_text_defaults_en(self):
        assert resolve_tts_language(None) == "en"

    def test_empty_string_behaves_like_none(self):
        assert resolve_tts_language("", AMHARIC_TEXT) == "am"
        assert resolve_tts_language("", ENGLISH_TEXT) == "en"

    def test_both_sniffs_text_script(self):
        assert resolve_tts_language("both", AMHARIC_TEXT) == "am"
        assert resolve_tts_language("both", ENGLISH_TEXT) == "en"

    def test_unsupported_language_falls_back_to_text_sniff(self):
        """Unsupported codes (fr, or, so...) must never pass through."""
        assert resolve_tts_language("fr", AMHARIC_TEXT) == "am"
        assert resolve_tts_language("oromoo", ENGLISH_TEXT) == "en"

    def test_mixed_text_with_any_ethiopic_is_am(self):
        assert resolve_tts_language(None, "Photosynthesis ማለት") == "am"

    def test_result_is_always_am_or_en(self):
        for lang in (None, "", "both", "am", "en", "fr", "swahili", "zh-CN"):
            for text in ("", AMHARIC_TEXT, ENGLISH_TEXT):
                assert resolve_tts_language(lang, text) in ("am", "en")


class _CapturingTTSProvider:
    """Fake TTS provider that records the language it was called with."""

    def __init__(self):
        self.seen_languages: list[str | None] = []

    async def synthesize(self, text, voice=None, language=None):
        self.seen_languages.append(language)
        return SynthesisResult(audio_bytes=b"fake-audio", format="mp3")

    async def transcribe(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError

    async def is_available(self):
        return True


@pytest.fixture
def capture_registry(monkeypatch):
    """Registry with a single fake TTS provider (no network, no settings)."""
    registry = SpeechProviderRegistry.__new__(SpeechProviderRegistry)
    registry._stt_providers = {}
    registry._tts_providers = {}
    registry._stt_fallback_chain = []
    registry._tts_fallback_chain = []
    registry._breakers = {}
    fake = _CapturingTTSProvider()
    registry._tts_providers["fake"] = fake
    registry._tts_fallback_chain = ["fake"]
    return registry, fake


class TestRegistryClampsTtsLanguage:
    """Providers must never receive None/''/'both'/unsupported languages."""

    async def test_none_language_is_clamped(self, capture_registry):
        registry, fake = capture_registry
        await registry.synthesize(ENGLISH_TEXT, language=None)
        assert fake.seen_languages == ["en"]

    async def test_none_language_with_amharic_text(self, capture_registry):
        registry, fake = capture_registry
        await registry.synthesize(AMHARIC_TEXT, language=None)
        assert fake.seen_languages == ["am"]

    async def test_both_language_is_resolved(self, capture_registry):
        registry, fake = capture_registry
        await registry.synthesize(AMHARIC_TEXT, language="both")
        await registry.synthesize(ENGLISH_TEXT, language="both")
        assert fake.seen_languages == ["am", "en"]

    async def test_unsupported_language_never_reaches_provider(self, capture_registry):
        registry, fake = capture_registry
        await registry.synthesize(ENGLISH_TEXT, language="fr")
        assert fake.seen_languages[0] in ("am", "en")

    async def test_explicit_languages_pass_through(self, capture_registry):
        registry, fake = capture_registry
        await registry.synthesize(ENGLISH_TEXT, language="en")
        await registry.synthesize(AMHARIC_TEXT, language="am")
        assert fake.seen_languages == ["en", "am"]


class TestNormalizeLanguageCodeUnchanged:
    """Guard: existing STT normalization behavior must not change."""

    def test_still_returns_none_for_unknown(self):
        assert normalize_language_code("swahili") is None
        assert normalize_language_code(None) is None

    def test_still_maps_known(self):
        assert normalize_language_code("amharic") == "am"
        assert normalize_language_code("en-US") == "en"
