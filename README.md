# EthioBio AI Assistant

AI-powered biology learning and teaching assistant for Ethiopian middle and high school education (Grades 7-12). Uses LangGraph orchestration, hybrid RAG (Dense + BM25 + Cross-encoder reranker), ChromaDB, Docling+OCR PDF extraction, and dynamic multi-provider AI system (Ollama, OpenAI, Anthropic).

## Features

- **Biology Q&A** — Ask biology questions, get curriculum-aligned answers with explicit source citations
- **Interactive Quiz** — Tap-to-answer quizzes with inline buttons, instant feedback, and score tracking
- **RAG-Grounded Generation** — Quiz questions and answers strictly based on Ethiopian textbook content
- **Lesson Planning** — Create structured lesson plans with objectives, activities, and assessments
- **Student Progress Tracking** — Monitor performance, identify weak areas, trend detection
- **Parent Summaries** — Weekly progress reports in English and Amharic
- **Amharic Support** — Bilingual explanations and translations
- **LangGraph Orchestration** — Intent classification → RAG retrieval → tutor → safety check → revise/finalize
- **Telegram Bot** — Primary user interface with interactive menus, commands, inline keyboards, conversation flows
- **Teacher Dashboard** — Next.js web dashboard (9 pages) for content review, approval workflow, monitoring
- **Hybrid RAG** — Dense (ChromaDB) + Sparse (BM25) + Cross-encoder reranker for accurate retrieval
- **Docling+OCR Extraction** — PyPdfium2 with RapidOCR fallback to handle garbled PDF font encoding
- **Source Citations** — Every answer cites `(Grade X, Unit Y: Title, p. Z)` format
- **Multi-Provider AI** — Ollama primary with OpenAI/Anthropic fallback chain, runtime model switching
- **Model Auto-Detection** — Discovers all locally installed Ollama models automatically
- **Model Selection UI** — Choose models in dashboard (Ask, Quiz, Lesson) and Telegram bot (`/model`)
- **Extensible Providers** — Clean `LLMProvider` interface for adding LM Studio, vLLM, llama.cpp
- **Recovery Plans** — Auto-generated remediation plans from weak topic detection, with XP rewards and milestone emails
- **Adaptive Quizzes** — Bayesian IRT ability estimation adjusts question difficulty per student per topic
- **Gamification** — XP, streaks, levels, achievements, mastery tracking across all activities
- **Notifications** — Email preference management with milestone alerts, review reminders, daily/weekly digests
- **Diagram Analysis** — Interactive diagram validation and labeling from textbook figures
- **DOCX/PDF Export** — Downloadable quizzes and lesson plans in Word and PDF formats
- **Spaced Repetition** — SM-2 based review scheduling for optimal memory retention
- **Activity Feed** — Recent user activity tracking across all learning interactions

## Architecture

```
src/
├── main.py                     # FastAPI server entry point
├── config.py                   # Pydantic Settings (env-based)
├── database/
│   ├── models.py               # 31 SQLAlchemy entities (UUID PKs, asyncpg, JSON columns)
│   └── session.py              # Async session with lazy engine, auto-create tables
├── llm/
│   ├── providers/              # Provider abstraction layer
│   │   ├── base.py             # LLMProvider ABC, ProviderInfo, ChatResponse
│   │   ├── ollama.py           # OllamaProvider (any local model)
│   │   ├── openai_provider.py  # OpenAIProvider (OpenAI, LM Studio, vLLM)
│   │   ├── anthropic_provider.py # AnthropicProvider (Claude)
│   │   └── openrouter.py       # OpenRouter-compatible provider
│   ├── manager.py              # ProviderManager — fallback chain orchestration
│   ├── registry.py             # ModelRegistry — auto-detect Ollama models
│   ├── ollama_client.py        # Ollama API wrapper (chat, embeddings, health)
│   ├── fallback.py             # OpenAI/Anthropic fallback adapter (legacy)
│   └── router.py               # ModelRouter — backward-compat wrapper over ProviderManager
├── rag/
│   ├── embedder.py             # Embedding via Ollama or sentence-transformers (dual backend)
│   ├── vector_store.py         # ChromaDB operations (PersistentClient)
│   └── retriever.py            # Curriculum search with grade/topic/unit filters
├── retrieval/                  # Hybrid search layer
│   ├── adapter.py              # VectorStoreAdapter — dense + BM25 + rerank merge
│   ├── bm25.py                 # BM25Okapi sparse index with pickle persistence
│   └── reranker.py             # Cross-encoder reranker (ms-marco-MiniLM-L-6-v2)
├── agents/
│   ├── base.py                 # Base agent with _call_llm
│   ├── orchestrator.py         # Intent classification + routing
│   ├── tutor.py                # Biology Q&A with source citations
│   ├── quiz.py                 # RAG-grounded quiz generation (5 types)
│   ├── lesson_planner.py       # Lesson plan generation
│   ├── translator.py           # English-Amharic translation
│   ├── safety.py               # Content review + hallucination guard
│   ├── student_progress.py     # Performance analytics + trend detection
│   ├── parent_summary.py       # Weekly bilingual report generation
│   ├── diagram.py              # Interactive diagram analysis + labeling
│   ├── recovery_agent.py       # LLM-based recovery plan generation
│   ├── spaced_repetition.py    # SM-2 spaced repetition scheduling
│   ├── weak_topic_detection.py # Post-quiz weak topic analysis + mastery sync
│   └── adaptive_quiz.py        # Bayesian IRT ability estimation + adaptive selection
├── graph/                      # LangGraph orchestration
│   ├── state.py                # AgentState (20+ fields), GraphOutput
│   ├── orchestrator.py         # Compiled graph: orchestrator → retrieve/skip → tutor → safety → revise/finalize
│   └── nodes/
│       ├── orchestrator.py     # Intent classifier, needs_retrieval routing
│       ├── retrieval.py        # RetrievalNode + SkipRetrievalNode
│       ├── tutor.py            # Answer generation with citations
│       └── safety.py           # Self-check + revision loop (reject/revise/finalize)
├── schemas/                    # 11 Pydantic schema files
├── api/
│   ├── chat.py                 # POST /chat
│   ├── quiz.py                 # POST /quiz/generate, /quiz/submit, /quiz/recommend
│   ├── lesson.py               # POST /lesson-plan/generate
│   ├── progress.py             # Progress + parent summary endpoints
│   ├── admin.py                # Dashboard, content review, monitoring, approve/reject
│   ├── graph.py                # POST /graph/chat, GET /graph/status
│   ├── diagram.py              # POST /diagram/generate, /diagram/validate, GET /diagram/textbook
│   ├── export.py               # GET /export/quiz, /export/lesson-plan (DOCX/PDF)
│   ├── gamification.py         # XP, streaks, levels, achievements, profile
│   ├── recovery.py             # Recovery plans, tasks, dashboard, schedule, notifications
│   ├── notifications.py        # Email preferences, verification, milestone alerts
│   └── activity.py             # GET /activity/{user_id}
├── telegram/
│   ├── bot.py                  # PTB Application (70 handlers, polling mode)
│   ├── keyboards.py            # Inline keyboard layouts (9 factory functions)
│   └── formatter.py            # Message formatting helpers
├── export/
│   ├── docx_exporter.py        # python-docx DOCX generation for quizzes/lessons
│   └── pdf_exporter.py         # fpdf2 PDF generation for quizzes/lessons
├── notifications/
│   ├── email_service.py        # Async SMTP sender (asyncio.to_thread)
│   └── templates/              # 3 Jinja2 HTML email templates
├── ingestion/
│   ├── docling_extractor.py    # PyPdfium2 + RapidOCR extraction, garbled detection, HybridChunker
│   └── diagram_extractor.py    # Diagram extraction from textbooks
├── evaluation/
│   └── ragas_test.py           # Ragas evaluation + heuristic fallback + gold dataset
└── observability/
    └── tracing.py              # LangSmith tracing (optional)
dashboard/                      # Next.js teacher dashboard (7 routes)
scripts/
├── ingest_curriculum.py        # PDF → ChromaDB + BM25 ingestion with Docling/OCR
├── ingest_diagrams.py          # Ingest textbook diagrams into vector store
├── index_diagrams.py           # Index diagrams for search
├── label_textbook_diagrams.py  # Label textbook diagrams
├── send_digests.py             # Cron-ready daily/weekly digest email sender
├── init-db.sql                 # pgvector extension init
└── ralph/                      # Autonomous agent PRD tasks
tests/                          # pytest suite (20 test files, asyncio_mode=auto)
data/
├── textbooks/                  # Ethiopian curriculum PDFs (Grades 9-12)
├── evaluation/
│   └── gold_set.json           # Ragas gold QA dataset
└── vectors_new/                # ChromaDB persist + BM25 index
```

### LangGraph Pipeline

```
entry → orchestrator → needs_retrieval? → retrieve ─┐
                  │                       skip_retr. ┤
                  └──────────────────────────────────→ tutor → safety → END / revise→tutor
```

### Hybrid RAG Pipeline

```
query → embed → dense search (ChromaDB) + sparse search (BM25) → merge (0.6/0.4) → rerank (cross-encoder) → top-k → format context
```

### Citation Format

All RAG-grounded responses include explicit source citations:

```
(Grade X, Unit Y: Title, p. Z)
```

Example: `(Grade 10, Unit 3: Biochemical Molecules, p. 72)`

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Ollama (signed in for cloud models)

### Setup

```bash
# Enter project directory
cd "EthioBio AI Assistant"

# Copy environment and edit with your settings
cp .env.example .env
# Set TELEGRAM_BOT_TOKEN, OLLAMA_CHAT_MODEL, etc.

# Start infrastructure
docker compose up -d postgres redis

# Create database tables (auto-created on first connection)
source .venv/bin/activate
python -c "
from sqlalchemy import create_engine
from src.database.models import Base
engine = create_engine('postgresql://ethiobio:ethiobio_pass@localhost:5432/ethiobio')
Base.metadata.create_all(engine)
"

# Sign in to Ollama (for cloud models like gemma4:31b-cloud)
ollama signin

# Pull Ollama models
ollama pull gemma4:31b-cloud
ollama pull tinyllama          # fallback
ollama pull nomic-embed-text   # embeddings

# Install Python dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Start the API server
python -m src.main

# In another terminal, start the Telegram bot
python -m src.telegram.bot
```

### Curriculum Ingestion

Place Ethiopian biology textbook PDFs in the grade directories:

```
data/textbooks/
├── Grade9/Grade_9_Biology_Textbook.pdf
├── Grade10/grade_10-biology_kehulumcom.pdf
├── Grade11/grade-11-biology-new-curriculum.pdf
└── Grade12/Grade_12_Biology_Textbook.pdf
```

Then run:

```bash
source .venv/bin/activate
python scripts/ingest_curriculum.py

# Verify
python scripts/ingest_curriculum.py --stats
python scripts/ingest_curriculum.py --query "What is DNA replication?" --grade 12
```

**Note:** Grade 10 textbooks with font encoding issues require full OCR extraction (RapidOCR). The ingestion script auto-detects garbled pages (alpha character ratio < 40%) and falls back to OCR automatically.

### Docker (full stack)

```bash
docker compose up --build
```

Services:
- **App** — FastAPI on `:8000`
- **Telegram Bot** — PTB polling mode
- **PostgreSQL** — pgvector/pg16 on `:5432`
- **Redis** — caching on `:6379`
- **Ollama** — model serving on `:11435` (host) / `:11434` (container)
- **Dashboard** — Next.js on `:3000`

## Environment Variables

Key environment variables (see `.env.example` for full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | (required) |
| `OLLAMA_CHAT_MODEL` | Primary LLM model | `gemma4:31b-cloud` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_EMBED_MODEL` | Embedding model | `nomic-embed-text` |
| `DATABASE_URL` | PostgreSQL async connection | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `FALLBACK_PROVIDER` | Fallback provider | `openai` or `anthropic` |
| `FALLBACK_API_KEY` | Fallback API key | (required if fallback enabled) |
| `VECTOR_STORE_PATH` | ChromaDB persist directory | `./data/vectors_new` |
| `LANGCHAIN_API_KEY` | LangSmith tracing | (optional) |
| `API_BASE_URL` | Backend API URL for Telegram bot | `http://app:8000` |
| `PROVIDER_OPENAI_COMPATIBLE_NAME` | OpenAI-compatible provider name | (optional) |
| `PROVIDER_OPENAI_COMPATIBLE_URL` | OpenAI-compatible provider URL | (optional) |
| `PROVIDER_OPENAI_COMPATIBLE_API_KEY` | OpenAI-compatible API key | (optional) |
| `PROVIDER_OPENAI_COMPATIBLE_MODEL` | OpenAI-compatible model name | (optional) |

## API Endpoints

| Method | Path | Module | Description |
|--------|------|--------|-------------|
| GET | `/health` | — | Health check (Ollama + DB status) |
| POST | `/chat` | Chat | Biology Q&A with RAG |
| POST | `/graph/chat` | Graph | LangGraph pipeline (intent → RAG → tutor → safety) |
| GET | `/graph/status` | Graph | Graph structure (nodes + edges) |
| GET | `/quiz/recommend/{user_id}` | Quiz | Recommend quiz parameters |
| POST | `/quiz/generate` | Quiz | Generate RAG-grounded quiz |
| POST | `/quiz/submit` | Quiz | Submit quiz answers, record attempts, update ability |
| POST | `/lesson-plan/generate` | Lesson | Create lesson plan |
| GET | `/progress/student/{student_id}` | Progress | Get student progress |
| POST | `/progress/student/{student_id}` | Progress | Record progress entry |
| POST | `/progress/parent-summary` | Progress | Generate parent summary |
| GET | `/admin/dashboard` | Admin | Dashboard overview |
| GET | `/admin/content/review` | Admin | Review content (use `type=quiz\|lesson`) |
| GET | `/admin/monitoring` | Admin | System monitoring |
| GET | `/admin/content/quiz/{item_id}` | Admin | Quiz detail with all questions |
| GET | `/admin/content/lesson/{item_id}` | Admin | Lesson detail with full content |
| PATCH | `/admin/content/{type}/{id}/status` | Admin | Approve/reject content |
| GET | `/models` | Models | List available models across all providers |
| GET | `/models/providers` | Models | Provider health and info |
| GET | `/models/active` | Models | Get currently active model |
| POST | `/models/active` | Models | Set active model |
| GET | `/models/health` | Models | Health check for all providers |
| POST | `/models/refresh` | Models | Force refresh Ollama model cache |
| POST | `/diagram/generate` | Diagram | Generate diagram analysis |
| POST | `/diagram/validate` | Diagram | Validate diagram labels |
| GET | `/diagram/textbook` | Diagram | List textbook diagrams |
| GET | `/export/quiz/{quiz_id}` | Export | Download quiz as DOCX/PDF |
| GET | `/export/lesson-plan/{lesson_id}` | Export | Download lesson plan as DOCX/PDF |
| POST | `/gamification/xp` | Gamification | Award XP (internal) |
| GET | `/gamification/profile/{user_id}` | Gamification | XP, level, streak, mastery, achievements |
| POST | `/gamification/activity` | Gamification | Log activity + update streak |
| GET | `/gamification/events/{user_id}` | Gamification | List XP events |
| GET | `/gamification/achievements/{user_id}` | Gamification | Achievement definitions + progress |
| POST | `/recovery/plan` | Recovery | Create recovery plan |
| GET | `/recovery/plan/{user_id}` | Recovery | List recovery plans |
| POST | `/recovery/task/complete` | Recovery | Complete task (XP + milestone check + email) |
| POST | `/recovery/auto-generate/{user_id}` | Recovery | Auto-generate plan from weak topics |
| GET | `/recovery/weak-topics/{user_id}` | Recovery | Get weak topics with severity |
| GET | `/recovery/history/{user_id}/{topic}` | Recovery | Mastery history for a topic |
| GET | `/recovery/dashboard/{user_id}` | Recovery | Combined weak topics + plans + recommendations |
| GET | `/recovery/schedule/{user_id}` | Recovery | Get spaced repetition schedule |
| GET | `/recovery/schedule/due/{user_id}` | Recovery | Get due reviews |
| POST | `/recovery/schedule/generate/{user_id}` | Recovery | Generate review schedule |
| POST | `/recovery/schedule/review` | Recovery | Record review result |
| GET | `/recovery/notifications/{user_id}` | Recovery | List recovery notifications |
| PATCH | `/recovery/notifications/{notification_id}/read` | Recovery | Mark notification read |
| PUT | `/recovery/notifications/read-all/{user_id}` | Recovery | Mark all notifications read |
| GET | `/notifications/preferences/{user_id}` | Notifications | Get email preferences |
| PUT | `/notifications/preferences/{user_id}` | Notifications | Update email preferences |
| POST | `/notifications/preferences/{user_id}/verify` | Notifications | Send verification code |
| POST | `/notifications/preferences/{user_id}/verify/{code}` | Notifications | Confirm verification code |
| GET | `/activity/{user_id}` | Activity | Get recent activity feed |

## Telegram Bot

The bot runs on **polling mode**. Search `@ethiobioaiassistant_bot` on Telegram.

### Interactive Quiz Flow

```
User selects "📝 Take a Quiz" → picks type → picks grade → types topic
Bot shows Question 1 with inline answer buttons (A/B/C/D)
User taps answer → instant feedback (✅ Correct / ❌ Wrong + explanation)
→ Next question → ... → Final score with Retry option
```

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Show main menu with icons |
| `/help` | Show help text |
| `/menu` | Return to main menu |
| `/ask <question>` | Ask a biology question directly |
| `/quiz [grade] [topic]` | Start interactive quiz |
| `/grade <7-12>` | Set default grade level |
| `/language <en\|am\|both>` | Set language |
| `/cancel` | Cancel current operation |
| `/model` | Select LLM model |
| `/socratic` | Toggle Socratic tutoring mode |
| `/hint` | Get a hint on current question |
| `/reveal` | Reveal the answer |
| `/settings` | Manage email notification preferences |
| `/email <address>` | Set email address for notifications |
| `/recovery` | View recovery plans and tasks |
| `/progress` | Show mastery progress per topic (text bar charts) |

### Menu Layout

```
Main Menu
├── 🧬 Ask a Question    → text input → LLM answer
├── 📝 Take a Quiz       → type → grade → topic → interactive quiz
├── 📊 My Progress       → stats (requires PostgreSQL)
├── 🌐 Language          → en / am / both
├── 🤖 Model Selection   → choose LLM model
├── 🔄 Recovery Plan     → view plans → complete tasks
├── ⚙️ Settings          → email notifications → verify
├── 👨‍🏫 Teacher Tools     → Lesson Plan + Dashboard links
└── ❓ Help
```

### Start the Bot

```bash
source .venv/bin/activate
python -m src.telegram.bot
```

### Troubleshooting

**Bot doesn't respond:**
1. Kill other instances: `pkill -f telegram.bot`
2. Clear stale connections:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/deleteWebhook?drop_pending_updates=true"
   curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates?offset=999999999"
   ```
3. Check for Conflict errors in the bot log

**Long messages cropped:** The bot automatically splits responses >4096 chars into multiple messages via `_reply_long()`.

**Teacher Tools buttons don't work:** The submenu uses `callback_data` instead of `url` buttons (Telegram blocks HTTP URLs). URL buttons require HTTPS which isn't available on localhost.

**Garbled textbook text:** Grade 10 textbooks have font encoding issues. The ingestion script auto-detects garbled pages (alpha ratio < 40%) and uses RapidOCR. If needed, force full OCR with `--use-docling` flag.

**Quiz/Lesson re-entry from grade buttons:** Callback patterns must anchor at end (`^quiz$` not `^quiz`). This is fixed in the current codebase.

## Testing

```bash
# Run unit tests (skip endpoint tests that hit real Ollama)
pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"

# RAG verification
python scripts/ingest_curriculum.py --query "What is protein synthesis?" --grade 12

# Live agent test
python -c "
import asyncio
from src.graph.orchestrator import run_graph
result = asyncio.run(run_graph('What is a cell?', grade_level=12))
print(result.answer)
"

# Evaluation (requires datasets + ragas)
pip install datasets ragas
python -c "from src.evaluation.ragas_test import run_evaluation; import asyncio; asyncio.run(run_evaluation())"
```

Set `LANGCHAIN_API_KEY` to enable LangSmith tracing.

## Bug Fixes Applied

- Multi-provider system: LLMProvider ABC, ProviderManager, ModelRegistry, runtime model switching
- Model selection UI: Dashboard (Ask, Quiz, Lesson pages) + Telegram bot (/model command)
- /models/* API endpoints: list, health, active model, refresh
- Next.js proxy: Added /models/* rewrite rule for dashboard model selector
- api_base_url config: Dedicated setting for Telegram bot to reach FastAPI backend
- `_get_or_create_user`: Session parameter was `None` — now creates its own session
- `handle_question`: DB save was inside the answer try/except — now independent
- `main()`: Missing `await app.start()` after `start_polling()` — handlers never fired
- Quiz handler pattern: `pattern="^quiz"` matched grade buttons too — fixed to `pattern="^quiz$"`
- Lesson handler pattern: `pattern="^lesson_plan"` — same fix, added `$` anchor
- `_reply_long()` helper: Long LLM responses >4096 chars are now split into multiple messages
- Teacher Tools URLs: HTTP URLs rejected by Telegram — changed to `callback_data` buttons
- QuizAgent RAG grounding: Quiz questions now generated from textbook content, not general knowledge
- `LessonPlan.teacher_id`: Changed to nullable for unauthenticated requests
- `telegram_id`: Changed from `Integer` to `BigInteger` for large Telegram user IDs
- Database `init_db()`: Deferred to first connection to allow server start without DB
- QuizAgent JSON parsing: Handles LLM returning `list` instead of `dict`
- `/admin/content/review`: Accepts both `type` and `content_type` params for dashboard compatibility
- Dashboard API calls: Bypass Next.js proxy for generation endpoints (socket hang-up fix)
- DB table auto-creation: `Base.metadata.create_all()` on startup eliminates manual init step
- Garbled PDF text: PyPdfium2 + RapidOCR fallback with auto-detection (alpha ratio < 40%)
- Grade 10 OCR: Full RapidOCR extraction required (176/182 pages garbled due to font encoding)
- Hybrid RAG: Dense + BM25 + cross-encoder reranker replaces single-vector retrieval
- Citation format: Explicit `(Grade X, Unit Y: Title, p. Z)` citations in all RAG responses
- Per-page chunking: Preserves accurate page numbers instead of full-text splitting
- Vector store path: `data/vectors_new/` (old `data/vectors/` had permission issues)
- Gamification module: XP, streaks, levels, achievements across quiz/tutor/recovery activities
- Recovery plans: Auto-generated remediation plans from weak topic detection, task completion flow, milestone bonus XP
- Adaptive quiz engine: Bayesian IRT ability estimation with logit model, per-topic StudentAbility tracking, difficulty_score column
- Weak topic detection: Post-quiz analysis updates StudentMastery, detects MisconceptionPattern, syncs StudentProfile
- Notification preferences: User email management with 6-digit verification code, digi frequency options
- Email service: Async SMTP via asyncio.to_thread(), Jinja2 HTML templates, milestone alerts at 10%+ progress
- Digest script: Cron-ready `scripts/send_digests.py` for daily/weekly mastery change + review reminder emails
- Bot notification commands: `/settings` and `/email` commands with inline keyboard flows for preference management
- Bot command menu: Registered via `set_my_commands()` at startup for discoverable command list

## Evaluation

```bash
pip install datasets ragas
python -c "from src.evaluation.ragas_test import run_evaluation; import asyncio; print(asyncio.run(run_evaluation(...)))"
```

Set `LANGCHAIN_API_KEY` to enable LangSmith tracing.

## Deployment

1. Configure `.env` with production values (secret keys, tokens)
2. Start PostgreSQL + Redis: `docker compose up -d postgres redis`
3. Ingest curriculum: `python scripts/ingest_curriculum.py`
4. Start API: `python -m uvicorn src.main:app --host 0.0.0.0 --port 8000`
5. Start bot: `python -m src.telegram.bot`
6. Start dashboard: `cd dashboard && npm run build && npx next start -p 3000`
7. (Optional) Set `TELEGRAM_WEBHOOK_URL` for production webhook mode

## Project Metrics

| Metric | Value |
|--------|-------|
| Python source files | 90 |
| Total Python lines | ~68,600 |
| Database models | 31 |
| Providers | 3 (Ollama, OpenAI, Anthropic) + extensible |
| Agents | 14 (Tutor, Quiz, LessonPlanner, Safety, Translator, StudentProgress, ParentSummary, Orchestrator, Diagram, RecoveryAgent, SpacedRepetition, WeakTopicDetection, AdaptiveQuiz, Base) |
| LangGraph nodes | 5 (orchestrator, retrieve, skip_retrieval, tutor, safety) |
| API endpoints | 47 |
| Test files | 20 |
| Dashboard pages | 9 |
| Textbooks ingested | 4 (Grades 9-12) |
| Vector store chunks | 1,165 |
| Retrieval methods | Hybrid (Dense + BM25 + Cross-encoder reranker) |
