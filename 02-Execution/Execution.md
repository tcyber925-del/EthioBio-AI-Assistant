# EthioBio AI Assistant - Execution

## Phase 1: Foundation
- [x] Scaffold repository and project structure
- [x] Build Telegram bot integration (PTB v21, async native)
- [x] Integrate Ollama for local/cloud model hosting (`gemma4:31b-cloud`)
- [x] Add fallback provider routing (OpenAI/Anthropic, confidence-based)
- [x] Implement retrieval pipeline (RAG)

## Phase 2: Core Features
- [x] Implement Tutor Agent for biology Q&A with source citations
- [x] Implement Quiz Agent for assessment generation (5 types, RAG-grounded)
- [x] Implement Lesson Planner Agent
- [x] Build teacher review tools (admin API + Next.js dashboard)

## Phase 3: Tracking & Analytics
- [x] Implement Student Progress Agent (trend detection, weak areas)
- [x] Implement Parent Summary Agent (bilingual reports)
- [x] Build analytics and monitoring (admin endpoints)

## Phase 4: Advanced Features
- [x] OCR integration (RapidOCR fallback for garbled PDFs)
- [ ] Voice support (speech-to-text) — *stubbed, needs Whisper/STT integration*
- [ ] WhatsApp channel support — *planned for v1.4*
- [x] PDF/DOCX export — *endpoints defined, Docling HybridChunker integrated*

## Phase 5: Multi-Provider AI System
- [x] `LLMProvider` abstract interface (`src/llm/providers/base.py`)
- [x] `OllamaProvider` — any local Ollama model with dynamic selection
- [x] `OpenAIProvider` — OpenAI API + OpenAI-compatible (LM Studio, vLLM)
- [x] `AnthropicProvider` — Anthropic Claude API
- [x] `ProviderManager` — fallback chain orchestration, runtime switching, health checks
- [x] `ModelRegistry` — auto-detect Ollama models via `/api/tags`
- [x] `ModelRouter` — backward-compatible wrapper over `ProviderManager`
- [x] `AgentState.preferred_model` field + schema updates
- [x] 6 new `/models/*` API endpoints (list, providers, active, health, refresh)
- [x] Dashboard model selector (Ask, Quiz, Lesson pages, Monitoring panel)
- [x] Telegram bot `/model` command with inline keyboard
- [x] `.env.example` updated with multi-provider config
- [x] Tests updated (10/10 passing in `tests/test_llm.py`)
- [x] Next.js proxy: `/models/:path*` rewrite rule
- [x] `api_base_url` config for Telegram bot Docker networking

## LangGraph Orchestration
- [x] Build StateGraph with 5 nodes (orchestrator, retrieve, skip_retrieval, tutor, safety)
- [x] Implement bidirectional safety revision loop (reject/revise → tutor)
- [x] Dependency-injected nodes (ModelRouter, VectorStoreAdapter)
- [x] 20+ field AgentState dataclass

## Hybrid RAG Pipeline
- [x] Implement `VectorStoreAdapter` (dense + BM25 + rerank merge)
- [x] Implement `BM25Index` with pickle persistence
- [x] Implement `Reranker` (cross-encoder `ms-marco-MiniLM-L-6-v2`)
- [x] Configurable weights (0.6 dense / 0.4 BM25)
- [x] `RetrievalFilter` with grade/topic/unit/source_type filtering

## Document Processing
- [x] Implement `docling_extractor.py` (PyPdfium2 + RapidOCR)
- [x] Garbled text detection (alpha character ratio < 40%)
- [x] Full OCR for Grade 10 (176/182 pages garbled due to font encoding)
- [x] Per-page chunking for accurate page numbers
- [x] Enriched metadata (`unit`, `topic`, `page_number`)
- [x] 4 textbooks ingested (Grades 9-12), 1,165 total chunks

## Source Citations
- [x] Citation format: `(Grade X, Unit Y: Title, p. Z)`
- [x] Update `format_context()` in `VectorStoreAdapter` with citation headers
- [x] Update TutorNode and TutorAgent system prompts to require citations
- [x] Verified working via API endpoint test

## Progress Log
| Date | Update |
|------|--------|
| 2026-05-12 | Initial project setup: scaffold, FastAPI, Telegram bot, Ollama integration |
| 2026-05-12 | Phase 0 complete: gemma4:31b-cloud model, Telegram bot fixes, curriculum ingestion script, RAG verified |
| 2026-05-12 | Phase 1-3: VectorStoreAdapter, LangGraph orchestrator, Ragas evaluation, LangSmith tracing. 54 Python files, ~4000 lines. |
| 2026-05-14 | Telegram enhancements: improved keyboard handling, `_reply_long()` for >4096 chars, `callback_data` buttons, ConversationHandler pattern fixes (`^quiz$`), `telegram_id` to `BigInteger`, DB auto-creation |
| 2026-05-14 | DB + Dashboard: auto table creation, improved dashboard error handling, bypass Next.js proxy, admin content review accepts both `type` and `content_type` |
| 2026-05-15 | Hybrid RAG: BM25 sparse retrieval, cross-encoder reranker, `VectorStoreAdapter` replacing simple `Retriever`, configurable weights (0.6/0.4), `RetrievalFilter` with multi-field filtering |
| 2026-05-15 | Docling+OCR: PyPdfium2 extraction with RapidOCR fallback, garbled detection (alpha ratio < 40%), full OCR for Grade 10, HybridChunker for token-aware chunking |
| 2026-05-16 | Citations: explicit `(Grade X, Unit Y: Title, p. Z)` format, enriched metadata, per-page chunking, TutorNode + TutorAgent prompts updated |
| 2026-05-16 | Re-ingestion: all 4 textbooks re-ingested (1,165 chunks), new vector store path `data/vectors_new/`, BM25 index auto-rebuild |
| 2026-05-17 | Documentation: updated README.md, PRD.md v1.2, Project-Overview.md, Planning.md, Execution.md, Review.md, Output.md |
| 2026-05-18 | Phase 5 complete: Multi-provider AI system v1.3 — LLMProvider ABC, ProviderManager, ModelRegistry, runtime model switching, model selection UI (dashboard + Telegram), 6 new /models/* endpoints, 10/10 tests passing |

## Blockers
- ~~PostgreSQL and Redis not running locally~~ — resolved via `docker compose up -d postgres redis`
- ~~datasets + ragas packages not installed~~ — resolved via `pip install datasets ragas`
- ~~Garbled Grade 10 PDF text~~ — resolved via RapidOCR full extraction
- ~~Vector store permission issues~~ — resolved with new path `data/vectors_new/`

## Decisions Made
- Using ChromaDB for vector store (lightweight, no extra server)
- sentence-transformers for local embeddings with Ollama fallback
- python-telegram-bot v21 (async native)
- Next.js 14 App Router for teacher dashboard (9 pages)
- Chroma behind VectorStoreAdapter — swap without touching agents
- LangGraph for orchestration — replaces ad-hoc agent flow
- Hybrid RAG (dense + BM25 + reranker) for improved retrieval accuracy
- PyPdfium2 + RapidOCR for PDF extraction (handles font encoding issues)
- Per-page chunking to preserve accurate page numbers
- Explicit source citations in system prompts (not post-processing)
- Grade 10 requires full OCR (not just fallback) due to widespread garbled text
- `telegram_id` as BigInteger (large user IDs overflow Integer)
- DB table auto-creation on startup (eliminates manual init step)
- Callback patterns anchored at end (`^quiz$` not `^quiz`) to prevent re-entry
- `data/vectors_new/` as vector store path (old path had root-owned files)
