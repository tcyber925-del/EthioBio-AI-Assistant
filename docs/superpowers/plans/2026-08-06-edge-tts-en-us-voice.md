# edge-tts en-US Voice Swap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace edge-tts English voice `en-US-JennyNeural` with `en-US-AriaNeural`, made env-configurable (voice + rate/pitch/volume prosody) with neutral defaults.

**Architecture:** Add five pydantic-settings fields to `src/config.py`; `EdgeTTSProvider` reads them at synthesize-time (matching the `gemini.py` pattern of reading `settings` at call time) and passes prosody kwargs to `edge_tts.Communicate`. The 2-letter `am`/`en` language contract and `resolve_tts_language()` clamping are untouched.

**Tech Stack:** Python 3.12+, pydantic-settings, edge-tts, pytest-asyncio (auto mode), ruff, mypy.

---

### Task 1: Settings fields + `.env.example`

**Files:**
- Modify: `src/config.py:46-50` (Whisper/Voice block)
- Modify: `.env.example:51-59` (Whisper/Voice block)

- [ ] **Step 1: Add settings fields**

In `src/config.py`, after `whisper_model: str = "base"` (line 50), add:

```python
    # edge-tts voice mapping (env-tunable; see .env.example)
    edge_tts_en_voice: str = "en-US-AriaNeural"  # was en-US-JennyNeural (poor accent)
    edge_tts_am_voice: str = "am-ET-AmehaNeural"
    edge_tts_rate: str = "+0%"
    edge_tts_pitch: str = "+0Hz"
    edge_tts_volume: str = "+0%"
```

- [ ] **Step 2: Document in `.env.example`**

In `.env.example`, after line 55 (`AZURE_SPEECH_REGION=`), add:

```
EDGE_TTS_EN_VOICE=en-US-AriaNeural
EDGE_TTS_AM_VOICE=am-ET-AmehaNeural
EDGE_TTS_RATE=+0%
EDGE_TTS_PITCH=+0Hz
EDGE_TTS_VOLUME=+0%
```

- [ ] **Step 3: Verify settings load**

Run: `python -c "from src.config import settings; assert settings.edge_tts_en_voice == 'en-US-AriaNeural'; assert settings.edge_tts_rate == '+0%'; print('ok')"`
Expected: prints `ok`

- [ ] **Step 4: Commit**

```bash
git add src/config.py .env.example
git commit -m "feat(config): env-configurable edge-tts voice and prosody"
```

---

### Task 2: Failing tests for voice selection

**Files:**
- Create: `tests/test_edge_tts_provider.py`

- [ ] **Step 1: Write the failing tests**

```python
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

    monkeypatch.setattr(
        "src.voice.providers.edge_tts.edge_tts.Communicate", fake_communicate
    )
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_edge_tts_provider.py -v`
Expected: FAIL — voice is still `en-US-JennyNeural` (tests 1, 2, 3, 5) and `Communicate` receives no prosody kwargs (test 4). `test_voice_is_env_configurable` passes trivially today since `edge_tts_en_voice` doesn't exist yet (settings fixture default); it must fail too.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_edge_tts_provider.py
git commit -m "test(voice): failing tests for configured edge-tts voice and prosody"
```

---

### Task 3: Implement provider changes

**Files:**
- Modify: `src/voice/providers/edge_tts.py` (whole file, 80 lines)

- [ ] **Step 1: Rewrite `edge_tts.py`**

```python
import io
from typing import Optional

import edge_tts
import structlog

from src.config import settings

from .base import SpeechProvider
from .types import SpeechProviderInfo, SynthesisResult

logger = structlog.get_logger(__name__)


def _voice_for(language: Optional[str]) -> str:
    """Map a clamped am/en language code to the configured edge-tts voice."""
    if language == "am":
        return settings.edge_tts_am_voice
    return settings.edge_tts_en_voice


class EdgeTTSProvider(SpeechProvider):
    """Text-to-speech provider using Microsoft Edge's online TTS service.

    Free, no API key required. Supports Amharic (am-ET-AmehaNeural)
    and English (en-US-AriaNeural) voices, both env-configurable.
    """

    @property
    def name(self) -> str:
        return "edge-tts"

    async def transcribe(
        self,
        audio: bytes,
        language: Optional[str] = None,
        mime_type: str = "audio/ogg",
    ):
        raise NotImplementedError("EdgeTTSProvider does not support STT")

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
    ) -> SynthesisResult:
        voice_name = voice or _voice_for(language)
        communicate = edge_tts.Communicate(
            text,
            voice_name,
            rate=settings.edge_tts_rate,
            pitch=settings.edge_tts_pitch,
            volume=settings.edge_tts_volume,
        )
        buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buffer.write(chunk["data"])
        audio_bytes = buffer.getvalue()
        return SynthesisResult(
            audio_bytes=audio_bytes,
            format="mp3",
            duration_seconds=_estimate_duration(audio_bytes),
        )

    async def is_available(self) -> bool:
        try:
            communicate = edge_tts.Communicate("test", settings.edge_tts_en_voice)
            async for _ in communicate.stream():
                break
            return True
        except Exception:
            return False

    def get_info(self) -> SpeechProviderInfo:
        return SpeechProviderInfo(
            name="edge-tts",
            provider_type="edge",
            supported_languages=["am", "en"],
            stt_supported=False,
            tts_supported=True,
            is_healthy=True,
        )


def _estimate_duration(audio_bytes: bytes) -> float:
    """Rough estimate: ~16 KB/s for MP3 speech at 128 kbps."""
    return len(audio_bytes) / (16 * 1024)
```

- [ ] **Step 2: Run the new tests**

Run: `pytest tests/test_edge_tts_provider.py -v`
Expected: all 5 PASS

- [ ] **Step 3: Commit**

```bash
git add src/voice/providers/edge_tts.py
git commit -m "feat(voice): env-configurable edge-tts voice and prosody, en-US-AriaNeural default"
```

---

### Task 4: Full verification

- [ ] **Step 1: Unit test suite**

Run: `pytest tests/ -v -k "not slow"`
Expected: all pass (no other test asserts a voice name; `test_voice_integration.py` uses `language="en"` only)

- [ ] **Step 2: Lint + typecheck**

Run: `ruff check . && mypy src/`
Expected: clean

- [ ] **Step 3: Manual smoke test**

Run: `python -c "
import asyncio
from src.voice.providers import EdgeTTSProvider

async def main():
    result = await EdgeTTSProvider().synthesize('Hello, this is a clearer American English voice.', language='en')
    print('bytes:', len(result.audio_bytes), 'format:', result.format)

asyncio.run(main())
"`
Expected: prints `bytes: <n> format: mp3` with no exception

- [ ] **Step 4: Commit**

```bash
git commit -m "docs: note en-US-AriaNeural default" --allow-empty  # only if follow-up docs changed; otherwise skip
```

(If no follow-up docs changed, skip this step entirely.)

---

## Self-Review

**Spec coverage:**
- Settings fields → Task 1 ✓
- `.env.example` → Task 1 ✓
- Provider helper + prosody kwargs → Task 3 ✓
- `is_available`/docstring use configured EN voice → Task 3 ✓
- New unit tests → Task 2 ✓
- Amharic untouched → Task 2 `test_amharic_uses_ameha_voice` ✓
- AGENTS.md gotcha #14 still valid — no changes needed ✓

**Placeholders:** none — every step has exact code/commands.

**Type consistency:** `_voice_for(language: Optional[str]) -> str` used in `synthesize` and matches `LANGUAGE_VOICES` removal; `captured["kwargs"]` asserted as `{"rate", "pitch", "volume"}` matches `Communicate` call kwargs order/names.
