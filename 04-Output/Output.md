# EthioBio AI Assistant - Output

## Final Deliverables

### Definition of Done (v1.2)
- [x] A student can use Telegram to ask biology questions
- [x] A teacher can generate and edit lesson plans and quizzes
- [x] The system uses Ollama first and falls back when needed
- [x] Curriculum grounding is active (hybrid RAG: dense + BM25 + reranker)
- [x] Progress tracking works (trend detection, weak areas)
- [x] Parent summaries work (bilingual)
- [x] All RAG responses include explicit source citations `(Grade X, Unit Y: Title, p. Z)`
- [x] Garbled textbook PDFs handled via OCR extraction
- [x] 4 textbooks ingested (Grades 9-12) with 1,165 chunks
- [x] The app is tested, deployed, and maintainable

## Documentation
- [[../00-Overview/PRD.md|Product Requirements Document v1.2]]
- [[../README.md|README — Quick Start, API docs, deployment guide]]
- [[../01-Planning/Planning.md|Planning Document]]
- [[../02-Execution/Execution.md|Execution Log]]
- [[../03-Review/Review.md|Review & Retrospective]]

## Metrics
| Metric | Target | Actual |
|--------|--------|--------|
| Python source files | — | 57 |
| Total Python lines | — | ~4,788 |
| Database models | 15 | 14 |
| Agents implemented | 10 | 8 core + orchestrator |
| LangGraph nodes | 5 | 5 |
| API endpoints | 10 | 15 |
| Tests | — | 7 test files, 23+ tests |
| Dashboard pages | — | 9 |
| Textbooks ingested | 4 | 4 (Grades 9-12) |
| Vector store chunks | — | 1,165 |
| Retrieval methods | Hybrid | Dense + BM25 + Cross-encoder reranker |

## Post-Project Actions
- [x] Deploy PostgreSQL + Redis (docker compose up -d postgres redis)
- [x] Pull Ollama models (gemma4:31b-cloud, tinyllama, nomic-embed-text)
- [x] Configure Telegram bot token in .env
- [x] Run initial test suite: pytest tests/ -v
- [x] Start API server: python -m src.main
- [x] Start Telegram bot: python -m src.telegram.bot
- [x] Ingest curriculum: python scripts/ingest_curriculum.py
- [ ] Add voice support (Whisper/STT)
- [ ] Add WhatsApp channel
- [ ] Set up CI/CD pipeline
- [ ] Add pre-commit hooks (ruff, mypy)

## Files Generated
### Core (src/)
- `config.py`, `main.py` — App entry and configuration (Pydantic Settings, FastAPI lifespan)
- `database/models.py` — 14 SQLAlchemy entities (UUID PKs, asyncpg, JSON columns, BigInteger for telegram_id)
- `database/session.py` — Async DB session management with auto-create tables
- `llm/ollama_client.py` — Ollama API integration (chat, embeddings, health)
- `llm/fallback.py` — OpenAI/Anthropic fallback adapters
- `llm/router.py` — Confidence-based model routing with DB logging
- `rag/embedder.py` — Local + Ollama embedding (dual backend)
- `rag/vector_store.py` — ChromaDB operations (PersistentClient)
- `rag/retriever.py` — Curriculum-aligned retrieval with filters
- `retrieval/adapter.py` — VectorStoreAdapter (dense + BM25 + rerank merge)
- `retrieval/bm25.py` — BM25Okapi sparse index with pickle persistence
- `retrieval/reranker.py` — Cross-encoder reranker (ms-marco-MiniLM-L-6-v2)
- `agents/base.py` — Abstract agent with tool calling
- `agents/orchestrator.py` — Intent classification + routing
- `agents/tutor.py` — Biology Q&A agent with source citations
- `agents/quiz.py` — Quiz generation agent (5 types, RAG-grounded)
- `agents/lesson_planner.py` — Lesson plan agent
- `agents/translator.py` — Amharic translation agent
- `agents/safety.py` — Content safety + hallucination guard (bidirectional revision)
- `agents/student_progress.py` — Performance analysis with trend detection
- `agents/parent_summary.py` — Weekly bilingual report generation
- `schemas/` — Pydantic models for all structured outputs (7 files)
- `api/` — FastAPI route handlers (chat, quiz, lesson, progress, admin, graph)
- `graph/` — LangGraph orchestration (StateGraph, 5 nodes, 20+ field AgentState)
- `graph/nodes/` — OrchestratorNode, RetrievalNode, SkipRetrievalNode, TutorNode, SafetyNode
- `telegram/bot.py` — PTB application with ConversationHandlers (interactive quiz, tutor, lesson)
- `telegram/keyboards.py` — Inline keyboard layouts (9 factory functions)
- `ingestion/docling_extractor.py` — PyPdfium2 + RapidOCR extraction, garbled detection, HybridChunker
- `evaluation/ragas_test.py` — Ragas evaluation + heuristic fallback + gold dataset
- `observability/tracing.py` — LangSmith tracing wrapper (optional)

### Dashboard (dashboard/)
- `src/app/page.tsx` — Dashboard home: stat cards, latency chart, activity table
- `src/app/ask/page.tsx` — Ask Q&A page
- `src/app/quizzes/page.tsx` — Quiz listing/management
- `src/app/quizzes/[id]/page.tsx` — Quiz detail
- `src/app/lessons/page.tsx` — Lesson plan listing
- `src/app/lessons/[id]/page.tsx` — Lesson detail
- `src/app/students/page.tsx` — Students listing
- `src/app/students/[id]/page.tsx` — Student detail
- `src/app/monitoring/page.tsx` — Monitoring/metrics
- `src/components/Sidebar.tsx` — Navigation sidebar (6 links)
- `src/components/StatCard.tsx` — Reusable stat card
- `src/components/Skeleton.tsx` — Loading skeleton components

### Infrastructure
- `docker-compose.yml` — 6 services: app, telegram-bot, postgres (pgvector), redis, ollama, dashboard
- `Dockerfile` — Python app container (python:3.12-slim, tesseract-ocr, torch CPU)
- `Dockerfile.dashboard` — Next.js container (node:20-alpine)
- `scripts/init-db.sql` — pgvector extension
- `scripts/ingest_curriculum.py` — PDF → ChromaDB + BM25 ingestion (Docling/OCR, CLI: --clear, --stats, --query)

### Tests
- `tests/test_llm.py` — Ollama chat, connection error, router fallback (4 tests)
- `tests/test_rag.py` — Embedder, retriever, format_context (3 tests)
- `tests/test_agents.py` — Tutor, Quiz, LessonPlanner, Orchestrator, Safety, Translator, StudentProgress (7 tests)
- `tests/test_api.py` — Health, quiz/generate, lesson-plan/generate, chat, admin/dashboard (5 tests)
- `tests/test_evaluation.py` — Gold set, Ragas imports, heuristic eval, gold set coverage (4 tests)
- `tests/conftest.py` — Fixtures: mock_router, mock_retriever

### Data
- `data/textbooks/` — Ethiopian curriculum PDFs (Grades 9-12)
- `data/vectors_new/` — ChromaDB persist directory + BM25 index (1,165 chunks)
- `data/evaluation/gold_set.json` — Ragas gold QA dataset (7 items)
