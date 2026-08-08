# EthioBio AI Assistant

AI-powered biology learning and teaching assistant for Ethiopian middle and high school education (Grades 7-12). Uses LangGraph orchestration (unified graph with 12+ nodes), hybrid RAG (Dense + BM25 + Cross-encoder reranker), pgvector, and dynamic multi-provider AI system (Ollama, OpenRouter, OpenAI, Anthropic, OpenAI-compatible).

## Features

- **Biology Q&A** — Ask biology questions, get curriculum-aligned answers with explicit source citations
- **Interactive Quiz** — Tap-to-answer quizzes with inline buttons, instant feedback, and score tracking
- **RAG-Grounded Generation** — Quiz questions and answers strictly based on Ethiopian textbook content
- **Lesson Planning** — Create structured lesson plans with objectives, activities, and assessments
- **Student Progress Tracking** — Monitor performance, identify weak areas, trend detection
- **Parent Summaries** — Weekly progress reports in English and Amharic
- **Amharic Support** — Bilingual explanations and translations
- **LangGraph Orchestration** — Unified graph: intent classification → planner/retrieve/skip → plan_executor → evidence_graph → sufficient_context → synthesis → tutor → hallucination → claim_verifier → safety → finalize/revise/reject
- **Agentic RAG** — Query rewriting, multi-index parallel search, iterative retrieval, claim verification
- **Telegram Bot** — Primary user interface with interactive menus, commands, inline keyboards, conversation flows
- **Teacher Dashboard** — Next.js web dashboard (9 pages) for content review, approval workflow, monitoring
- **Hybrid RAG** — Dense (pgvector) + Sparse (BM25) + Cross-encoder reranker for accurate retrieval
- **Source Citations** — Every answer cites `(Grade X, Unit Y: Title, p. Z)` format
- **Multi-Provider AI** — Ollama primary with OpenRouter/OpenAI/Anthropic fallback chain, circuit breakers per provider
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
- **Cookie-Based JWT Auth** — Secure HTTP-only cookie authentication with refresh token rotation and Redis JTI revocation
- **Tiered Rate Limiting** — 6-tier Redis-backed rate limiting with X-RateLimit-* headers
- **PII Redaction** — Right-to-left position-based string slicing for PII in outputs
- **LLM Circuit Breaker** — Per-provider CLOSED/OPEN/HALF_OPEN state machine with automatic recovery

## Architecture

```
src/
├── main.py                     # FastAPI server entry point
├── config.py                   # Pydantic Settings (env-based), ~80 vars
├── redis_client.py             # Global lazy Redis singleton (async)
├── database/
│   ├── models.py               # 31+ SQLAlchemy entities (UUID PKs, asyncpg, JSON columns)
│   └── session.py              # Async session with lazy engine, auto-create tables
├── llm/
│   ├── providers/              # Provider abstraction layer
│   │   ├── base.py             # LLMProvider ABC, ProviderInfo, ChatResponse
│   │   ├── ollama.py           # OllamaProvider (any local model)
│   │   ├── openai_provider.py  # OpenAIProvider (OpenAI, LM Studio, vLLM)
│   │   ├── anthropic_provider.py # AnthropicProvider (Claude)
│   │   └── openrouter.py       # OpenRouter-compatible provider
│   ├── manager.py              # ProviderManager — fallback chain orchestration + circuit breakers
│   ├── circuit_breaker.py      # Per-provider circuit breaker (threshold=5, recovery_timeout=30s, half_open_max=3)
│   ├── registry.py             # ModelRegistry — auto-detect Ollama models
│   ├── ollama_client.py        # Ollama API wrapper (chat, embeddings, health)
│   └── router.py               # ModelRouter — backward-compat wrapper over ProviderManager
├── rag/
│   ├── embedder.py             # Embedding via fastembed (ONNX) or Ollama fallback
│   ├── vector_store.py         # pgvector wrapper (delegating — ChromaDB removed)
│   ├── pgvector_store.py       # Raw pgvector operations
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
│   └── planner/                # Agentic RAG planner
│       ├── planner.py          # PlannerAgent — generates execution plans
│       ├── query_rewriter.py   # QueryRewriterAgent — query expansion
│       └── search_fanout.py    # SearchFanoutAgent — multi-index parallel search
├── graph/                      # LangGraph orchestration
│   ├── state.py                # AgentState (50+ fields), GraphOutput
│   ├── orchestrator.py         # Compiled graph: build_unified_graph() (production)
│   └── nodes/
│       ├── orchestrator.py     # Intent classifier, complexity scoring, routing
│       ├── planner.py          # Plan generation (complex queries)
│       ├── plan_executor.py    # Iterates subtasks, calls QueryRewriter + SearchFanout
│       ├── query_rewriter.py   # LLM-based query expansion
│       ├── search_fanout.py    # Parallel multi-index retrieval
│       ├── evidence_graph.py   # Dedup, persist, select, analyze
│       ├── sufficient_context.py # Coverage evaluation + loop controller
│       ├── synthesis.py        # Evidence synthesis
│       ├── retrieval.py        # RetrievalNode + SkipRetrievalNode
│       ├── tutor.py            # Dual-mode tutor (legacy or agentic synthesis)
│       ├── hallucination.py    # Hallucination detection
│       ├── claim_verifier.py   # Claim extraction + verification against evidence
│       └── safety.py           # LLM safety check + citation/quote verification
├── schemas/                    # Pydantic schema files
│   ├── common.py               # HealthResponse, etc.
│   ├── streaming.py            # TokenChunk for SSE streaming
│   └── ...                     # Other schemas
├── api/                        # FastAPI route modules
│   ├── auth.py                 # Cookie-based JWT auth (register, token, refresh, logout, me, OTP)
│   ├── internal.py             # Internal API key auth (/internal/health)
│   ├── chat.py                 # POST /chat
│   ├── quiz.py                 # POST /quiz/generate, /quiz/submit, /quiz/recommend
│   ├── lesson.py               # POST /lesson-plan/generate
│   ├── progress.py             # Progress + parent summary endpoints
│   ├── admin.py                # Dashboard, content review, monitoring, approve/reject
│   ├── graph.py                # POST /graph/chat, GET /graph/status, traces
│   ├── diagram.py              # POST /diagram/generate, /diagram/validate, GET /diagram/textbook
│   ├── export.py               # GET /export/quiz, /export/lesson-plan (DOCX/PDF)
│   ├── gamification.py         # XP, streaks, levels, achievements, profile
│   ├── recovery.py             # Recovery plans, tasks, dashboard, schedule, notifications
│   ├── notifications.py        # Email preferences, verification, milestone alerts
│   ├── activity.py             # GET /activity/{user_id}
│   ├── models.py               # Model listing, health, active model, refresh
│   ├── students.py             # Student operations (teacher-facing)
│   ├── teacher.py              # Teacher operations
│   ├── parent.py               # Parent dashboard operations
│   ├── users.py                # User management
│   ├── workspace.py            # Workspace management
│   ├── collection.py           # Content collections
│   ├── assignment.py           # Assignments
│   ├── bookmark.py             # Bookmarks
│   ├── memory.py               # Memory management
│   ├── agent_orchestrator.py   # Agent orchestration
│   ├── knowledge.py            # Knowledge platform
│   ├── tracing.py              # Trace viewing API
│   ├── retrieval.py            # Retrieval API
│   ├── intelligence/           # Adaptive intelligence
│   │   ├── continue_learning_router.py
│   │   └── ...
│   ├── misconceptions.py       # Misconception detection
│   └── ekg.py                  # Educational knowledge graph
├── telegram/
│   ├── bot.py                  # PTB Application (3600+ lines, 50+ handlers, 6 conversation flows)
│   ├── keyboards.py            # Inline keyboard layouts (9+ factory functions)
│   └── formatter.py            # Message formatting helpers
├── guardrails/
│   ├── input/
│   │   ├── middleware.py       # App-wide rate-limit middleware (6 tiers)
│   │   ├── rate_limiter.py     # TieredRateLimiter with Redis sorted sets
│   │   ├── sanitizer.py        # Input sanitization
│   │   └── prompt_injection.py # Prompt injection detection
│   ├── output/
│   │   ├── pii_scanner.py      # PII redaction (position-based)
│   │   ├── toxicity.py         # Toxicity detection
│   │   └── topic_enforcer.py   # Topic enforcement
│   ├── tool_guard.py           # Tool usage guardrails
│   └── startup.py              # Startup checks (fatal on default SECRET_KEY)
├── core/
│   ├── errors.py               # AppError hierarchy with structured dict serialization
│   ├── monitoring.py           # PipelineMonitor, LRU trace eviction
│   ├── tracing.py              # TraceRepository, Trace dataclass
│   ├── memory/                 # Cross-session memory, router
│   ├── evidence/               # Evidence graph, selector, scoring, summarizer
│   ├── pipeline/               # Document ingestion pipeline (PDF/DOCX → chunks → embed → index)
│   ├── knowledge_registry.py   # Lifecycle management for knowledge items
│   ├── storage.py              # LocalFileStorage
│   ├── event_infrastructure/   # Event bus
│   └── workspace/              # Workspace dependencies
├── export/
│   ├── docx_exporter.py        # python-docx DOCX generation for quizzes/lessons
│   └── pdf_exporter.py         # fpdf2 PDF generation for quizzes/lessons
├── notifications/
│   ├── email_service.py        # Async SMTP sender (asyncio.to_thread)
│   └── templates/              # Jinja2 HTML email templates
├── ingestion/
│   ├── docling_extractor.py    # PyPdfium2 + RapidOCR extraction, garbled detection, HybridChunker
│   └── diagram_extractor.py    # Diagram extraction from textbooks
├── observability/
│   ├── tracing.py              # OTel span helpers + GenAI semconv constants
│   ├── metrics.py              # Counter/Gauge/Histogram registry + Prometheus text export
│   ├── structured_logging.py   # Consistent log_event schema via structlog
│   ├── health.py               # ModuleHealthRegistry for per-module health checks
│   ├── alerting.py             # Threshold-driven alert manager
│   ├── instrumentation.py      # OTel SDK init + OpenLLMetry (optional)
│   ├── guardrail_instrumentation.py  # @observe_guardrail decorator
│   └── evaluation/             # Async eval pipeline
│       ├── sampler.py          # EvalSampler with sampling rate
│       ├── judge.py            # LLMJudge for answer quality
│       ├── writer.py           # evaluate_and_write
│       ├── drift.py            # Drift detection
│       ├── runner.py           # Batch evaluation runner
│       └── datasets/           # Gold datasets
├── data/                       # Data directory
│   ├── textbooks/              # Ethiopian curriculum PDFs (Grades 9-12)
│   ├── evaluation/             # Gold datasets
│   └── vectors_new/            # BM25 index + vector store artifacts
├── services/                   # Domain services
├── retrieval/                  # Search layer
├── schemas/                    # Pydantic schemas
├── utils/                      # Utility functions
└── agents/                     # LLM agents
```

### Unified LangGraph Pipeline

```
entry → orchestrator → _route_after_orchestrator
           │
           ├── "planner" → plan_executor → evidence_graph → sufficient_context
           │       └── route_after_sufficiency:
           │           ├── "synthesis" → synthesis → tutor
           │           ├── "rewrite" → plan_executor
           │           └── "replan" → planner
           │
           ├── "retrieve" → tutor
           └── "skip_retrieval" → tutor

tutor → hallucination → claim_verifier → route_after_verification
    ├── "finalize" → safety → END
    ├── "revise" → tutor (max 2)
    └── "reject" → safety → END
         safety ←───────────────────┘
```

### Hybrid RAG Pipeline

```
query → embed → dense search (pgvector) + sparse search (BM25) → merge (0.6/0.4) → rerank (cross-encoder) → top-k → format context
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

# Start the API server (includes bot when TELEGRAM_BOT_TOKEN is set)
python -m src.main

# Or start bot separately (polling mode)
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

### Docker (full stack)

```bash
docker compose up --build
```

Services:
- **App** — FastAPI on `:8000` (API + bot in webhook mode)
- **Telegram Bot** — Separate container in polling mode
- **PostgreSQL** — pgvector/pg16 on `:5432`
- **Redis** — caching on `:6379`
- **Ollama** — model serving on `:11435` (host) / `:11434` (container)
- **Cron** — Daily proactive reminders
- **Jaeger** — Trace collection on `:16686`
- **Prometheus** — Metric scraping on `:9090`
- **Grafana** — Dashboards on `:3001` (default: admin/ethiobio)
- **Dashboard** — Next.js on `:3000`

## Environment Variables

Key environment variables (see `.env.example` for full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | (required) |
| `OLLAMA_CHAT_MODEL` | Primary LLM model | `tinyllama` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_API_KEY` | Ollama Cloud API key | (optional) |
| `OLLAMA_EMBED_MODEL` | Embedding model | `nomic-embed-text` |
| `DATABASE_URL` | PostgreSQL async connection | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection | `redis://localhost:6379/0` |
| `OPENROUTER_API_KEY` | OpenRouter API key | (optional) |
| `FALLBACK_PROVIDER` | Fallback provider | `openai` or `anthropic` |
| `FALLBACK_API_KEY` | Fallback API key | (required if fallback enabled) |
| `JWT_SECRET` | JWT signing secret | (required — hard-blocks with SystemExit if default) |
| `SECRET_KEY` | App secret key | (required — hard-blocks with SystemExit if default) |
| `SENTRY_DSN` | Sentry DSN for error tracking | (optional) |
| `OTEL_ENDPOINT` | OTLP gRPC endpoint | (optional) |
| `DASHBOARD_URL` | Frontend URL for CORS | `http://localhost:3000` |
| `API_BASE_URL` | Backend API URL for Telegram bot | `http://app:8000` |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare for image gen | (optional) |
| `EMAIL_HOST` | SMTP host for notifications | (optional) |
| `INTERNAL_API_KEY` | Inter-service auth key | (optional) |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true` |
| `EVAL_ENABLED` | Enable async evaluation | `true` |

## API Endpoints

### Core

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (Ollama + DB status) |
| GET | `/health/modules` | Per-module health (guardrails, eval) |
| GET | `/liveness` | Process liveness check |
| GET | `/readiness` | External dependency readiness (DB, Redis, Ollama) |
| GET | `/metrics` | Prometheus-format metrics |
| GET | `/ping` | Ping |
| POST | `/echo` | Echo (debug) |

### Chat & Graph

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Biology Q&A with RAG (legacy) |
| POST | `/graph/chat` | Unified LangGraph pipeline (intent → planner/retrieve → tutor → safety) |
| GET | `/graph/status` | Graph structure (nodes + edges) |
| GET | `/graph/traces` | List recent pipeline traces |
| GET | `/graph/traces/{trace_id}` | Get specific trace details |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create user account |
| POST | `/auth/token` | Login (email/password) |
| POST | `/auth/refresh` | Token rotation (refresh cookie) |
| POST | `/auth/logout` | Logout (revoke refresh token) |
| GET | `/auth/me` | Current user info |
| POST | `/auth/request-otp` | Request OTP for dashboard login (via Telegram) |
| POST | `/auth/verify-otp` | Verify OTP, issue JWT |
| GET | `/auth/oauth/{provider}/login` | Google OAuth start (Auth Code + PKCE, state in Redis) |
| GET | `/auth/oauth/{provider}/callback` | OAuth callback → validates id_token (JWKS), links/creates user |
| POST | `/auth/oauth/claim` | Exchange one-time ticket for session cookies |
| GET | `/auth/public-stats` | Aggregated public stats |

### Internal

| Method | Path | Description |
|--------|------|-------------|
| GET | `/internal/health` | Internal health (API key required) |

### Quiz

| Method | Path | Description |
|--------|------|-------------|
| POST | `/quiz/generate` | Generate RAG-grounded quiz |
| POST | `/quiz/submit` | Submit quiz answers, record attempts, update ability |
| GET | `/quiz/recommend/{user_id}` | Recommend quiz parameters |

### Lesson Plans

| Method | Path | Description |
|--------|------|-------------|
| POST | `/lesson-plan/generate` | Create lesson plan |

### Progress

| Method | Path | Description |
|--------|------|-------------|
| GET | `/progress/student/{student_id}` | Get student progress |
| POST | `/progress/student/{student_id}` | Record progress entry |
| POST | `/progress/parent-summary` | Generate parent summary |
| GET | `/progress/trends` | Progress trends |

### Admin

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/dashboard` | Dashboard overview |
| GET | `/admin/content/review` | Review content (use `type=quiz\|lesson`) |
| GET | `/admin/monitoring` | System monitoring |
| GET | `/admin/content/quiz/{item_id}` | Quiz detail |
| GET | `/admin/content/lesson/{item_id}` | Lesson detail |
| PATCH | `/admin/content/{type}/{id}/status` | Approve/reject content |

### Models

| Method | Path | Description |
|--------|------|-------------|
| GET | `/models` | List available models across all providers |
| GET | `/models/providers` | Provider health and info |
| GET | `/models/active` | Get currently active model |
| POST | `/models/active` | Set active model |
| GET | `/models/health` | Health check for all providers |
| POST | `/models/refresh` | Force refresh Ollama model cache |

### Diagram

| Method | Path | Description |
|--------|------|-------------|
| POST | `/diagram/generate` | Generate diagram analysis |
| POST | `/diagram/validate` | Validate diagram labels |
| GET | `/diagram/textbook` | List textbook diagrams |

### Export

| Method | Path | Description |
|--------|------|-------------|
| GET | `/export/quiz/{quiz_id}` | Download quiz as DOCX/PDF |
| GET | `/export/lesson-plan/{lesson_id}` | Download lesson plan as DOCX/PDF |

### Gamification

| Method | Path | Description |
|--------|------|-------------|
| POST | `/gamification/xp` | Award XP (internal) |
| GET | `/gamification/profile/{user_id}` | XP, level, streak, mastery, achievements |
| POST | `/gamification/activity` | Log activity + update streak |
| GET | `/gamification/events/{user_id}` | List XP events |
| GET | `/gamification/achievements/{user_id}` | Achievement definitions + progress |

### Recovery

| Method | Path | Description |
|--------|------|-------------|
| POST | `/recovery/plan` | Create recovery plan |
| GET | `/recovery/plan/{user_id}` | List recovery plans |
| POST | `/recovery/task/complete` | Complete task (XP + milestone check) |
| POST | `/recovery/auto-generate/{user_id}` | Auto-generate plan from weak topics |
| GET | `/recovery/weak-topics/{user_id}` | Get weak topics with severity |
| GET | `/recovery/history/{user_id}/{topic}` | Mastery history |
| GET | `/recovery/dashboard/{user_id}` | Combined view |
| GET | `/recovery/schedule/{user_id}` | Spaced repetition schedule |
| GET | `/recovery/schedule/due/{user_id}` | Due reviews |
| POST | `/recovery/schedule/generate/{user_id}` | Generate review schedule |
| POST | `/recovery/schedule/review` | Record review result |
| GET | `/recovery/notifications/{user_id}` | List notifications |
| PATCH | `/recovery/notifications/{notification_id}/read` | Mark read |
| PUT | `/recovery/notifications/read-all/{user_id}` | Mark all read |

### Notifications

| Method | Path | Description |
|--------|------|-------------|
| GET | `/notifications/preferences/{user_id}` | Get email preferences |
| PUT | `/notifications/preferences/{user_id}` | Update email preferences |
| POST | `/notifications/preferences/{user_id}/verify` | Send verification code |
| POST | `/notifications/preferences/{user_id}/verify/{code}` | Confirm verification code |

### Activity

| Method | Path | Description |
|--------|------|-------------|
| GET | `/activity/{user_id}` | Get recent activity feed |

### User Management

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users/{user_id}` | Get user info |
| PUT | `/users/{user_id}` | Update user |
| POST | `/users/lookup` | Find user by email or telegram_id |

### Student (Teacher operations)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/students` | List students (teacher) |
| GET | `/students/{student_id}` | Get student profile |
| GET | `/students/{student_id}/progress` | Student progress |
| POST | `/students/bulk-assign` | Bulk assign to teacher |

### Teacher

| Method | Path | Description |
|--------|------|-------------|
| GET | `/teacher/profile` | Get teacher profile |
| POST | `/teacher/students` | Teacher-student operations |

### Parent

| Method | Path | Description |
|--------|------|-------------|
| GET | `/parent/children` | List linked children |
| GET | `/parent/children/{child_id}/progress` | Child progress |
| POST | `/parent/link` | Link child by code |

### Workspace / Collection / Assignment / Bookmark

| Method | Path | Description |
|--------|------|-------------|
| * | `/workspace/*` | Workspace management |
| * | `/collection/*` | Content collections |
| * | `/assignment/*` | Assignments |
| * | `/bookmark/*` | Bookmarks |

### Knowledge Platform

| Method | Path | Description |
|--------|------|-------------|
| POST | `/knowledge/upload` | Upload document |
| GET | `/knowledge/items` | List knowledge items |
| GET | `/knowledge/{item_id}` | Get item details |

### Webhook

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhook` | Telegram bot webhook endpoint |

### Telemetry

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tracing/traces` | List traces |
| GET | `/tracing/traces/{trace_id}` | Get trace |
| GET | `/ekg/*` | Educational knowledge graph |
| GET | `/digital-twin/*` | Digital twin operations |

## Agentic RAG Pipeline

### Features

- **Hybrid Routing** — Simple queries use direct retrieval, complex queries use agentic pipeline
- **Query Rewriting** — LLM-based query expansion and decomposition
- **Multi-Index Search** — Parallel retrieval from curriculum, evidence, and cross-session indices
- **Iterative Retrieval** — Re-plan and re-retrieve when evidence is insufficient
- **Claim Verification** — Verify factual claims against evidence for accuracy
- **Performance Monitoring** — Trace ID generation and node-level timing

### Routing Logic

| Query Complexity | Pipeline | Nodes |
|------------------|----------|-------|
| Simple (fact lookup) | Direct | orchestrator → retrieve → tutor → hallucination → claim_verifier → safety |
| Complex (multi-hop) | Agentic | orchestrator → planner → plan_executor → evidence_graph → sufficient_context → synthesis → tutor → hallucination → claim_verifier → safety |

### Monitoring

```bash
# List recent traces
curl http://localhost:8000/graph/traces

# Get specific trace
curl http://localhost:8000/graph/traces/trace_abc123
```

## Telegram Bot

The bot runs in **webhook mode** (production) or **polling mode** (development). It's deployed as a unified Railway service with the API (webhook mode).

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
| `/diagram` | Start diagram conversation |
| `/dashboard_login` | Generate OTP for dashboard login |
| `/parent_register <email>` | Link parent account |
| `/children` | List linked children (parent) |
| `/child_progress` | Show child's progress (parent) |
| `/link <email>` | Link teacher dashboard account |
| `/assignments` | List assignments |
| `/submit <id> <answer>` | Submit assignment answer |

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

### Troubleshooting

**Bot doesn't respond:**
1. Kill other instances: `pkill -f telegram.bot`
2. Clear stale connections:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/deleteWebhook?drop_pending_updates=true"
   curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates?offset=999999999"
   ```
3. Check for Conflict errors in the bot log

**Long messages cropped:** The bot automatically splits responses >4096 chars via `_reply_long()`.

## Authentication

The project uses cookie-based JWT authentication:

- **Access token** — Short-lived (15 min), stored in `access_token` cookie (path=/)
- **Refresh token** — Long-lived (7 days), stored in `refresh_token` cookie (path=/auth/refresh)
- **Refresh rotation** — Each refresh invalidates the old token and issues new pair
- **Redis JTI revocation** — Token reuse detection via Redis `refresh:{jti}` key
- **OTP flow** — Telegram → `/dashboard_login` generates OTP → `/auth/verify-otp` issues JWT
- **Internal API key** — `X-API-Key` header for service-to-service auth

### Google OAuth (login & linking)

- Flow: dashboard → `/auth/oauth/google/login?redirect=/classroom` (307 to Google, PKCE S256, state single-use in Redis) → callback validates `id_token` against cached Google JWKS, resolves or creates the user, and returns a one-time `ticket` to the dashboard → `/auth/oauth/claim` swaps the ticket for the standard cookie pair.
- **Login** — new users are created from verified profile; an existing email (password/Telegram account) reveals via `?oauth_error=email_conflict` — no auto-merge.
- **Linking** — start with `?link=1` while logged in (`oauth_accounts` row is added to the current user and authenticated immediately). Doing it anonymously returns `?oauth_error=login_required`.
- `oauth_accounts` table: unique `(provider, provider_user_id)` and `(user_id, provider)`, so a Google account can only ever bind to one EthioBio user.
- Requires `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET`, `OAUTH_CALLBACK_BASE_URL` (defaults to `DASHBOARD_URL`); errors surface as `not_configured` when unset.

## Testing

```bash
# Run unit tests (skip slow endpoint tests)
pytest tests/ -v -k "not slow"

# Full test suite with coverage
pytest tests/ -v -m "not slow" --cov=src --cov-report=term

# Lint + typecheck
ruff check . && mypy src/

# Pre-commit hooks
pre-commit run --all-files
```

## Observability Stack

The project ships with a full observability stack in `docker-compose.yml`:

| Service | Port | Credentials |
|---------|------|-------------|
| Jaeger (traces) | `:16686` | — |
| Prometheus (metrics) | `:9090` | — |
| Grafana (dashboards) | `:3001` | `admin` / `ethiobio` |

- **Traces**: OTel spans exported via OTLP gRPC (`:4317`) to Jaeger. GenAI semantic conventions.
- **Metrics**: Prometheus-format at `/metrics`. Scraped by Prometheus on 15s interval.
- **Dashboards**: Pre-built Grafana dashboard auto-provisioned in `grafana/dashboards/`.
- **Sentry**: Optional error tracking with Sentry SDK (free tier).
- **Health checks**: Per-module health registry at `/health/modules`, readiness endpoint at `/readiness`.

## Rate Limiting

Six-tier Redis-backed rate limiting (configurable, disabled during tests):

| Tier | Window | Max | Routes |
|------|--------|-----|--------|
| `auth` | 60s | 5 | `/auth/*` (except OTP) |
| `otp` | 300s | 3 | `/auth/request-otp`, `/auth/verify-otp` |
| `chat` | 60s | 20 | `/chat/*` |
| `write` | 60s | 30 | POST/PUT/PATCH/DELETE |
| `read` | 60s | 100 | Everything else |
| `internal` | 60s | 500 | `/internal/*` |

Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## Deployment

### Backend (Railway)

The API + Telegram bot run as a unified Railway service:

```bash
railway up                    # deploy from local directory
railway redeploy --yes        # redeploy last image
railway deployment list       # check status
```

Push to `main` triggers auto-deploy (when GitHub connected).

### Frontend (Vercel)

```bash
cd dashboard
npm run build
vercel deploy --prod
```

## Project Metrics

| Metric | Value |
|--------|-------|
| Python source files | ~150 |
| Total Python lines | ~75,000 |
| Database models | 31+ |
| LLM Providers | 5 (Ollama, OpenRouter, OpenAI, Anthropic, OpenAI-compatible) |
| Agents | 15+ (Tutor, Quiz, LessonPlanner, Safety, Translator, StudentProgress, etc.) |
| LangGraph nodes | 12+ (orchestrator, planner, plan_executor, evidence_graph, sufficient_context, synthesis, retrieve, skip_retrieval, tutor, hallucination, claim_verifier, safety) |
| API endpoints | 70+ |
| Test files | 90+ |
| Dashboard pages | 9 |
| Textbooks ingested | 4 (Grades 9-12) |
| Vector store backend | pgvector (ChromaDB removed) |
| Retrieval methods | Hybrid (Dense + BM25 + Cross-encoder reranker) |
| CI/CD | GitHub Actions (lint + typecheck + tests + security) |
| Auth | Cookie-based JWT with refresh rotation + Redis JTI |
| Rate limiting | 6-tier Redis-backed |
| Circuit breaker | Per-provider (threshold=5, recovery_timeout=30s) |
