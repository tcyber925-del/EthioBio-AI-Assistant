# EthioBio AI Assistant - Review

## Final Status
- Completed: v1.3 (Phases 1-5 complete, Phase 4 partially complete)
- On Budget: Yes (open-source stack, Ollama primary, fallback on-demand)
- On Time: Yes (delivered within May 2026)

## What Worked
- **Multi-provider architecture**: `LLMProvider` ABC with clean fallback chain (Ollama → OpenAI → Anthropic → OpenAI-compatible). Runtime model switching without restarts.
- **Model auto-detection**: `ModelRegistry` discovers all locally installed Ollama models via `/api/tags`.
- **Model selection UI**: Dashboard (Ask, Quiz, Lesson pages) and Telegram bot (`/model` command) with inline keyboard.
- **LangGraph orchestration**: Clean separation of concerns with 5-node pipeline and bidirectional safety revision loop
- **Hybrid RAG**: Dense + BM25 + reranker significantly improved retrieval accuracy over single-vector approach
- **Docling+OCR extraction**: Resolved garbled Grade 10 textbook text (176/182 pages had font encoding issues)
- **Source citations**: `(Grade X, Unit Y: Title, p. Z)` format provides transparency and reduces hallucinations
- **Telegram bot**: Interactive quiz flow with inline buttons, conversation handlers, and `_reply_long()` for message splitting
- **DB auto-creation**: `Base.metadata.create_all()` on startup eliminates manual initialization steps
- **Docker Compose**: 6-service topology (app, bot, postgres, redis, ollama, dashboard) with health checks

## What Could Improve
- **Voice support**: Still stubbed — needs Whisper/STT integration for voice notes
- **WhatsApp channel**: Planned but not started
- **Test coverage**: Endpoint tests skip Ollama-dependent tests; need better mocking strategy
- **CI/CD**: No automated pipeline — manual testing and deployment
- **Pre-commit hooks**: No linting/typecheck enforcement before commits
- **Dashboard**: Next.js proxy causes socket hang-ups; bypassed but not root-caused
- **Grade 7-8 textbooks**: Not yet available for ingestion

## Lessons Learned
1. **PDF font encoding is a real problem**: Ethiopian curriculum PDFs have embedded fonts that produce garbled text. PyPdfium2 alone is insufficient — RapidOCR fallback is essential. Grade 10 required full OCR (34 minutes vs 5 seconds for other grades).
2. **Per-page chunking preserves accuracy**: Full-text splitting loses page number context. Per-page chunks ensure citations reference correct pages.
3. **Telegram callback patterns need anchors**: `^quiz` matches grade buttons too — must use `^quiz$` to prevent re-entry from submenus.
4. **Hybrid retrieval is worth the complexity**: BM25 catches keyword matches that dense embeddings miss. Cross-encoder reranker improves final result quality.
5. **Explicit citations in system prompts work better than post-processing**: LLM generates citations naturally when instructed, rather than appending them after the fact.
6. **Vector store paths matter**: Old `data/vectors/` had root-owned files from Docker runs. New `data/vectors_new/` avoids permission issues.
7. **DB table auto-creation simplifies deployment**: Deferring `create_all()` to first connection allows server start without DB being ready.
8. **Provider abstraction pays off**: `LLMProvider` ABC makes adding new providers trivial. `ProviderManager` fallback chain handles failures gracefully.
9. **`api_base_url` vs `dashboard_url`**: Separate config needed for Telegram bot to reach FastAPI backend in Docker (`http://app:8000` vs `http://localhost:3000`).
10. **Ollama model caching needs explicit refresh**: Both `OllamaProvider` and `ModelRegistry` cache model lists. `POST /models/refresh` clears both.

## Retrospective
- **Team feedback**: Architecture is clean and modular. LangGraph pipeline is easy to understand and extend. Multi-provider system adds flexibility without complexity.
- **Technical debt**: Endpoint tests need better mocking. Dashboard proxy issue needs root-cause analysis.
- **Next priorities**: Voice support (Whisper), WhatsApp integration, CI/CD pipeline, pre-commit hooks.

## Handover Notes
- All 4 textbooks (Grades 9-12) ingested with enriched metadata. 1,165 chunks in `data/vectors_new/`.
- Vector store path: `./data/vectors_new` (ChromaDB + BM25 index)
- Ollama models: `gemma4:31b-cloud` (default), `tinyllama:latest`, `nomic-embed-text:latest`, `nemotron-3-super:cloud`
- Provider chain: Ollama → OpenAI → Anthropic → OpenAI-compatible (LM Studio, vLLM)
- Telegram bot: polling mode, `@ethiobioaiassistant_bot`, model selection via `/model`
- Dashboard: Next.js 14 on `:3000`, 9 pages + model selector
- API: FastAPI on `:8000`, 21 endpoints (including 6 `/models/*`)
- Docker: `docker compose up --build` starts all 6 services
- Tests: 10/10 passing in `tests/test_llm.py`

## Final Sign-off
- [x] Approved — v1.3 complete
- Date: May 18, 2026
