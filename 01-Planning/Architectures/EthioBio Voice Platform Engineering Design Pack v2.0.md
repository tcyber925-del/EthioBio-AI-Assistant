# EthioBio Voice Platform Engineering Design Pack v2.0

### Architecture & Implementation Blueprint

**Version:** 2.3
**Status:** Approved for Implementation
**Audience:** AI Coding Agents & Technical Lead

---

## Changelog

**v2.3 (2026-07-28)** - Conversation contract, Telegram-first validation, and production hardening:

* **Normalized conversation contract defined.** `ConversationRequest` is the sole cross-gateway interface: `user_id`, `conversation_id`, `session_id`, `transcript`, `language`, `language_confidence`, and `modality`. Gateway-native updates, authentication objects, codec details, and provider hints stay inside each adapter.
* **Identity, learning thread, and delivery context separated.** `user_id` preserves learner identity; `conversation_id` identifies the active learning thread; `session_id` scopes a live turn; channel/device data is delivery-only.
* **Telegram batch voice becomes the first end-to-end proof.** M3 delivers `voice note -> STT -> Conversation Service -> LangGraph -> text/TTS reply`; streaming is a subsequent optimization.
* **Reliability, privacy, and observability added.** Idempotency, graceful text fallback, configurable retention, learner deletion, and privacy-safe metrics are now explicit requirements.


**v2.2 (2026-07-28)** — Multi-gateway architecture, mobile strategy, Telegram voice priority:

* **M5 redefined as Gateway Abstraction Layer.** Not "Voice API endpoints" — a set of client-aware adapters (WebVoiceAdapter, TelegramVoiceAdapter, [future] MobileVoiceAdapter) that normalize transport/auth/audio before reaching the Conversation Service. Same service, any gateway.
* **Mobile strategy: PWA-first.** The existing Next.js 14 dashboard already supports Service Workers + WebRTC. Ship voice on the PWA for MVP; native Flutter app deferred to v2 after voice features are validated against real usage.
* **Telegram voice promoted to P1 — ships in M3.** The bot at `src/telegram/bot.py` already has webhook infrastructure and conversation state. Handling `Message.voice` is ~50 lines: download opus → STT → Conversation Service → TTS → upload → send. No frontend work. Ships when the first SpeechProvider lands.
* **Cross-gateway session design rule:** learner identity is keyed by `user_id`; active conversation and live session are separate identifiers. Continuity across web/Telegram/mobile does not conflate simultaneous sessions.
* **Architecture diagram updated** to show the Gateway Layer with adapters between clients and Conversation Service.
* Two existing voice stubs discovered (`src/config.py:43 whisper_model`, `src/llm/router.py:68 _is_voice_request`). Neither wired. Noted for cleanup in M1.

**v2.1 (2026-07-28)** — Provider strategy rewritten from verified research (see `01-Planning/Research/Free Voice STT-TTS Providers — Production Report.md`):

* Azure F0 free tier quantified (5 audio-hrs/mo STT + 0.5M chars/mo TTS, ongoing).
* Addis AI fully verified: 28 voices (19 Amharic + 9 Afaan Oromo — the only Oromo voices in existence), batch-only STT/TTS (no streaming), Realtime API (<300ms, WebSocket), 500 ETB starter credits, ETB pricing.
* New fallback/self-host providers added: Groq (free Whisper API), Cloudflare Workers AI, faster-whisper + OmniVoice Amharic (Apache-2.0, voice cloning), Gemini-TTS (am-ET Preview).
* Ruled out with evidence: Deepgram, Coqui XTTS v2, Meta MMS (license), Google classic Cloud TTS voices (no Amharic). Plan's "Google Speech" entry corrected to Gemini-TTS.
* Language scope set: Amharic + Afaan Oromo; Tigrinya excluded (no provider exists).
* `SpeechProvider` interface aligned to the existing `src/llm/providers/` patterns (ABC, default non-streaming fallbacks, circuit breaker, registry, structlog).

---

# Page 1 — Executive Summary

## Vision

Transform **EthioBio AI Assistant** into a **multimodal educational AI platform** where **voice is a first-class interface** rather than an additional feature. The existing LangGraph orchestration, educational workflows, memory system, and RAG remain the intelligence layer; voice simply becomes another way to interact with them.

## Objectives

* Deliver production-grade voice conversations.
* Preserve the existing architecture.
* Minimize refactoring.
* Maintain provider independence.
* Optimize for Ethiopian languages.
* Support future multimodal expansion.

## Core Architectural Principle

```
Voice is NOT another AI assistant.

Voice is another interface to the same AI assistant.
```

Every interaction—text, voice, or future modalities—must flow through the same Conversation Service and LangGraph execution pipeline.

## Success Criteria

* No duplicated business logic.
* Shared Conversation Service.
* Streaming-first pipeline.
* Provider abstraction.
* Zero regression for text chat.
* Future-ready multimodal architecture.

---

# Page 2 — Current Architecture Review

## Existing Strengths

The repository already contains the essential infrastructure:

* LangGraph orchestration
* Persistent conversation memory
* Agentic RAG
* Educational workflows
* Quiz engine
* Teacher dashboard
* Provider abstraction
* Authentication
* Conversation history
* Multi-provider LLM support

These components **must not be rewritten**.

## Existing Execution Flow

```
Frontend

↓

API

↓

Conversation Logic

↓

LangGraph

↓

Memory

↓

RAG

↓

LLM

↓

Response
```

## Architectural Decision

Do NOT create

```
Text Agent

Voice Agent
```

Instead

```
Text

Voice

Future Interfaces

↓

Conversation Service

↓

LangGraph

↓

Educational Intelligence
```

Everything shares the same pipeline.

---

# Page 3 — Product Requirements

## MVP Features

### Input

* Push-to-talk
* Streaming microphone
* Partial transcription
* Mixed Amharic/English speech
* Automatic language detection
* Language scope: **Amharic (primary), Afaan Oromo (via Addis AI — the only provider with Oromo voices)**. Tigrinya is out of scope: no production provider exists anywhere (verified 2026-07).

### Output

* Streaming speech synthesis
* Neural voices
* Transcript
* Playback controls
* Interruptible responses

### Delivery Channels (MVP)

| Channel | Timeline | Effort | Rationale |
|---------|----------|--------|-----------|
| **Web PWA** (Next.js 14, WebSocket) | M5–M6 | Full frontend build (new dashboard route + hooks + components) | Primary voice UI; existing Next.js codebase reduces build time vs native |
| **Telegram bot** (voice messages) | **M3** (ships with first SpeechProvider) | ~50 lines — `Message.voice` download → STT → Conversation Service → TTS → upload → send | Telegram dominance in Ethiopia + existing bot infra + zero frontend work |
| **[v2] Native mobile** (Flutter/RN) | Post-MVP | New repo, new CI, separate app store deployment | Deferred until voice features are validated against real usage patterns |

**Mobile strategy: PWA-first.** The existing Next.js dashboard at `dashboard/` gains Service Workers + `manifest.json` via `next-pwa`. WebRTC mic access is mature on Chrome/Android (dominates Ethiopian mobile market). Native mobile is v2 scope, after usage data confirms the investment.

### Educational Features

* Voice tutoring
* Voice quizzes
* Homework assistance
* Lesson explanations
* Reading practice

## Future Features

* Pronunciation scoring
* Classroom mode
* Offline speech
* Vision
* Camera understanding
* Handwriting
* Voice cloning

## Non-Goals

* Telephone integration
* Offline voice processing
* Live translation
* Call-center workflows

---

# Page 4 — Target Architecture

```
                  Gateway Layer

      Web PWA (Next.js)     Telegram Bot     [Future] Mobile
           │                     │                  │
           ▼                     ▼                  ▼
    WebVoiceAdapter      TelegramVoiceAdapter  MobileVoiceAdapter
           │                     │                  │
           └─────────────────────┼──────────────────┘
                                 │
                      Conversation Service
                                 │
                            LangGraph
                                 │
                   Memory • RAG • Tools
                                 │
                          LLM Providers
                                 │
                        Speech Providers
```

## Design Rules

Business logic belongs to LangGraph.

Speech providers only handle:

* Speech-to-Text
* Text-to-Speech
* Streaming
* Audio processing

Nothing educational belongs inside speech providers.

---

# Page 5 — Technical Design

## New Backend Modules

```
voice/

    providers/

    session/

    streaming/

    stt/

    tts/

    vad/

    audio/

    gateways/
        base.py          # GatewayAdapter ABC
        web.py           # WebVoiceAdapter (WebSocket, Next.js PWA)
        telegram.py      # TelegramVoiceAdapter (voice msg webhook)
        # future: mobile.py
```

## Core Services

Conversation Service

Speech Provider

Voice Session

Audio Stream

Language Detection

Voice Gateway (client-aware adapter layer — routes transport/auth/audio to Conversation Service)

Gateway Adapter (ABC with pluggable implementations per client type)

## Gateway Abstraction

The Voice Gateway is **not** a single "Voice API endpoint." It is a collection of **client-aware adapters**, each handling its own transport protocol, authentication, and audio codec, then emitting a normalized inner call to the Conversation Service.

### Adapter Contract

Every `GatewayAdapter` implements:

```python
class GatewayAdapter(ABC):
    @property
    def client_type(self) -> str: ...          # "web", "telegram", "mobile"
    async def handle_voice_input(input, metadata) -> ConversationRequest: ...
    async def deliver_audio(response, metadata) -> DeliveryResult: ...
    async def is_available() -> bool: ...
```

### Planned Adapters

| Adapter | Client | Transport | Auth | Audio In | Audio Out |
|---------|--------|-----------|------|----------|-----------|
| `WebVoiceAdapter` | Next.js PWA | WebSocket | JWT (existing) | PCM/Opus via WebRTC | PCM stream → browser |
| `TelegramVoiceAdapter` | Telegram bot | Webhook | Bot token | Opus file download | MP3 upload → send |
| `MobileVoiceAdapter` | [v2] Flutter app | WebSocket | JWT + device token | PCM/Opus native mic | PCM stream |

### Design Rule

The Conversation Service **never knows which adapter called it**. It receives a `ConversationRequest` with user_id, transcript, language, and session_id — nothing about the transport. This guarantees that Telegram voice, web voice, and future mobile voice share exactly one code path for LangGraph, Memory, RAG, and all educational logic.

## Conversation Contract and Operational Requirements

The Conversation Service never receives gateway-native updates, authentication objects, codec details, device identifiers, delivery handles, or provider hints. It accepts only a normalized request:

```python
@dataclass(frozen=True)
class ConversationRequest:
    user_id: str                 # durable learner identity
    conversation_id: str         # active learning thread
    session_id: str              # live interaction
    transcript: str
    language: str | None
    language_confidence: float | None
    modality: Literal["text", "voice"]
```

`user_id` preserves learner continuity; `conversation_id` selects a learning thread; `session_id` scopes a live interaction. Channel and device are delivery context only. Conflicting turns within a conversation are serialized; simultaneous channels use distinct conversations.

Every gateway supplies a stable inbound idempotency key. Telegram uses its update/message identifier, so redelivery cannot create duplicate turns, provider charges, or audio replies. When STT confidence is low, audio is unsupported, a provider fails, or TTS fails, return an actionable text response without rerunning a completed conversation.

Raw audio is stored only when enabled and only for a configured retention period. Long-term transcript memory requires explicit learner consent and must support deletion by learner identity. Metrics must not contain raw audio or transcript text by default; record gateway, duration, language/confidence, provider, fallback reason, delivery result, and STT/graph/TTS/delivery latency.


## Speech Provider Interface

The `SpeechProvider` ABC mirrors the existing `src/llm/providers/base.py` pattern so the voice subsystem inherits proven behavior (health checks, registry, circuit breaker, structlog) instead of inventing new conventions.

```python
class SpeechProvider(ABC):
    # Core legs — mirror LLMProvider.chat()
    async def transcribe(audio, language) -> TranscriptResult: ...
    async def synthesize(text, voice, language) -> AudioClip: ...

    # Streaming legs — mirror LLMProvider.chat_stream():
    # the base class ships a non-streaming default that wraps
    # transcribe()/synthesize(); providers override only when they
    # support true streaming (Azure: yes. Addis batch APIs: no).
    async def stream_transcription(audio_stream, language) -> AsyncGenerator[PartialTranscript]: ...
    async def stream_audio(text_stream, voice) -> AsyncGenerator[AudioChunk]: ...

    # Housekeeping — identical semantics to the LLM providers
    async def is_available() -> bool: ...
    async def check_health() -> bool: ...
    def get_info() -> SpeechProviderInfo: ...  # name, languages, voices, streaming caps
    @property
    def name(self) -> str: ...
```

Registered implementations (Milestones 3–4):

* `AzureSpeechProvider` — primary; true streaming STT + TTS for `am-ET`.
* `AddisAIProvider` — fallback TTS/STT (batch clips, 60s STT cap); **primary for Afaan Oromo**.
* `GroqSTTProvider` — free STT fallback (`whisper-large-v3-turbo`, OpenAI-compatible endpoint, `language="am"`).
* `LocalSpeechProvider` — self-hosted `faster-whisper` (STT) + OmniVoice Amharic (TTS, Apache-2.0 pending license review).
* `EdgeTTSProvider` — **dev/benchmark only**; blocked in production config (unofficial endpoint).

Provider selection, failover order, health tracking, and structured logging reuse the existing machinery from `src/llm/` (`ProviderManager`, `CircuitBreaker`, registry). The Conversation Service never knows which provider is active — it sees only `SpeechProvider`.

---

# Page 6 — Voice Conversation Pipeline

```
User

↓

Microphone

↓

Noise Suppression

↓

Echo Cancellation

↓

Silero VAD

↓

Streaming STT

↓

Conversation Service

↓

LangGraph

↓

Memory

↓

RAG

↓

LLM

↓

Streaming TTS

↓

Playback
```

## Rules

Audio is temporary.

Text becomes conversation history.

The educational workflow remains identical for text and voice.

---

# Page 7 — Streaming & Provider Strategy

## Streaming

Everything streams.

Never wait for complete responses.

```
Speech

↓

Partial Transcript

↓

LLM Tokens

↓

Partial Speech

↓

Playback
```

## Primary Provider

Azure Speech SDK

Reasons

* Production maturity
* True streaming STT + TTS (SDK + WebSocket)
* Amharic Neural Voices (`am-ET-MekdesNeural` F, `am-ET-AmehaNeural` M)
* SDK support
* Reliability
* **F0 free tier (verified 2026-07): 5 audio-hours/mo STT + 0.5M chars/mo neural TTS, ongoing (not a 12-month trial)**

## Secondary Provider

Addis AI (verified 2026-07, docs contract 2026-07-23)

Verified profile

* **Addis Voices 2: 28 voices — 19 Amharic + 9 Afaan Oromo** (the only Oromo voices offered by any provider)
* STT (`/api/v2/stt`): Amharic + Oromo, dialect-tuned, **batch only, 60s / 10MB max**
* TTS: durable clips (mp3/wav/pcm) — **does not stream partial audio**
* Realtime API: WebSocket speech-to-speech, <300ms, server VAD, interruptions — a full agent loop, not a TTS/STT leg (see Risks)
* Free tier: 500 ETB starter credits (one-time); then ETB wallet paygo (TTS 5 ETB/min, STT 3.5 ETB/1K chars)
* SDKs: `addisai` on PyPI + npm; no training on customer data; on-prem option for Enterprise

Purpose

* Benchmarking (Ethiopian dialect reference)
* Ethiopian language optimization
* Fallback TTS when Azure free quota exhausts (clips suit async content: lesson narration, reading practice)
* **Primary provider for Afaan Oromo** (no alternative exists)

## Provider Catalog (verified 2026-07 — see research report for sources)

| Role | Provider | Amharic | Oromo | Streaming | Cost |
|---|---|---|---|---|---|
| Primary STT+TTS | Azure Speech | ✅ | ❌ | ✅ both legs | F0 free monthly, then paygo |
| Fallback TTS / Oromo primary | Addis AI | ✅ | ✅ | ❌ batch | 500 ETB credits, then paygo |
| Free STT fallback | Groq `whisper-large-v3(-turbo)` | ✅ | ❌ | ❌ batch (216× RT) | **Free: ~8 audio-hrs/day** |
| Free STT fallback 2 | Cloudflare Workers AI Whisper | ✅ | ❌ | ❌ batch | Free daily allocation; $0.00051/min paid |
| Self-host STT | faster-whisper large-v3 (+ HF am fine-tunes) | ✅ | ❌ | ✅ via VAD chunking | Free (own GPU/CPU) |
| Self-host TTS | OmniVoice Amharic (0.6B, ~3GB VRAM) | ✅ | ❌ | chunk-level | Free; **license review required** |
| Future TTS | Gemini-TTS (`am-ET` Preview, streaming) | ✅ | ❌ | ✅ | AI Studio free tier now |
| Realtime S2S | Addis Realtime API | ✅ | ✅ | ✅ full-duplex | paygo tokens — post-MVP evaluation only |
| Dev/benchmark TTS | edge-tts (`am-ET` Azure voices, no key) | ✅ | ❌ | ✅ | Free — **never production** (unofficial endpoint) |

Ruled out with evidence: Deepgram (no Amharic in Nova-2/3/Flux), Coqui XTTS v2 (17 languages, no Amharic + non-commercial license), Meta MMS (CC-BY-NC + uroman transliteration friction), Google classic Cloud TTS voices (no `am-ET` — the only Google path is Gemini-TTS), AWS Polly (no Amharic; AWS Transcribe am-ET exists but free tier is 60 min/mo for 12 months only — kept as reference).

No provider-specific logic should leak into business code.

---

# Page 8 — Frontend Design

New Components

```
VoiceButton

Waveform

Transcript

AudioPlayer

VoiceSettings

ConnectionStatus
```

New Hooks

```
useVoiceSession()

useStreamingAudio()

useMicrophone()

useSpeechRecognition()
```

## UX Principles

* Push-to-talk first
* Continuous mode later
* Visible transcript
* Interrupt AI speaking
* Replay responses
* Adjustable speech rate
* Network status indicator

---

# Page 9 — Coding-Agent Execution Roadmap

## Milestone 1

Refactor Conversation Service

Deliverable

Unified conversation entry point plus normalized `ConversationRequest`/`ConversationResponse` contract. Separate `user_id`, `conversation_id`, and `session_id`; migrate text chat without behavior change.

---

## Milestone 2

Create Voice Module

Deliverable

Independent speech subsystem.

---

## Milestone 3

Speech Provider Layer

Deliverable

`SpeechProvider` ABC mirroring `src/llm/providers/base.py` + Azure provider (am-ET streaming) + Addis AI fallback (batch) + config-driven provider registry reusing `ProviderManager`/`CircuitBreaker`. Ship the Telegram batch proof: idempotent voice-note download -> STT -> Conversation Service -> LangGraph -> text/TTS reply. Exercise Amharic, Afaan Oromo, and Amharic/English code-switching; allow learner language override.

---

## Milestone 4

Streaming Infrastructure

Deliverable

Streaming STT/TTS, VAD, interruption, and partial transcripts. This follows M3 batch validation rather than blocking it.

---

## Milestone 5

Voice Gateway (Gateway Abstraction Layer)

Deliverable

Client-aware gateway adapters:

* `GatewayAdapter` ABC with `handle_voice_input()`, `deliver_audio()`, `is_available()`.
* `WebVoiceAdapter` — FastAPI WebSocket endpoint for the Next.js PWA; JWT auth via existing middleware; streams PCM/Opus → Conversation Service → streams audio back.
* `TelegramVoiceAdapter` — voice message handler in `src/telegram/bot.py`; downloads `.ogg` → STT → Conversation Service → TTS → uploads result → sends as audio reply.
* `MobileVoiceAdapter` — [v2 milestone] placeholder; same WebSocket contract as Web once the Flutter app exists.
* Cross-gateway session design: adapters route by `user_id` plus explicit `conversation_id`/`session_id`; channel and device remain delivery context. This provides continuity without conflicts when one learner is active on multiple gateways.

---

## Milestone 6

Frontend Voice UI

Deliverable

Voice experience.

---

## Milestone 7

Educational Voice Integration

Deliverable

Voice tutoring.

Voice quizzes.

Lesson explanations.

Reading support.

---

## Milestone 8

Production

Deliverable

Monitoring.

Analytics.

Configuration.

Security.

Deployment.

Provider failover.

Configured audio/transcript retention, learner consent and deletion, idempotency storage, and privacy-safe operational metrics.

---

# Page 10 — Risks & Mitigation

| Risk                      | Mitigation                                |
| ------------------------- | ----------------------------------------- |
| Vendor lock-in            | Speech Provider abstraction               |
| High latency              | Streaming + VAD + partial responses       |
| Code duplication          | Shared Conversation Service               |
| Existing chat regression  | Preserve current text pipeline            |
| Provider outages          | Configurable fallback providers (circuit breaker reused from `src/llm/circuit_breaker.py`) |
| Future multimodal changes | Interface-driven architecture             |
| Scaling                   | Stateless voice gateway + session manager |
| Free-quota exhaustion (Azure F0 5h/mo, Groq 8h/day) | Failover chain Azure → Groq → self-host; per-provider usage metering in Milestone 8 |
| OmniVoice license conflict (Apache-2.0 claim vs. base model CC-BY-NC) | Legal review or author confirmation before shipping `LocalSpeechProvider` TTS; ship STT-only self-host until cleared |
| Addis AI batch-only STT/TTS (no streaming) | Confine Addis to fallback/clip roles + Oromo; never the real-time path; re-evaluate if vendor ships streaming |
| Addis Realtime API bypasses LangGraph (own agent loop) | Post-MVP evaluation only; spike a "dumb audio pipe" bridge in Milestone 4 before any use; One Conversation Engine stays authoritative |
| edge-tts unofficial endpoint (ToS, can break) | Dev/benchmark only; hard-blocked in production config |
| Tigrinya unsupported by any provider | Language promise scoped to Amharic + Afaan Oromo; Tigrinya tracked as open question |
| PWA audio reliability on iOS Safari | WebRTC mic persistence and background audio are unreliable on iOS; MVP targets Android+Desktop; iOS native app added to v2 scope |
| Cross-gateway session conflicts (same user on mobile + web simultaneously) | Separate durable `user_id`, `conversation_id`, and `session_id`; serialize conflicting turns within a conversation and let simultaneous channels use distinct conversations |
| Webhook redelivery / duplicate charges | Persist an inbound idempotency key and completed response before delivery; retry by replaying the stored result rather than rerunning STT, LangGraph, or TTS |
| Low-confidence or code-switched transcription | Capture language/confidence, support learner override, ask for correction below threshold, and test Amharic/English mixed utterances |
| Audio/TTS delivery failure | Preserve and return the completed text response; retry delivery independently without rerunning LangGraph |
| Learner privacy exposure | Configured retention, explicit consent before transcript memory, deletion by learner identity, and no raw audio/transcript logging by default |

---

# Page 11 — Architecture Principles

## Principle 1

One Conversation Engine.

---

## Principle 2

One LangGraph.

---

## Principle 3

One Memory System.

---

## Principle 4

One RAG Pipeline.

---

## Principle 5

One Educational Intelligence Layer.

---

## Principle 6

Speech is replaceable.

---

## Principle 7

Business logic never lives inside providers.

---

## Principle 8

Streaming-first.

---

## Principle 9

Gateways are replaceable adapters.

Each client type (web PWA, Telegram bot, mobile app) gets its own `GatewayAdapter` that handles transport-specific concerns. The Conversation Service never knows which gateway called it. Adding a new client means writing one adapter, not forking the pipeline.

## Principle 10

Future modalities reuse the same architecture.

Examples

* Vision
* Camera
* Documents
* Handwriting
* Live classroom
* Wearables

---

# Page 12 — Definition of Done

The Voice Platform is complete when:

* Voice and text share the same Conversation Service.
* LangGraph remains the single source of orchestration.
* Memory and RAG behave identically across modalities.
* Speech providers can be swapped through configuration only.
* Provider catalog documents verified language coverage (Amharic, Afaan Oromo), streaming capability, and free-tier limits per provider.
* Telegram batch voice functions end-to-end with idempotency and text fallback; streaming STT and TTS then function end-to-end.
* Existing text functionality remains unchanged.
* Voice sessions support interruption, replay, and transcript generation.
* Monitoring, security, analytics, and deployment are production-ready.
* Raw-audio retention, transcript-memory consent, and learner deletion behavior are implemented and verified.
* The architecture supports future multimodal interfaces without structural redesign.

---

# Final Engineering Directives (Mandatory)

These directives should be treated as non-negotiable throughout implementation:

1. **Preserve the existing LangGraph architecture.** Extend it only when necessary; do not replace or bypass it.
2. **Never duplicate business logic.** All educational reasoning, memory access, RAG retrieval, and tool execution must remain centralized in the Conversation Service and LangGraph.
3. **Keep speech vendor-agnostic.** Introduce all Speech-to-Text and Text-to-Speech providers through a common abstraction to avoid vendor lock-in.
4. **Design for streaming by default.** The architecture should support incremental speech recognition, LLM token streaming, and incremental speech synthesis.
5. **Favor minimal, incremental changes.** Integrate with the existing codebase instead of introducing parallel systems or large-scale rewrites.
6. **Maintain backward compatibility.** All existing text-chat functionality must continue to work without modification.
7. **Optimize for future multimodality.** New interfaces (voice today, vision and documents tomorrow) should plug into the same conversation pipeline rather than creating separate application flows.

This Version 2.0 combines the implementation depth of the original Master Plan with the organization and clarity of the Engineering Design Pack, making it suitable as the primary architectural blueprint for coding agents working directly on the EthioBio codebase.
