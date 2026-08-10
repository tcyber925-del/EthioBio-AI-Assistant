# Addis AI × EthioBio Voice Engine — Integration Research

**Date:** 2026-08-10 · **Status:** research/assessment only — no implementation.
**Source docs verified:** adisdev docs (contract verified 2026-07-23), PyPI `addisai` 0.2.0 JSON metadata.
Every claim is tagged **[DOC]** (documented) or **[ASSUMPTION]** (inference; verify before building).

## 1. Addis AI platform facts

| Item | Fact | Tag | Source |
|---|---|---|---|
| Base URL | `https://api.addisassistant.com` | DOC | https://docs.addisassistant.com/docs/get-started/quickstart |
| Auth | `x-api-key` header, `sk_...` keys; SDK reads `ADDIS_API_KEY` env | DOC | same |
| Python SDK | `addisai` on PyPI, v0.2.0 (2026-07-18), Python ≥3.8, httpx-based, MIT, **sync-only** (async `AsyncAddisAI` planned) | DOC | https://pypi.org/pypi/addisai/json |
| LLM model | `Addis-፩-አሌፍ` (SDK id `addis-1-alef`), 128k context, 4096 max output, stateless (`conversation_history`), persona/system, function calling (non-streaming), streaming beta | DOC | https://docs.addisassistant.com/docs/capabilities/text-generation |
| LLM pricing | 0.3 ETB / 1k input tokens, 0.8 ETB / 1k output | DOC | https://docs.addisassistant.com/docs/platform/pricing |
| Amharic token density | ≈1 word = 1.5–1.8 tokens | DOC | https://docs.addisassistant.com/docs/capabilities/text-generation |

## 2. STT — addis-whisper

- POST `https://api.addisassistant.com/api/v2/stt`, `multipart/form-data`; fields `audio` (file) + `request_data` (JSON string: `{"language_code": "am"}`). Headers: `x-api-key`. [DOC]
- Response: `{"status":"success","data":{"transcription": "...", "usage_metadata": {"totalBilledDuration": "15s","requestId": "..."}},"confidence": 0.982}` [DOC]
- Formats: WAV, MP3, M4A, WebM (WAV fastest). **OGG/Opus NOT listed** — Telegram voice notes are OGG/Opus → conversion or verification needed. [DOC + ASSUMPTION]
- Limits: max 60 s duration, max 10 MB file. Mono preferred, 16 kHz+ recommended. [DOC]
- Best case WER < 10% in quiet, single-speaker, 10–30 cm. No partial transcripts documented. [DOC]
- Pricing: **3.5 ETB / 1,000 transcribed characters**. [DOC]
- Source: https://docs.addisassistant.com/docs/capabilities/speech-to-text

## 3. TTS — Addis Voices 2

- POST `https://api.addisassistant.com/api/v1/voice/generations`; body `text`, `voice_id`, `language` (`am`/`om`), `output_format` (`mp3_44100` | `wav_44100` | `pcm_16000`), optional `client_request_id` (idempotency). [DOC]
- Response: durable clip metadata + signed `audio_url` (first response may include an inline data URL; replay may not → always use signed URL). [DOC]
- **Does not stream partial audio**; billed **5 ETB per generated minute**; estimate endpoint `POST /api/v1/voice/estimate` before generation. [DOC]
- Voice catalog: `GET /api/v1/voice/voices?language=am` (filters: language, gender, search, include_unavailable); canonical example `am-hamen`; 19 Amharic + 9 Afan Oromo voices live at doc verification date; **availability can change without a docs release** → call `voices.list()` at runtime. [DOC]
- Preview: `GET /api/v1/voice/voices/{id}/preview` (signed, expiring). [DOC]
- `speed` applied; `stability`/`similarity`/`style` accepted but ignored (`meta.ignoredVoiceSettings`). [DOC]
- Idempotency: reuse `client_request_id` only when retrying the same logical generation (avoids double-billed clips); "generation-in-progress" responses have a retry interval. [DOC]
- Best practices: split long text at natural boundaries (no partial streaming), persist clip IDs, log clip/request/client-request IDs never keys. [DOC]
- Legacy Voice 1 API (`/api/v1/audio`, base64 WAV) still available, same key. [DOC]
- Source: https://docs.addisassistant.com/docs/capabilities/text-to-speech

## 4. Realtime API — አሌፍ-1.2-realtime-audio

- WebSocket `wss://relay.addisassistant.com/ws?apiKey=YOUR_API_KEY` (query param auth; for production the docs' demo notes say issue short-lived auth from backend — mechanism not yet documented). [DOC]
- <300 ms response time; bidirectional audio; natural interruptions/back-channeling; **server-side VAD** currently. [DOC]
- Input: **PCM16 LE, 16 kHz mono**, sent as JSON envelope `{"data": <base64>, "mimeType": "audio/pcm;rate=16000"}`. [DOC]
- Output: **PCM16 mono, typically 24 kHz**, under `serverContent.modelTurn.parts[0].inlineData.data` (base64). [DOC]
- Handshake: wait for `{"setupComplete": true}` or `{"type":"status","message":"Ready to start conversation"}` before streaming. [DOC]
- Turn end + billing: `{"serverContent":{"turnComplete":true},"usageMetadata":{"totalBilledAudioDurationSeconds":5.2}}`. [DOC]
- Warnings (billing), errors `{"error":{"message","status","timestamp"}}`; close 1006 → wrong endpoint / bad apiKey / binary instead of JSON envelopes. [DOC]
- Pricing: 1 ETB / 1k input tokens, 4 ETB / 1k output tokens (tokens, not seconds — unit mismatch with per-minute TTS). [DOC]
- **Knowledge Base (RAG attach) is "Coming Soon"** — sessions cannot be grounded on our curriculum today. [DOC]
- Source: https://docs.addisassistant.com/docs/capabilities/realtime

## 5. Platform

- Rate limits: Free 60 RPM / 1,000 RPD / 40k TPM / 3 concurrent; Pro 500 RPM / unlimited / 250k TPM / 50 concurrent; enterprise custom. Headers `x-ratelimit-limit|remaining|reset-requests`. 429 → exponential backoff. [DOC] https://docs.addisassistant.com/docs/platform/limits
- Errors: standard HTTP codes; JSON `{"status":"error","error":{"code","message","param"}}`; 401 invalid key, 429 rate limit, 500/503 retry. [DOC] https://docs.addisassistant.com/docs/platform/errors
- SDK error classes: `InsufficientCreditsError` (with `available_balance`), `RateLimitError` (`retry_after`), `APIError` (`status/code/details`); SDK auto-retries 408/409/425/429/5xx (max 2). [DOC] https://pypi.org/pypi/addisai/json
- Billing: native ETB; wallet balance; low-balance warnings; developer platform is authoritative for account-specific pricing. [DOC] https://docs.addisassistant.com/docs/platform/pricing

## 6. VUI reference pattern

- Server-side orchestrator: STT (transcribe) → LLM (chat) → TTS (voice.generate) in one server endpoint; client uploads WAV/MP3 16 kHz and plays the returned clip URL. [DOC] https://docs.addisassistant.com/docs/integration/voice-interface
- Latency guidance: parallel/segmented TTS clips (no partial streaming); realtime API for sub-300 ms conversational experience; client-side VAD 500–1000 ms silence; keep session context in `messages`. [DOC] same

## 7. EthioBio voice engine (repo facts — src/voice/)

- `SpeechProvider` ABC: `transcribe(audio, language, mime_type) -> TranscriptResult`, `synthesize(text, voice, language) -> SynthesisResult`, `is_available`, `check_health`, `get_info`, `name` (`src/voice/providers/base.py:7-43`).
- `TranscriptResult(text, language, language_confidence, duration_seconds, segments)`; `SynthesisResult(audio_bytes, format, duration_seconds)` (`src/voice/providers/types.py:68-81`).
- Config-driven registry `SpeechProviderRegistry._init_providers()` (`src/voice/providers/registry.py:46-68`); per-provider `CircuitBreaker` (threshold 5, 30 s recovery); fallback chains; metrics `STTTimer`/`TTSTimer` (`src/observability/voice_metrics.py`).
- Language: `normalize_language_code` + `resolve_tts_language` hard-clamp to `am`/`en` (`src/voice/providers/types.py:20-65`).
- No WebSockets anywhere. Voice = chunked REST (`/chat/voice/chunk`) + SSE (`/chat/voice/turn`, feature flag `voice_turn_enabled` default False) + full-audio TTS (`POST /chat/tts`).
- Voice turn loop: `run_graph` → stream `TokenChunk` SSE → `synthesize()` entire answer → 15 KB `audio_b64` chunks (`src/core/conversation/service.py:283-417`).
- Telegram voice notes are OGG/Opus; sent back as voice notes via `reply_voice` (`src/telegram/voice_handler.py:189-203`). VAD detector exists but unwired (`src/voice/vad/detector.py`).
- Stream-session chunk flow + partials exist for Groq only (`src/voice/streaming/session.py`, `src/api/chat.py:108-164`).

## 8. Key open questions (must verify before building)

1. OGG/Opus (Telegram) accepted by `/api/v2/stt`? Not in the documented list → transcode-to-WAV path or live test.
2. English STT — SDK README lists `am|om|en|ha|sw` but the STT docs only document Amharic/Oromo; English accuracy unknown.
3. STT latency, TTS latency — no figures published; benchmark needed.
4. Realtime short-lived-auth mechanism ("issue short-lived auth from your backend") — not specified in docs (demo only). Current auth = API key in WS query string.
5. No partial transcripts from STT; no streaming TTS — both impact the existing partial-transcript UX.
6. Realtime RAG/context attach not yet available — blocks curriculum-grounded realtime tutoring.
7. Voice catalog churn — must implement `voices.list()` at startup + refresh.