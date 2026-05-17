# EthioBio AI Assistant - Review

## Final Status
- Completed: v1.2 (Phases 1-3 complete, Phase 4 partially complete)
- On Budget: Yes (open-source stack, Ollama primary, fallback on-demand)
- On Time: Yes (delivered within May 2026)

## What Worked
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

## Retrospective
- **Team feedback**: Architecture is clean and modular. LangGraph pipeline is easy to understand and extend.
- **Technical debt**: Endpoint tests need better mocking. Dashboard proxy issue needs root-cause analysis.
- **Next priorities**: Voice support (Whisper), WhatsApp integration, CI/CD pipeline, pre-commit hooks.

## Handover Notes
- All 4 textbooks (Grades 9-12) ingested with enriched metadata. 1,165 chunks in `data/vectors_new/`.
- Vector store path: `./data/vectors_new` (ChromaDB + BM25 index)
- Ollama model: `gemma4:31b-cloud` (requires `ollama signin`)
- Telegram bot: polling mode, `@ethiobioaiassistant_bot`
- Dashboard: Next.js 14 on `:3000`, 9 pages
- API: FastAPI on `:8000`, 15 endpoints
- Docker: `docker compose up --build` starts all 6 services

## Final Sign-off
- [x] Approved — v1.2 complete
- Date: May 17, 2026
