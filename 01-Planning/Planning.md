# EthioBio AI Assistant - Planning

## Objectives
Build an AI-powered biology learning and teaching assistant for Ethiopian middle and high school education. Helps teachers save time, helps students learn more effectively, and supports parents and school administrators with simple, useful updates.

## Scope
### In Scope (v1.2)
- Telegram bot (interactive quiz flow, conversation handlers, inline keyboards)
- English-first biology Q&A with source citations
- Amharic support for explanations and summaries
- Hybrid RAG retrieval (Dense + BM25 + Cross-encoder reranker)
- Quiz generation (5 types: MC, T/F, short answer, matching, diagram-labeling)
- Lesson planning
- Student progress tracking with trend detection
- Parent summaries (bilingual)
- Teacher review dashboard (Next.js, 9 pages)
- Ollama-first model routing (`gemma4:31b-cloud`)
- Fallback AI provider support (OpenAI/Anthropic)
- LangGraph orchestration (5 nodes)
- Docling+OCR PDF extraction for garbled textbooks
- Explicit source citations `(Grade X, Unit Y: Title, p. Z)`
- Logging, monitoring, and evaluation

### Out of Scope (v1.2)
- Full mobile app
- Video learning platform
- Custom foundation model training
- Real-time classroom proctoring
- Non-biology subjects
- Full offline classroom package
- Voice support (stubbed, planned for v1.3)
- WhatsApp integration (planned for v1.3)

## Approach
### Product Principles
- **Curriculum first**: answers must match Ethiopian biology content.
- **English first**: curriculum content is mainly English.
- **AI is assistive, not authoritative**: teachers control final output.
- **Low-resource friendly**: text-first, mobile-first, lightweight.
- **Modular by design**: agents and tools must be replaceable.
- **Fallback ready**: local models are primary; external providers are backup.
- **Safe and explainable**: the system should be understandable and auditable.
- **Cited sources**: every answer cites its textbook source with grade, unit, topic, and page.

### AI Architecture
- **Primary**: Ollama-hosted models (`gemma4:31b-cloud`)
- **Fallback**: OpenAI (`gpt-4o-mini`) or Anthropic (`claude-3-haiku`) when confidence < 0.5 or Ollama unavailable
- **Model Router**: confidence-based routing with DB logging to `ModelRoutingLog`
- **Orchestration**: LangGraph StateGraph with 5 nodes and dependency injection

### Agent System
- Orchestrator Agent (intent classification)
- Curriculum Retrieval Agent (hybrid: dense + BM25 + reranker)
- Tutor Agent (RAG-grounded with citations)
- Quiz Agent (5 question types, context-grounded)
- Lesson Planner Agent
- Translation Agent (English-Amharic)
- Student Progress Agent (trend detection, weak areas)
- Parent Summary Agent (bilingual reports)
- Safety Agent (self-check loop, bidirectional revision)
- Evaluation Agent (Ragas + heuristic fallback)

### Retrieval Pipeline
```
query → embed → dense search (ChromaDB) + sparse search (BM25) → merge (0.6/0.4) → rerank (cross-encoder) → top-k → format context
```
- Configurable weights: 0.6 dense / 0.4 BM25
- `VectorStoreAdapter` interface — swappable without touching agents
- Filtering: grade_level, topic, unit, source_type

### Document Processing
- PyPdfium2 for fast PDF text extraction
- RapidOCR fallback for garbled pages (font encoding issues)
- Auto-detection: alpha character ratio < 40% triggers OCR
- Grade 10 requires full OCR (176/182 pages garbled)
- Docling HybridChunker for token-aware RAG chunking
- Per-page chunking to preserve accurate page numbers

### LangGraph Pipeline
```
entry → orchestrator → needs_retrieval? → retrieve ─┐
                  │                       skip_retr. ┤
                  └──────────────────────────────────→ tutor → safety → END / revise→tutor
```

## Risks & Mitigation
| Risk | Impact | Mitigation |
|------|--------|------------|
| Hallucinated answers | High | Hybrid RAG, safety checks, fallback, teacher review, explicit citations |
| Weak Amharic output | Medium | Use Amharic selectively, keep English primary |
| Local model performance issues | High | Model routing and fallback providers |
| Poor curriculum alignment | High | Curated content store, human review, hybrid retrieval, grade/topic filtering |
| Low internet access | Medium | Text-first design and cached responses |
| Garbled PDF text | High | PyPdfium2 + RapidOCR with auto-detection (alpha ratio < 40%) |
| Font encoding issues (Grade 10) | High | Full OCR extraction for affected textbooks |

## Resources Needed
### Backend
- Python 3.12+, FastAPI, uvicorn

### Data Storage
- PostgreSQL 16 + pgvector, Redis 7, ChromaDB + BM25

### AI Runtime
- Ollama (`gemma4:31b-cloud`, `tinyllama`, `nomic-embed-text`)
- OpenAI/Anthropic adapters for fallback

### Retrieval Layer
- ChromaDB (dense) + BM25Okapi (sparse) + cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`)

### Document Processing
- PyPdfium2, RapidOCR, Docling HybridChunker

### Channels
- Telegram (v1.2), WhatsApp (planned for v1.3)

### Admin UI
- Next.js 14 App Router, Tailwind CSS 3.4, recharts, lucide-react

### Infrastructure
- Dockerized services (6 containers), migration scripts, environment templates, health checks, backups

### Testing & Quality
- pytest (7 test files), ruff linting, mypy type checking, Ragas evaluation
