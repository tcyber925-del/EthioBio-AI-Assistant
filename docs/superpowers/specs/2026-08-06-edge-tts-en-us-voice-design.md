# edge-tts English Voice → en-US-AriaNeural (Env-Configurable)

Date: 2026-08-06
Status: Approved

## Problem

English TTS output from edge-tts (the only active TTS provider; no `GEMINI_API_KEY`
or Azure keys are set in `.env`) uses `en-US-JennyNeural`. The voice is perceived as
having a poor accent and is not heard clearly. Note: the locale was already `en-US`;
the complaint is about the Jenny voice itself, not the locale.

## Goals

- Replace the English voice with `en-US-AriaNeural` (clearer female US voice).
- Make the voice mapping env-configurable so it can be tuned without a code deploy.
- Add configurable prosody (rate/pitch/volume) with neutral defaults (= current behavior).
- Leave Amharic (`am-ET-AmehaNeural`) and the rest of the pipeline untouched.

## Non-Goals

- No changes to Azure provider (not configured; would be dead config — YAGNI).
- No changes to Gemini provider (Kore voice; not in use).
- No change to the 2-letter language contract (`am`/`en`) — `resolve_tts_language()`
  clamping in `src/voice/providers/types.py` is unchanged.

## Design

### 1. Settings (`src/config.py`, Whisper/Voice block ~line 50)

| Field | Default | Notes |
|-------|---------|-------|
| `edge_tts_en_voice` | `en-US-AriaNeural` | was `en-US-JennyNeural` |
| `edge_tts_am_voice` | `am-ET-AmehaNeural` | unchanged |
| `edge_tts_rate` | `+0%` | edge-tts rate override |
| `edge_tts_pitch` | `+0Hz` | edge-tts pitch override |
| `edge_tts_volume` | `+0%` | edge-tts volume override |

### 2. Provider (`src/voice/providers/edge_tts.py`)

- Replace the static `LANGUAGE_VOICES` dict with a `_voice_for(language)` helper that
  reads the configured voices from `settings` at call time.
- `synthesize()` passes `rate`, `pitch`, `volume` to `edge_tts.Communicate(...)`.
- `FALLBACK_VOICE` and `is_available()` use the configured English voice.
- Update the class docstring (Jenny → Aria).

### 3. `.env.example`

Document the 5 new vars under `# Whisper / Voice`.

### 4. Tests

- No existing test asserts a voice name, so nothing breaks.
- Add one unit test: monkeypatch `edge_tts.Communicate` and assert the configured
  voice + prosody kwargs are passed for `en` and `am`.

### 5. Docs

- AGENTS.md gotcha #14 remains valid (registry still clamps to `am`/`en`).

## Error Handling

Invalid voice names fail when streaming starts; the registry's circuit breaker and
fallback chain already handle provider failures. No extra validation added.

## Testing

```bash
pytest tests/ -v -k "not slow"   # unit tests
ruff check . && mypy src/        # lint + typecheck
```
