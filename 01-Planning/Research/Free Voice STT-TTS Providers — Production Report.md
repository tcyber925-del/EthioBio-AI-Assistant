---
type: synthesis
title: "Free Voice STT/TTS Providers — Production Report (Ethiopian Audience)"
created: 2026-07-28
updated: 2026-07-28
tags: [research, voice, stt, tts, amharic, production]
status: developing
related:
  - "[[EthioBio Voice Platform Engineering Design Pack v2.0]]"
research_method: autoresearch (4 rounds, 21 primary sources, official docs only; Addis AI deep dive added 2026-07-28)
---

# Free Voice STT/TTS Providers — Production Report

## Overview

Evaluation of **free / zero-cost speech-to-text (STT) and text-to-speech (TTS) providers** for the EthioBio Voice Platform, targeting Ethiopian users (primary: Amharic `am-ET`; secondary: Tigrinya, Afaan Oromo, Somali). All findings verified against official documentation in July 2026. Confidence: **high** = multiple official sources, **medium** = single official source, **low** = community claim.

**Headline finding:** The design pack's Azure-first choice is validated (only managed cloud with full Amharic STT + streaming + 2 neural voices + an always-free tier). The strongest *new* findings: **OmniVoice Amharic** — a 2026 Apache-2.0 open-weights Amharic TTS with zero-shot voice cloning that runs on a free Colab T4 — **Groq's free Whisper API** (~8 audio-hours/day free) for STT fallback, and **Addis AI fully verified** (§2A): 28 Ethiopian voices incl. the world's only Afaan Oromo TTS/STT, a <300ms Realtime API, and 500 ETB free starter credits — ideal fallback, not main provider (no streaming STT/TTS in its cascade APIs).

---

## 1. Providers Already in the Design Pack (Baseline)

| Provider | Amharic STT | Amharic TTS | Free tier (verified) | Notes |
|---|---|---|---|---|
| **Azure Speech** (primary) | ✅ `am-ET` real-time + fast transcription; custom speech: plain-text only | ✅ `am-ET-MekdesNeural` (F), `am-ET-AmehaNeural` (M) | **F0 ongoing:** 5 audio-hrs/mo STT + 0.5M chars/mo neural TTS + 5 hrs/mo translation | Only managed provider with full streaming SDK for am-ET. Also has Voice Live API (speech-to-speech, paid). Confidence: high |
| **Addis AI** (secondary) | ✅ Amharic + Afaan Oromo, dialect-optimized (`/api/v2/stt`, batch, 60s max) | ✅ **Addis Voices 2: 28 voices (19 Amharic + 9 Oromo)** | 500 ETB starter credits (one-time); then paygo ETB wallet | Fully verified — see §2A deep dive. Confidence: high |
| **Whisper** (future) | ✅ `am` supported in large-v3 | — | Open weights (MIT) | See §2 for free *hosted* Whisper options |
| **Demtse** (future) | — | — | Not publicly documented | Local vendor; no verifiable public API docs. Confidence: low |
| **Google Speech** (future) | ⚠️ Classic Cloud TTS voices: **no Amharic** (verified — full voice list contains no `am-ET`). Chirp/USM STT: unverified | ✅ **Gemini-TTS: `am-ET` (Preview)** | AI Studio free tier exists; Cloud free tier: 1M chars/mo Standard, 0→waveNet... (Cloud TTS free tier does not apply to Gemini-TTS) | Google's only Amharic path is **Gemini-TTS** (`gemini-2.5-flash-tts`, `gemini-2.5-pro-tts`, `gemini-3.1-flash-tts-preview`). Supports bidirectional streaming synthesis. Confidence: high |

---

## 2. NEW Providers (Not in the Design Pack)

### STT

| Provider | Amharic | Free allowance | Streaming | License/ToS | Production verdict |
|---|---|---|---|---|---|
| **Groq API** (whisper-large-v3 / v3-turbo) | ✅ multilingual Whisper, `language="am"` | **Free tier: 20 RPM, 2K req/day, 7,200 audio-sec/hr, 28,800 audio-sec/day (~8 audio-hrs/day)** | ❌ batch upload only (but 216× real-time; ~1.5s for a 5-min file) | Standard API ToS. Paid: $0.04–0.111/audio-hr | **Best free managed STT fallback.** OpenAI-compatible endpoint — trivial to wire into the SpeechProvider abstraction. Confidence: high |
| **Cloudflare Workers AI** (whisper-large-v3-turbo) | ✅ | Free daily allocation (Workers AI free tier); paid $0.00051/audio-min | ❌ batch | Standard CF ToS | Second free managed Whisper option; also useful as edge inference later. Confidence: high |
| **Self-host faster-whisper** (CTranslate2) | ✅ large-v3 `am`; HF fine-tunes: `agkphysics/wav2vec2-large-xlsr-53-amharic` (50k downloads), `badrex/Ethio-ASR-amharic`, `b1n1yam/shook-medium-amharic-2k`, `chappM/whisper-amharic-small-v2` | Free (your GPU; runs CPU too) | ✅ via VAD-chunked streaming wrappers | MIT | The "local speech models" slot in the plan. Zero marginal cost, offline-capable, data-privacy win (student voice never leaves infra). Confidence: high |
| **AWS Transcribe** | ✅ `am-ET` **batch AND streaming** | 60 min/mo free (12 months only) | ✅ | Standard AWS ToS | Verified am-ET streaming — the only *other* managed streaming Amharic STT besides Azure. Free tier too small for production; keep as failover reference. Confidence: high |
| **Deepgram** | ❌ Nova-2/3/Flux: no Amharic. ⚠️ Only via Deepgram Whisper Cloud (`whisper-large`) | $200 signup credit | Whisper cloud: limited (15 concurrent paid / 5 paygo) | Standard ToS | **Ruled out** for native Amharic. Whisper Cloud is a viable managed-Whisper niche. Confidence: high |
| **Meta MMS ASR/LID** (fairseq, HF) | ✅ amh ASR + language-ID for 1,000+ langs (covers Tigrinya, Oromo, Somali) | Free | ❌ | **CC-BY-NC 4.0** | Non-commercial only — benchmark/research use, or license negotiation. Confidence: high |

### TTS

| Provider | Amharic quality | Free allowance | Streaming | License | Production verdict |
|---|---|---|---|---|---|
| **OmniVoice Amharic** (`african-low-resource/omnivoice-amharic`, 2026) | ⭐ Purpose-built: trained on ~331h Amharic (Google WaxalNLP ~200h, Leyu Addis dialect ~50h, clear-audio ~40h, BDU ASR ~41h). Handles ejectives (ጠ/ጸ/ቸ), gemination, natural prosody. Zero-shot voice cloning from 10s audio | Free, self-host (0.6B params, ~3GB VRAM, runs on free Colab T4; RTF ~0.025 on the base arch = 40× real-time) | ⚠️ Non-autoregressive diffusion — chunk-level synthesis; true token-streaming unverified | **Apache-2.0** (claimed by fine-tune; see license risk below) | **Best free self-host TTS candidate.** Covers plan's future "voice cloning" goal for free. ⚠️ Eval metrics still TBD; male-skewed (65%) data; Addis-dialect bias; code-mixing unpredictable. Live demo exists (HF Space `demeleww/omnivoice-amharic-demo`). Confidence: medium-high |
| **k2-fsa/OmniVoice** (base model, 2026) | 646 languages zero-shot (Amharic included; Tigrinya/Oromo coverage plausible — **verify**) | Free, self-host | ⚠️ same as above | Code Apache-2.0; **weights CC-BY-NC** (Emilia dataset) | Non-commercial weights. Use the Amharic fine-tune instead. Confidence: high |
| **edge-tts** (rany2, 11.6k★) | ✅ Same Azure voices free: `am-ET-AmehaNeural`, `am-ET-MekdesNeural`; rate/volume/pitch control; word-boundary subtitles | Unlimited (unofficial Microsoft Edge endpoint, no API key) | ✅ streams chunks | Library GPL-3.0; **uses undocumented MS endpoint — ToS gray zone, can break anytime** | **Dev/benchmark/demo only — never production.** Zero-effort way to test the full Azure voice UX before paying Azure. Confidence: high |
| **Gemini-TTS** (Google) | ✅ `am-ET` in Preview (30 Chirp-style voices, prompt-steerable style/emotion, multi-speaker) | AI Studio free tier (rate-limited); Cloud: paygo | ✅ Cloud TTS API `StreamingSynthesize` (multi-req/multi-resp, PCM/OGG_OPUS 24kHz) | Standard Google ToS | **Track closely** — the only big-tech TTS besides Azure moving on Amharic. Preview status = not for GA launch, ideal secondary for the provider abstraction. Confidence: high |
| **Meta MMS-TTS-amh** | ✅ VITS 36M params, purpose-trained Amharic | Free, self-host (CPU-friendly) | ❌ | **CC-BY-NC 4.0**; input must be Latin-transliterated via `uroman` (extra preprocessing step) | Non-commercial license + transliteration friction. Benchmark baseline only. Confidence: high |
| **Coqui XTTS v2** | ❌ 17 languages — **no Amharic** | Free, self-host | ✅ | CPML (non-commercial) | **Ruled out** (no am + NC license). OmniVoice supersedes it on both axes. Confidence: high |

### §2A. Addis AI Deep Dive (verified against docs 2026-07-23/28)

Full documentation now available and researched. Addis AI is a production platform (SDKs on npm/PyPI as `addisai`, OpenAI-style API, `x-api-key` auth, ETB wallet billing).

**Capability matrix vs. design-pack requirements:**

| Requirement (Design Pack) | Addis AI support | Detail |
|---|---|---|
| Streaming microphone / realtime | ✅ **Realtime API** — WebSocket `wss://relay.addisassistant.com/ws`, <300ms response, PCM16 in @16kHz / out @24kHz, server-side VAD, natural interruption + back-channeling | Powered by `አሌፍ-1.2-realtime-audio`; protocol is Gemini-Live-style (`serverContent.modelTurn`) |
| Streaming TTS | ❌ **Not supported** | Addis Voices 2 generates durable clips (mp3/wav/pcm) — "does not stream partial audio". Only the Realtime API streams audio |
| Streaming STT / partial transcripts | ❌ **Not supported** | STT is batch multipart upload, **60s max duration, 10MB max** |
| Amharic voices | ✅ 19 voices (Hamen, Nejat, Tesfa, Muaz, Roba, Yohannes…) — conversational/narration/commercial styles | `voices.list()` catalog API + signed previews |
| **Afaan Oromo** | ✅ **9 voices + STT** — *the only provider on earth with production Oromo voice* | Azure/AWS/Google/Groq: none |
| Tigrinya | ❌ | Not offered by any provider found in this research |
| Mixed Amharic/English (code-switch) | ⚠️ Degraded | STT docs: "code-switching may have lower accuracy" |
| Language detection | ❌ Not documented | — |
| SDK / integration fit | ✅ Python `addisai` + Node; server-side proxy pattern mirrors our FastAPI Voice Gateway | Idempotency keys, pre-generation cost estimates, usage/clip history APIs |
| Privacy / data residency | ✅ "No" training on API data; **on-premise deployment for Enterprise** (banking/gov/health) | Strong fit for Ethiopian schools/government later |
| Billing | ETB wallet (local payment rail — no forex card needed) | 500 ETB free starter credits |

**Verified pricing (ETB):** TTS **5/min generated audio** · STT **3.5 per 1K output chars** · Realtime 1/4 per 1K in/out tokens · LLM 0.3/0.8 per 1K tokens. 500 ETB credits ≈ 100 TTS-minutes ≈ ~100 short voice sessions — a genuine free pilot, but **not a recurring free tier** (unlike Azure F0).

**Main vs. fallback verdict:**

- ❌ **Cannot be main provider yet** — both cascade-leg APIs (STT, TTS) lack streaming, violating the design pack's streaming-first Principle 8; no perpetual free tier; single-vendor maturity risk vs. Azure's SLA.
- ✅ **Ideal fallback + three primary niches:**
  1. **Primary for Afaan Oromo** (no alternative exists anywhere).
  2. **TTS fallback for Amharic** when Azure F0 quota exhausts — durable clips are fine for async content (lesson narration, reading practice, homework audio).
  3. **Benchmarking reference** for Ethiopian dialect/accent quality (exactly the role the design pack assigns it).
- ⚠️ **Realtime API is architecturally special** — it is a full speech-to-speech agent loop (its own model turn), which would bypass our Conversation Service/LangGraph if used as the main loop. Re-evaluate only for the future "continuous mode" feature (post-MVP), with the tension against "One Conversation Engine" explicitly decided then.

### Enabling datasets (for self-host/fine-tune path)

- `google/WaxalNLP` — ~200h Amharic speech (Google, 2025) — the corpus behind OmniVoice Amharic. Confidence: high
- `gheero-Leyu/leyu-amharic-addis-ababa-dialect` (~50h), `surafelabebe/amharic_clear_audio_tts` (~40h), `chappM/amharic-bdu-asr` (~41h). Confidence: medium

---

## 3. Recommended Production Stack

Maps to the design pack's `SpeechProvider` abstraction (Milestone 3) — every row is config-swappable, no business-logic impact.

```
STT primary   : Azure am-ET (streaming SDK)          [F0: 5 hrs/mo free]
STT fallback  : Groq whisper-large-v3-turbo          [free ~8 audio-hrs/day, batch-but-fast]
STT offline   : faster-whisper large-v3 (self-host)  [free, private]
STT Ethiopian : Addis AI (batch, dialect-tuned)      [500 ETB credits → 3.5 ETB/1K chars]
TTS primary   : Azure am-ET-Mekdes/Ameha Neural      [F0: 0.5M chars/mo free]
TTS fallback  : Addis Voices 2 (19 am voices, clips) [500 ETB credits → 5 ETB/min]
TTS self-host : OmniVoice Amharic (own GPU/Colab)    [free, Apache-2.0, cloning-ready]
TTS secondary : Gemini-TTS am-ET (when GA)           [AI Studio free tier now]
OROMO (all)   : Addis AI — only provider in existence [9 voices + STT]
Realtime S2S  : Addis Realtime API (<300ms, WS)      [post-MVP continuous mode only]
Benchmark     : edge-tts (UX parity check), MMS (WER/MOS baseline)
VAD           : Silero (already in plan, free)
```

**Cost model (pilot ≈ 50 students × 10 voice turns/day):** Azure F0 covers ~2–3 weeks of STT before breaching 5 hrs/mo; Groq free tier absorbs the STT overflow (~8 audio-hrs/day is far above pilot need); OmniVoice self-host on one ~$0.30–0.50/hr spot GPU (or existing Ollama host) makes TTS marginal-cost ≈ $0. Effective pilot cost: **near $0**, with Azure as the quality anchor and everything else config-level failover.

---

## 4. Contradictions & Risks

1. **License conflict (medium severity):** `african-low-resource/omnivoice-amharic` claims Apache-2.0, but its base `k2-fsa/OmniVoice` weights are CC-BY-NC (Emilia training data). A fine-tune cannot unilaterally strip an NC condition. → **Action: legal review or written confirmation from the authors before commercial shipping.** If it fails review, fall back to Azure/edge-tts-quality path and self-host STT only.
2. **edge-tts is not a production provider.** It proxies an undocumented Microsoft endpoint; it can be rate-limited or killed without notice, and violates the spirit of Azure ToS. Use only for development and UX benchmarking.
3. **"Multilingual" ≠ "Amharic-capable."** Verified rule-outs: Deepgram Nova (all tiers), Google classic Cloud TTS voices, Coqui XTTS v2. Do not assume coverage — check the voice list.
4. **OmniVoice Amharic quality claims are self-reported** (MOS/ejective-accuracy metrics still "TBD" on the model card). Benchmark against Azure voices with Ethiopian students before committing. Confidence: medium.
5. **Plan-doc gap:** The design pack lists "Google Speech" as a future provider — verified that Google's classic TTS has **no** Amharic voice; the actual Google path is Gemini-TTS (Preview) or Gemini Live API (unverified for am). Update the plan's provider table accordingly.

## 5. Open Questions

> [!gap] These need verification before Milestone 3/8 sign-off.

1. **Tigrinya (`ti-ET`) coverage** — no provider found supports it (Azure am-ET only; Addis AI: am+om only). MMS claims `tir` in its 1,000+ language list — verify per-language before promising Tigrinya.
2. **Gemini Live API** (realtime speech-to-speech) Amharic support status — the `ai.google.dev` docs fetch timed out twice; retry before Milestone 4.
3. ~~Addis AI docs~~ — **RESOLVED 2026-07-28** (see §2A). Remaining: **Demtse** still has no public docs; vendor call needed.
4. **OmniVoice streaming behavior** — diffusion TTS synthesizes per-chunk; validate time-to-first-byte against the design pack's streaming-first rule (Principle 8).
5. **Independent Amharic WER benchmark** — no public eval compares Azure vs Addis `addis-whisper` vs Whisper-large-v3 vs HF fine-tunes on Ethiopian-accented classroom audio; plan a 2-hour recorded test set as part of Milestone 8 analytics. Addis STT claims WER <10% under clean conditions (single speaker, 16kHz mono).
6. **Addis streaming roadmap** — Voices 2 TTS and STT are batch today; ask the vendor (Telegram community / support@addisassistant.com) whether streaming variants are planned, since streaming support would upgrade them to main-provider candidacy.
7. **Addis Realtime API + LangGraph bridge** — can the Realtime session be configured as a "dumb" audio pipe (audio-in→transcript out, text-in→audio out) so it fits the provider abstraction without bypassing LangGraph? Needs a spike in Milestone 4.

## 6. Sources

1. [Azure Speech language support (STT/TTS am-ET)](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support) — Microsoft Learn, updated 2026-06
2. [Azure Speech pricing — F0 free tier](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/) — Microsoft, 2026
3. [Groq Speech-to-Text docs](https://console.groq.com/docs/speech-to-text) + [rate limits](https://console.groq.com/docs/rate-limits) — 2026
4. [Cloudflare Workers AI — whisper-large-v3-turbo](https://developers.cloudflare.com/workers-ai/models/whisper-large-v3-turbo/)
5. [HF: african-low-resource/omnivoice-amharic](https://huggingface.co/african-low-resource/omnivoice-amharic) — 2026
6. [HF: k2-fsa/OmniVoice](https://huggingface.co/k2-fsa/OmniVoice) + arXiv:2604.00688 — 2026
7. [HF: facebook/mms-tts-amh](https://huggingface.co/facebook/mms-tts-amh) + MMS paper arXiv:2305.13516
8. [HF models search: "amharic" (549 models)](https://huggingface.co/models?search=amharic)
9. [GitHub: rany2/edge-tts](https://github.com/rany2/edge-tts) — am-ET voice list
10. [Google Cloud TTS — supported voices (no am-ET)](https://cloud.google.com/text-to-speech/docs/voices)
11. [Google Cloud — Gemini-TTS (am-ET Preview)](https://cloud.google.com/text-to-speech/docs/gemini-tts)
12. [AWS Transcribe — supported languages (am-ET batch+streaming)](https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html)
13. [Deepgram — Models & Languages Overview (no Amharic)](https://developers.deepgram.com/docs/models-languages-overview)
14. [HF: coqui/XTTS-v2 (17 languages, no Amharic)](https://huggingface.co/coqui/XTTS-v2)
15. [HF dataset: google/WaxalNLP](https://huggingface.co/datasets/google/WaxalNLP)
16. [Addis AI docs — Introduction](https://docs.addisassistant.com/docs/get-started/introduction)
17. [Addis AI docs — Text-to-Speech (Voices 2)](https://docs.addisassistant.com/docs/capabilities/text-to-speech) — contract verified 2026-07-23
18. [Addis AI docs — Speech-to-Text](https://docs.addisassistant.com/docs/capabilities/speech-to-text)
19. [Addis AI docs — Realtime API](https://docs.addisassistant.com/docs/capabilities/realtime)
20. [Addis AI docs — Pricing](https://docs.addisassistant.com/docs/platform/pricing) + [FAQ](https://docs.addisassistant.com/docs/platform/faq) (free tier: 500 ETB credits)
21. [Addis AI docs — Server-side Integration](https://docs.addisassistant.com/docs/integration/server)
