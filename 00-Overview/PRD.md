---
title: EthioBio AI Assistant
---
# EthioBio AI Assistant

## Product Requirements Document (PRD) v1.2

## 1. Overview

EthioBio AI Assistant is an AI-powered biology learning and teaching assistant for Ethiopian middle and high school education. It is designed to help biology teachers save time, help students learn more effectively, and support parents and school administrators with simple, useful updates.

The product is **English-first** because the Ethiopian middle and high school biology curriculum is mainly in English, but it also supports **Amharic** for explanations, parent communication, and accessibility.

The system will be **Telegram-first**, with WhatsApp support added later. The AI layer will use **Ollama-hosted local/open models as the primary engine**, with fallback to other providers when needed for quality, speed, or availability.

All RAG-grounded responses include **explicit source citations** in the format `(Grade X, Unit Y: Title, p. Z)` to ensure curriculum alignment and reduce hallucinations.

---

## 2. Product goals

1. Reduce biology teacher workload.
    
2. Improve student understanding and practice.
    
3. Support curriculum-aligned biology learning.
    
4. Work in low-bandwidth and mixed-resource environments.
    
5. Use local/open models first to reduce cost and improve control.
    
6. Provide fallback AI providers for reliability.
    
7. Offer a modular AI-agent architecture that can grow over time.

8. Ensure all answers cite their textbook sources for transparency and trust.

---

## 3. Target users

### Primary users

- Biology teachers
    
- Middle school students
    
- High school students
    

### Secondary users

- Parents
    
- School administrators
    
- Tutors and exam-prep centers
    

---

## 4. Problem statement

Teachers spend too much time:

- preparing lesson plans
    
- writing quizzes and exams
    
- explaining the same concepts repeatedly
    
- tracking student progress
    
- communicating with parents
    

Students struggle with:

- difficult biology terminology
    
- limited individual support
    
- lack of practice questions
    
- low access to lab resources
    
- inconsistent study habits
    

Schools need a tool that is:

- affordable
    
- easy to use
    
- curriculum aligned
    
- mobile-friendly
    
- suitable for low-resource settings
    

---

## 5. Product scope

### In scope for v1

- Telegram bot
    
- English-first biology Q&A
    
- Amharic support for explanations and summaries
    
- Curriculum-aligned retrieval (hybrid: dense + BM25 + reranker)
    
- Quiz generation (MC, T/F, short answer, matching, diagram-labeling)
    
- Lesson planning
    
- Student progress tracking
    
- Parent summaries
    
- Teacher review dashboard (Next.js, 9 pages)
    
- Ollama-first model routing
    
- Fallback AI provider support (OpenAI/Anthropic)
    
- Logging, monitoring, and evaluation
    
- Docling+OCR PDF extraction for garbled textbooks
    
- Explicit source citations in all RAG responses
    

### Out of scope for v1

- Full mobile app
    
- Video learning platform
    
- Custom foundation model training
    
- Real-time classroom proctoring
    
- Non-biology subjects
    
- Full offline classroom package
    

---

## 6. Product principles

- **Curriculum first**: answers must match Ethiopian biology content.
    
- **English first**: curriculum content is mainly English.
    
- **AI is assistive, not authoritative**: teachers control final output.
    
- **Low-resource friendly**: text-first, mobile-first, lightweight.
    
- **Modular by design**: agents and tools must be replaceable.
    
- **Fallback ready**: local models are primary; external providers are backup.
    
- **Safe and explainable**: the system should be understandable and auditable.

- **Cited sources**: every answer must cite its textbook source with grade, unit, topic, and page number.

---

## 7. Core user stories

### Student stories

- As a student, I want to ask a biology question and get a clear answer.
    
- As a student, I want quizzes to help me practice for exams.
    
- As a student, I want explanations in simple English and sometimes Amharic.
    
- As a student, I want to send a voice note when typing is hard.

- As a student, I want to see which textbook page a concept comes from.
    

### Teacher stories

- As a teacher, I want lesson plans generated from a topic and grade.
    
- As a teacher, I want quizzes and exams generated quickly.
    
- As a teacher, I want to review and edit AI-generated content.
    
- As a teacher, I want to see which topics students struggle with.

- As a teacher, I want to verify that AI answers cite the correct textbook sources.
    

### Parent stories

- As a parent, I want to receive simple weekly progress updates.
    
- As a parent, I want messages in English or Amharic.
    

### Admin stories

- As an admin, I want to manage school content and usage.
    
- As an admin, I want to monitor AI quality, failures, and usage patterns.
    

---

## 8. Functional requirements

### 8.1 Chat tutor

The assistant must:

- answer biology questions
    
- adapt to student level
    
- explain concepts simply
    
- support English first, Amharic on request
    
- use curriculum context when available

- cite sources in `(Grade X, Unit Y: Title, p. Z)` format

### 8.2 Quiz generation

The assistant must generate:

- multiple choice questions
    
- true/false questions
    
- short answer questions
    
- matching questions
    
- diagram-labeling prompts
    
- answer keys
    
- short explanations

- questions grounded in retrieved textbook content, not general LLM knowledge

### 8.3 Lesson planning

The assistant must generate:

- lesson objective
    
- prior knowledge activation
    
- explanation
    
- activities
    
- assessment
    
- homework
    
- teacher notes
    

### 8.4 Student progress tracking

The system must:

- track attempts and scores
    
- map performance to biology topics
    
- identify weak areas (<60% score threshold)
    
- recommend revision

- detect trends (improving/declining/stable)

### 8.5 Parent summaries

The system must:

- generate weekly progress updates
    
- warn about low performance when needed
    
- support English and Amharic
    

### 8.6 Voice support

The system should:

- accept voice notes
    
- convert speech to text
    
- reply with text in v1
    
- optionally support voice replies later
    

### 8.7 Teacher dashboard

The dashboard must allow:

- content review
    
- quiz editing
    
- lesson plan editing
    
- student performance viewing
    
- export to PDF/DOCX

- monitoring metrics (fallback rate, failure rate, latency)

### 8.8 Source citations

The system must:

- extract page-level metadata during PDF ingestion
    
- preserve grade, unit, topic, and page number for each chunk
    
- include citations in all RAG-grounded responses
    
- format citations as `(Grade X, Unit Y: Title, p. Z)`

---

## 9. AI architecture

## 9.1 Model strategy

The system must use:

### Primary

- Ollama-hosted open models for most requests (`gemma4:31b-cloud`)
    

### Fallback

- external providers (OpenAI `gpt-4o-mini`, Anthropic `claude-3-haiku`) when:
    
    - local model confidence is low (< 0.5)
        
    - request is too complex
        
    - response quality is not sufficient
        
    - local service is unavailable
        
    - voice/transcription needs a stronger model
        

### Routing logic

A model router should decide:

- which model to use
    
- whether to use retrieval
    
- whether to call a tool
    
- whether to ask a clarification question
    
- whether to fallback

- log all routing decisions to `ModelRoutingLog` DB table

---

## 10. AI agent system

The product uses multiple specialized agents orchestrated via LangGraph.

### 10.1 Orchestrator Agent

Routes user requests to the right agent. Intent classification: tutor/quiz/lesson_plan/progress/translation/admin/general.

### 10.2 Curriculum Retrieval Agent

Searches approved biology sources before answering. Uses hybrid retrieval: dense (ChromaDB) + sparse (BM25) + cross-encoder reranker.

### 10.3 Tutor Agent

Explains biology concepts in a student-friendly way. Grounded in retrieved textbook content with explicit source citations.

### 10.4 Quiz Agent

Generates assessments, answer keys, and explanations. Retrieves 5 ChromaDB chunks and generates questions strictly from context.

### 10.5 Lesson Planner Agent

Creates structured lesson plans for teachers.

### 10.6 Translation Agent

Supports English-first content with Amharic translation or bilingual summaries.

### 10.7 Student Progress Agent

Tracks learner performance and topic mastery. Detects trends (improving/declining/stable) and identifies weak areas.

### 10.8 Parent Summary Agent

Creates short and readable progress reports in English and Amharic.

### 10.9 Safety Agent

Blocks unsafe, irrelevant, or low-quality outputs. Routes: "reject" (score < 0.4), "revise" (score < 0.7), "finalize" (pass). Bidirectional revision loop back to Tutor Agent.

### 10.10 Evaluation Agent

Checks curriculum alignment, grade appropriateness, and answer quality. Uses Ragas metrics (faithfulness, answer relevancy, context recall, context precision) with heuristic fallback.

---

## 11. Advanced technical capabilities for AI agents

### 11.1 Tool use

Agents should be able to call tools such as:

- curriculum search
    
- quiz builder
    
- lesson plan exporter
    
- OCR
    
- speech-to-text
    
- PDF/DOCX export
    
- analytics functions
    

### 11.2 Retrieval-Augmented Generation (RAG)

The assistant must:

- retrieve relevant curriculum passages using hybrid search (dense + BM25 + rerank)
    
- ground answers in approved sources
    
- attach source references in `(Grade X, Unit Y: Title, p. Z)` format
    
- reduce hallucinations

- support grade/topic/unit/source_type filtering

### 11.3 Structured outputs

Generated content should use strict schemas, especially for:

- quizzes
    
- lesson plans
    
- parent summaries
    
- progress reports
    

### 11.4 Multi-step reasoning

The agent should:

1. interpret the request
    
2. retrieve relevant content
    
3. draft a response
    
4. critique the draft (Safety Agent)
    
5. revise if needed
    
6. produce the final output
    

### 11.5 Confidence scoring

The system should estimate confidence and choose whether to:

- answer directly
    
- ask for clarification
    
- fallback to another model
    
- route to teacher review
    

### 11.6 Memory

Use:

- short-term conversation memory
    
- long-term learner memory
    
- teacher preference memory
    

### 11.7 Self-check loop

The assistant should verify:

- factual correctness
    
- grade appropriateness
    
- curriculum match
    
- clarity
    
- language quality
    

### 11.8 Observability

Track:

- prompt version
    
- model used
    
- retrieval hits
    
- fallback rate
    
- latency
    
- user feedback
    
- failures

- LangSmith tracing (optional, via `LANGCHAIN_API_KEY`)

---

## 12. Technical architecture

### 12.1 Backend

- Python 3.12+
    
- FastAPI
    
- uvicorn
    

### 12.2 Data storage

- PostgreSQL 16 with pgvector for persistent application data
    
- Redis 7 for caching and background jobs
    
- ChromaDB for vector store (with BM25 sparse index)
    

### 12.3 AI runtime

- Ollama for primary local/cloud model hosting (`gemma4:31b-cloud`)
    
- OpenAI/Anthropic adapters for fallback APIs
    

### 12.4 Retrieval layer

- ChromaDB (dense) + BM25Okapi (sparse) + cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`)
    
- Configurable weights: 0.6 dense / 0.4 BM25
    
- `VectorStoreAdapter` interface — swappable without touching agents
    

### 12.5 Channels

- Telegram first (python-telegram-bot v21, async native)
    
- WhatsApp later
    

### 12.6 Document processing

- PyPdfium2 for fast PDF text extraction
    
- RapidOCR for garbled pages (font encoding issues)
    
- Auto-detection of garbled text (alpha character ratio < 40%)
    
- Docling HybridChunker for token-aware RAG chunking
    
- Per-page chunking to preserve accurate page numbers
    
- DOCX parser support
    

### 12.7 Voice processing

- speech-to-text (stubbed)
    
- optional text-to-speech later
    

### 12.8 Admin UI

- Next.js 14 App Router (9 pages: Dashboard, Quizzes, Lessons, Students, Monitoring, Ask Q&A)
    
- Tailwind CSS 3.4, recharts, lucide-react
    

### 12.9 Orchestration

- LangGraph StateGraph with 5 nodes: orchestrator → retrieve/skip → tutor → safety → revise/finalize
    
- Dependency-injected nodes (ModelRouter, VectorStoreAdapter)
    
- 20+ field AgentState dataclass
    

---

## 13. Data model

### Main entities

- User (telegram_id as BigInteger)
    
- StudentProfile
    
- TeacherProfile
    
- ClassGroup
    
- ClassEnrollment
    
- CurriculumTopic
    
- LessonPlan
    
- Question
    
- Quiz
    
- QuizAttempt
    
- ProgressRecord
    
- ParentSummary
    
- MessageThread
    
- ContentSource
    
- FeedbackEvent
    
- ModelRoutingLog
    

### Key fields

- role
    
- language preference
    
- grade level
    
- subject focus
    
- topic mastery
    
- score history
    
- source references
    
- created_at / updated_at
    
- model used
    
- confidence score

- UUID primary keys, asyncpg, JSON columns

---

## 14. API requirements

### Core endpoints

- `/chat`
    
- `/quiz/generate`
    
- `/quiz/submit`
    
- `/lesson-plan/generate`
    
- `/progress/student/{id}`
    
- `/progress/parent-summary`
    
- `/graph/chat`
    
- `/graph/status`
    
- `/admin/dashboard`
    
- `/admin/content/review`
    
- `/admin/monitoring`
    
- `/health`
    

### API expectations

- consistent JSON schemas
    
- validated inputs and outputs
    
- error messages suitable for debugging
    
- secure authentication for teacher/admin routes
    

---

## 15. Non-functional requirements

### Performance

- fast enough for classroom use
    
- graceful fallback under load
    
- cached retrieval for repeated queries
    

### Reliability

- retry logic
    
- safe failure modes
    
- clear error handling
    
- DB table auto-creation on startup
    

### Security

- secrets in environment variables or vault
    
- role-based access control
    
- no public exposure of sensitive student data
    

### Maintainability

- modular code
    
- test coverage (pytest, 7 test files)
    
- clear docs
    
- clean separation of concerns
    
- ruff linting (line-length=100, EFINW)
    
- mypy type checking (strict=false)
    

### Cost control

- use Ollama first
    
- fallback only when needed
    
- batch background tasks when possible
    

---

## 16. Testing and quality assurance

### Automated tests

- unit tests (57 Python files, ~4,788 lines)
    
- integration tests
    
- API tests
    
- retrieval tests
    
- language tests
    
- schema validation tests
    
- prompt regression tests

- Ragas evaluation with heuristic fallback

### Manual tests

- teacher workflow
    
- student workflow
    
- parent workflow
    
- low-bandwidth behavior
    
- voice input behavior
    
- fallback provider behavior

- garbled PDF extraction verification

### Acceptance criteria

The system is acceptable when:

- students get understandable biology help
    
- teachers can generate and edit quizzes and lesson plans
    
- curriculum retrieval reduces hallucinations
    
- Ollama is used by default
    
- fallback works when necessary
    
- performance data is stored correctly
    
- deployment is repeatable

- all RAG responses include explicit source citations

- Grade 10 textbooks with font encoding issues are handled via OCR

---

## 17. Deployment requirements

### Environments

- local development
    
- staging
    
- production
    

### Deployment steps

1. Build and test locally.
    
2. Deploy to staging.
    
3. Run smoke tests.
    
4. Validate sample biology queries.
    
5. Promote to production.
    
6. Monitor logs, errors, and usage.
    
7. Roll back if needed.
    

### Infrastructure

- Dockerized services (6 containers: app, bot, postgres, redis, ollama, dashboard)
    
- migration scripts
    
- environment templates
    
- health checks
    
- backups

- docker-compose.yml with service topology

---

## 18. Suggested MVP delivery phases

### Phase 1 ✅

Telegram bot, basic tutoring, Ollama integration, retrieval.

### Phase 2 ✅

Quiz generation, lesson planning, teacher review tools.

### Phase 3 ✅

Student progress tracking, parent summaries, analytics.

### Phase 4 🔄

Voice support (stubbed), OCR (integrated for garbled PDFs), WhatsApp integration (planned), exports (stubbed).

---

## 19. Risks and mitigations

### Risk: hallucinated answers

Mitigation: RAG (hybrid: dense + BM25 + rerank), safety checks, fallback, teacher review, explicit source citations.

### Risk: weak Amharic output

Mitigation: use Amharic selectively and keep English primary.

### Risk: local model performance issues

Mitigation: model routing and fallback providers (OpenAI/Anthropic).

### Risk: poor curriculum alignment

Mitigation: curated content store, human review, hybrid retrieval, grade/topic/unit filtering.

### Risk: low internet access

Mitigation: text-first design and cached responses.

### Risk: garbled PDF text from font encoding issues

Mitigation: PyPdfium2 + RapidOCR fallback with auto-detection (alpha ratio < 40%). Grade 10 requires full OCR.

---

## 20. Definition of done

The product is done for v1 when:

- a student can use Telegram to ask biology questions
    
- a teacher can generate and edit lesson plans and quizzes
    
- the system uses Ollama first and falls back when needed
    
- curriculum grounding is active (hybrid RAG)
    
- progress tracking works
    
- parent summaries work
    
- the app is tested, deployed, and maintainable

- all RAG responses include explicit source citations `(Grade X, Unit Y: Title, p. Z)`

- garbled textbook PDFs are handled via OCR extraction

- 4 textbooks ingested (Grades 9-12) with 1,165 chunks

---

## 21. Build instruction for coding agents

Use this as the implementation directive:

```text
Build EthioBio AI Assistant v1.2 as a production-ready Telegram-first biology learning platform for Ethiopian middle and high school education.

Requirements:
- English-first curriculum alignment
- Amharic support as secondary
- Ollama as the primary model runtime (gemma4:31b-cloud)
- Fallback providers (OpenAI/Anthropic) when local models are insufficient
- Hybrid RAG over approved biology curriculum content (Dense + BM25 + Cross-encoder reranker)
- Agent-based architecture with tool use, routing, memory, confidence scoring, and self-checking
- LangGraph orchestration (5 nodes: orchestrator → retrieve/skip → tutor → safety → revise/finalize)
- FastAPI backend
- PostgreSQL 16 + pgvector + Redis 7
- ChromaDB vector store with BM25 sparse index
- Teacher dashboard (Next.js 14, 9 pages)
- Student progress tracking with trend detection
- Parent summaries (bilingual)
- Quiz generation (5 types, RAG-grounded)
- Lesson planning
- Docling+OCR PDF extraction (PyPdfium2 + RapidOCR fallback)
- Explicit source citations (Grade X, Unit Y: Title, p. Z)
- Dockerized deployment (6 services)
- Full automated test coverage (pytest, 7 test files)

Implementation order:
1. scaffold repo
2. build Telegram bot
3. integrate Ollama
4. add fallback provider routing
5. implement hybrid retrieval pipeline (dense + BM25 + rerank)
6. implement tutor agent with citations
7. implement quiz agent
8. implement lesson planner
9. implement student tracking
10. implement teacher dashboard
11. add Docling+OCR PDF extraction
12. add tests and evaluation suite
13. add deployment scripts
14. document everything

Standards:
- no placeholder-only code
- no TODOs in final deliverable
- all endpoints tested
- all generated outputs schema-validated
- all secrets externalized
- readable logs (structlog)
- clean docs
- working deployment
- ruff linting (line-length=100, EFINW)
- mypy type checking (strict=false)
```

If you want, I can next turn this into a **developer-ready backlog** with **epics, user stories, acceptance criteria, and a week-by-week implementation plan**.
