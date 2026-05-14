# EthioBio AI Assistant

AI-powered biology learning and teaching assistant for Ethiopian middle and high school education (Grades 7-12). Uses LangGraph orchestration, RAG with ChromaDB, and gemma4:31b-cloud via Ollama.

## Features

- **Biology Q&A** — Ask biology questions, get curriculum-aligned answers from Grade 12 textbook
- **Interactive Quiz** — Tap-to-answer quizzes with inline buttons, instant feedback, and score tracking
- **RAG-Grounded Generation** — Quiz questions strictly based on Ethiopian textbook content, not general LLM knowledge
- **Lesson Planning** — Create structured lesson plans with objectives, activities, and assessments
- **Student Progress Tracking** — Monitor performance, identify weak areas
- **Parent Summaries** — Weekly progress reports in English and Amharic
- **Amharic Support** — Bilingual explanations and translations
- **LangGraph Orchestration** — Intent classification → RAG retrieval → gemma4 generation → safety check
- **Telegram Bot** — Primary user interface with interactive menus, commands, and inline keyboards
- **Teacher Dashboard** — Next.js web dashboard for content review, approval workflow, monitoring
- **Gemma4-First** — Cloud-hosted 31B parameter model with TinyLlama fallback

## Architecture

```
src/
├── main.py                # FastAPI server entry point
├── config.py              # Pydantic Settings (env-based)
├── database/
│   ├── models.py          # 15 SQLAlchemy entities
│   └── session.py         # Async session with lazy engine
├── llm/
│   ├── ollama_client.py   # Ollama API wrapper (chat, embeddings, health)
│   ├── fallback.py        # OpenAI/Anthropic fallback adapter
│   └── router.py          # Confidence-based model routing
├── rag/
│   ├── embedder.py        # Embedding via Ollama or sentence-transformers
│   ├── vector_store.py    # ChromaDB operations
│   └── retriever.py       # Curriculum search with grade filtering
├── retrieval/
│   ├── adapter.py         # VectorStoreAdapter — ChromaDB abstraction
│   └── __init__.py
├── agents/
│   ├── base.py            # Base agent with _call_llm
│   ├── orchestrator.py    # Intent classification
│   ├── tutor.py           # Biology Q&A
│   ├── quiz.py            # RAG-grounded quiz generation
│   ├── lesson_planner.py  # Lesson plan generation
│   ├── translator.py      # English-Amharic translation
│   ├── safety.py          # Content review
│   ├── student_progress.py# Performance analytics
│   └── parent_summary.py  # Weekly report generation
├── graph/                 # LangGraph orchestration
│   ├── state.py           # AgentState, GraphOutput
│   ├── orchestrator.py    # Compiled graph with 5 nodes
│   └── nodes/
│       ├── orchestrator.py # Intent classifier
│       ├── retrieval.py    # RAG context fetch
│       ├── tutor.py        # Answer generation
│       └── safety.py       # Self-check + revision
├── schemas/               # Pydantic models for all structured outputs
├── api/
│   ├── chat.py            # POST /chat
│   ├── quiz.py            # POST /quiz/generate, /quiz/submit
│   ├── lesson.py          # POST /lesson-plan/generate
│   ├── progress.py        # Progress + parent summary endpoints
│   ├── admin.py           # Dashboard, content review, monitoring, approve/reject
│   └── graph.py           # POST /graph/chat, GET /graph/status
├── telegram/
│   ├── bot.py             # PTB Application with ConversationHandlers (interactive quiz)
│   └── keyboards.py       # Inline keyboard layouts (icons, submenus)
├── evaluation/
│   └── ragas_test.py      # Ragas evaluation metrics + gold dataset
└── observability/
    └── tracing.py         # LangSmith tracing (optional)
dashboard/                 # Next.js teacher dashboard (sidebar, 6 pages)
scripts/
├── ingest_curriculum.py   # PDF/DOCX → ChromaDB ingestion with smart chunking
tests/                     # pytest suite (23+ tests)
data/
├── textbooks/             # Place curriculum PDFs here
│   ├── Grade7/ ... Grade12/
├── evaluation/
│   └── gold_set.json      # Ragas gold QA dataset
└── vectors/               # ChromaDB persist directory
```

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

# Create database tables
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
├── Grade7/
├── Grade8/
├── Grade9/
├── Grade10/
├── Grade11/
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

## Environment Variables

Key environment variables (see `.env.example` for full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | (required) |
| `OLLAMA_CHAT_MODEL` | Primary LLM model | `gemma4:31b-cloud` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_EMBED_MODEL` | Embedding model | `nomic-embed-text` |
| `DATABASE_URL` | PostgreSQL async connection | `postgresql+asyncpg://...` |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (Ollama + DB status) |
| POST | `/chat` | Biology Q&A with RAG |
| POST | `/graph/chat` | LangGraph pipeline (intent → RAG → tutor → safety) |
| GET | `/graph/status` | Graph structure (nodes + edges) |
| POST | `/quiz/generate` | Generate RAG-grounded quiz |
| POST | `/quiz/submit` | Submit quiz answers |
| POST | `/lesson-plan/generate` | Create lesson plan |
| POST | `/progress/student/{id}` | Get student progress |
| POST | `/progress/parent-summary` | Generate parent summary |
| GET | `/admin/dashboard` | Dashboard overview |
| GET | `/admin/content/review` | Review content (use `type=quiz\|lesson`) |
| GET | `/admin/content/quiz/{id}` | Quiz detail with all questions |
| GET | `/admin/content/lesson/{id}` | Lesson detail with full content |
| PATCH | `/admin/content/{type}/{id}/status` | Approve/reject content |
| GET | `/admin/monitoring` | System monitoring |

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
| `/ask <question>` | Ask a biology question directly |
| `/quiz [grade] [topic]` | Start interactive quiz |
| `/grade <7-12>` | Set default grade level |
| `/language <en\|am\|both>` | Set language |
| `/cancel` | Cancel current operation |

### Menu Layout

```
Main Menu
├── 🧬 Ask a Question    → text input → LLM answer
├── 📝 Take a Quiz       → type → grade → topic → interactive quiz
├── 📊 My Progress       → stats (requires PostgreSQL)
├── 🌐 Language          → en / am / both
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

## Testing

```bash
# Run unit tests
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
```

## Bug Fixes Applied

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
