---
title: EthioBio AI Assistant
---
# EthioBio AI Assistant

## Product Requirements Document (PRD) v1.1

## 1. Overview

EthioBio AI Assistant is an AI-powered biology learning and teaching assistant for Ethiopian middle and high school education. It is designed to help biology teachers save time, help students learn more effectively, and support parents and school administrators with simple, useful updates.

The product is **English-first** because the Ethiopian middle and high school biology curriculum is mainly in English, but it also supports **Amharic** for explanations, parent communication, and accessibility.

The system will be **Telegram-first**, with WhatsApp support added later. The AI layer will use **Ollama-hosted local/open models as the primary engine**, with fallback to other providers when needed for quality, speed, or availability.

---

## 2. Product goals

1. Reduce biology teacher workload.
    
2. Improve student understanding and practice.
    
3. Support curriculum-aligned biology learning.
    
4. Work in low-bandwidth and mixed-resource environments.
    
5. Use local/open models first to reduce cost and improve control.
    
6. Provide fallback AI providers for reliability.
    
7. Offer a modular AI-agent architecture that can grow over time.
    

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
    
- curriculum-aligned retrieval
    
- quiz generation
    
- lesson planning
    
- student progress tracking
    
- parent summaries
    
- teacher review dashboard
    
- Ollama-first model routing
    
- fallback AI provider support
    
- logging, monitoring, and evaluation
    

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
    

---

## 7. Core user stories

### Student stories

- As a student, I want to ask a biology question and get a clear answer.
    
- As a student, I want quizzes to help me practice for exams.
    
- As a student, I want explanations in simple English and sometimes Amharic.
    
- As a student, I want to send a voice note when typing is hard.
    

### Teacher stories

- As a teacher, I want lesson plans generated from a topic and grade.
    
- As a teacher, I want quizzes and exams generated quickly.
    
- As a teacher, I want to review and edit AI-generated content.
    
- As a teacher, I want to see which topics students struggle with.
    

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
    

### 8.2 Quiz generation

The assistant must generate:

- multiple choice questions
    
- true/false questions
    
- short answer questions
    
- matching questions
    
- diagram-labeling prompts
    
- answer keys
    
- short explanations
    

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
    
- identify weak areas
    
- recommend revision
    

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
    

---

## 9. AI architecture

## 9.1 Model strategy

The system must use:

### Primary

- Ollama-hosted open models for most requests
    

### Fallback

- external providers when:
    
    - local model confidence is low
        
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
    

---

## 10. AI agent system

The product should use multiple specialized agents.

### 10.1 Orchestrator Agent

Routes user requests to the right agent.

### 10.2 Curriculum Retrieval Agent

Searches approved biology sources before responding.

### 10.3 Tutor Agent

Explains biology concepts in a student-friendly way.

### 10.4 Quiz Agent

Generates assessments, answer keys, and explanations.

### 10.5 Lesson Planner Agent

Creates structured lesson plans for teachers.

### 10.6 Translation Agent

Supports English-first content with Amharic translation or bilingual summaries.

### 10.7 Student Progress Agent

Tracks learner performance and topic mastery.

### 10.8 Parent Summary Agent

Creates short and readable progress reports.

### 10.9 Safety Agent

Blocks unsafe, irrelevant, or low-quality outputs.

### 10.10 Evaluation Agent

Checks curriculum alignment, grade appropriateness, and answer quality.

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

- retrieve relevant curriculum passages
    
- ground answers in approved sources
    
- attach source references internally
    
- reduce hallucinations
    

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
    
4. critique the draft
    
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
    

---

## 12. Technical architecture

### 12.1 Backend

- Python
    
- FastAPI
    

### 12.2 Data storage

- PostgreSQL for persistent application data
    
- Redis for caching and background jobs
    

### 12.3 AI runtime

- Ollama for primary local model hosting
    
- provider adapters for fallback APIs
    

### 12.4 Retrieval layer

- pgvector, Qdrant, or Chroma
    

### 12.5 Channels

- Telegram first
    
- WhatsApp later
    

### 12.6 Document processing

- PDF parser
    
- DOCX parser
    
- OCR for images and worksheets
    

### 12.7 Voice processing

- speech-to-text
    
- optional text-to-speech later
    

### 12.8 Admin UI

- React or Next.js dashboard
    

---

## 13. Data model

### Main entities

- User
    
- StudentProfile
    
- TeacherProfile
    
- ClassGroup
    
- CurriculumTopic
    
- LessonPlan
    
- Question
    
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
    

---

## 14. API requirements

### Core endpoints

- `/chat`
    
- `/quiz/generate`
    
- `/lesson-plan/generate`
    
- `/progress/student/{id}`
    
- `/parent-summary/generate`
    
- `/content/search`
    
- `/admin/review`
    
- `/voice/transcribe`
    
- `/export/pdf`
    
- `/export/docx`
    

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
    

### Security

- secrets in environment variables or vault
    
- role-based access control
    
- no public exposure of sensitive student data
    

### Maintainability

- modular code
    
- test coverage
    
- clear docs
    
- clean separation of concerns
    

### Cost control

- use Ollama first
    
- fallback only when needed
    
- batch background tasks when possible
    

---

## 16. Testing and quality assurance

### Automated tests

- unit tests
    
- integration tests
    
- API tests
    
- retrieval tests
    
- language tests
    
- schema validation tests
    
- prompt regression tests
    

### Manual tests

- teacher workflow
    
- student workflow
    
- parent workflow
    
- low-bandwidth behavior
    
- voice input behavior
    
- fallback provider behavior
    

### Acceptance criteria

The system is acceptable when:

- students get understandable biology help
    
- teachers can generate and edit quizzes and lesson plans
    
- curriculum retrieval reduces hallucinations
    
- Ollama is used by default
    
- fallback works when necessary
    
- performance data is stored correctly
    
- deployment is repeatable
    

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

- Dockerized services
    
- migration scripts
    
- environment templates
    
- health checks
    
- backups
    

---

## 18. Suggested MVP delivery phases

### Phase 1

Telegram bot, basic tutoring, Ollama integration, retrieval.

### Phase 2

Quiz generation, lesson planning, teacher review tools.

### Phase 3

Student progress tracking, parent summaries, analytics.

### Phase 4

Voice support, OCR, WhatsApp integration, exports.

---

## 19. Risks and mitigations

### Risk: hallucinated answers

Mitigation: RAG, safety checks, fallback, teacher review.

### Risk: weak Amharic output

Mitigation: use Amharic selectively and keep English primary.

### Risk: local model performance issues

Mitigation: model routing and fallback providers.

### Risk: poor curriculum alignment

Mitigation: curated content store and human review.

### Risk: low internet access

Mitigation: text-first design and cached responses.

---

## 20. Definition of done

The product is done for v1 when:

- a student can use Telegram to ask biology questions
    
- a teacher can generate and edit lesson plans and quizzes
    
- the system uses Ollama first and falls back when needed
    
- curriculum grounding is active
    
- progress tracking works
    
- parent summaries work
    
- the app is tested, deployed, and maintainable
    

---

## 21. Build instruction for coding agents

Use this as the implementation directive:

```text
Build EthioBio AI Assistant v1.1 as a production-ready Telegram-first biology learning platform for Ethiopian middle and high school education.

Requirements:
- English-first curriculum alignment
- Amharic support as secondary
- Ollama as the primary model runtime
- fallback providers when local models are insufficient
- RAG over approved biology curriculum content
- agent-based architecture with tool use, routing, memory, confidence scoring, and self-checking
- FastAPI backend
- PostgreSQL + Redis
- teacher dashboard
- student progress tracking
- parent summaries
- quiz generation
- lesson planning
- voice support later
- Dockerized deployment
- full automated test coverage

Implementation order:
1. scaffold repo
2. build Telegram bot
3. integrate Ollama
4. add fallback provider routing
5. implement retrieval pipeline
6. implement tutor agent
7. implement quiz agent
8. implement lesson planner
9. implement student tracking
10. implement teacher dashboard
11. add tests and evaluation suite
12. add deployment scripts
13. document everything

Standards:
- no placeholder-only code
- no TODOs in final deliverable
- all endpoints tested
- all generated outputs schema-validated
- all secrets externalized
- readable logs
- clean docs
- working deployment
```

If you want, I can next turn this into a **developer-ready backlog** with **epics, user stories, acceptance criteria, and a week-by-week implementation plan**.