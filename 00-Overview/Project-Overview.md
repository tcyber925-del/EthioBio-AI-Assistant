---
title: EthioBio AI Assistant
---
# EthioBio AI Assistant

## Overview
- **Project Name**: EthioBio AI Assistant
- **Status**: Active — v1.3
- **Start Date**: May 2026
- **Target Date**: —
- **Priority**: High

## Stakeholders
### Primary Users
- Biology teachers
- Middle school students
- High school students

### Secondary Users
- Parents
- School administrators
- Tutors and exam-prep centers

## Goals
1. Reduce biology teacher workload.
2. Improve student understanding and practice.
3. Support curriculum-aligned biology learning.
4. Work in low-bandwidth and mixed-resource environments.
5. Use local/open models first to reduce cost and improve control.
6. Provide fallback AI providers for reliability.
7. Offer a modular AI-agent architecture that can grow over time.
8. Ensure all answers cite their textbook sources for transparency.

## Deliverables
### Phase 1 ✅ Complete
Telegram bot, basic tutoring, Ollama integration, retrieval.

### Phase 2 ✅ Complete
Quiz generation, lesson planning, teacher review tools.

### Phase 3 ✅ Complete
Student progress tracking, parent summaries, analytics.

### Phase 4 🔄 In Progress
Voice support (stubbed), OCR (integrated for garbled PDFs), WhatsApp integration (planned), exports (stubbed).

### Phase 5 ✅ Complete
Dynamic multi-provider AI system: `LLMProvider` ABC, `ProviderManager` fallback chain, `ModelRegistry` auto-detection, runtime model switching, model selection UI in dashboard and Telegram bot, 6 new `/models/*` API endpoints.

## Dependencies
- Ollama for local/cloud model hosting (primary, auto-detects available models)
- OpenAI API (fallback provider)
- Anthropic API (fallback provider)
- OpenAI-compatible providers (LM Studio, vLLM)
- PostgreSQL 16 with pgvector for data storage
- Redis 7 for caching and background jobs
- ChromaDB + BM25 for hybrid vector retrieval
- Telegram Bot API

## Timeline
| Phase | Start | End | Status |
|-------|-------|-----|--------|
| Planning | May 2026 | May 2026 | ✅ Complete |
| Execution | May 2026 | May 2026 | ✅ Complete (v1.3) |
| Review | — | — | Pending |

## Notes
English-first product (Ethiopian biology curriculum is in English) with Amharic support for explanations, parent communication, and accessibility. All RAG responses include explicit source citations in `(Grade X, Unit Y: Title, p. Z)` format. 4 textbooks ingested (Grades 9-12) with 1,165 chunks.

## Resources
- [[./PRD.md|Full PRD Document v1.3]]

## Actions
- [x] Define detailed implementation plan
- [x] Set up project infrastructure
- [x] Implement LangGraph orchestration
- [x] Implement hybrid RAG (dense + BM25 + reranker)
- [x] Implement Docling+OCR PDF extraction
- [x] Implement source citations
- [ ] Add voice support (Whisper/STT)
- [ ] Add WhatsApp channel
- [ ] Add PDF/DOCX export
