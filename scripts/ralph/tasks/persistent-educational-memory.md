# Feature PRD — Persistent Educational Memory Layer

## Project
EthioBio AI Assistant

## Branch
feature/persistent-educational-memory

## Status
Planned

## Priority
CRITICAL

## Type
Core Architecture Upgrade

---

# Overview

Implement a conversational memory layer that enables the tutor to remember what happened during and between tutoring sessions. The current system loses contextual continuity because the tutor pipeline is fully stateless — each request is independent, Socratic mode is a boolean toggle with no dialogue state, and mastery/misconception data (already persisted in DB) is never injected into the tutor prompt.

This feature introduces structured educational memory optimized for LangGraph-based tutoring, enabling long-horizon conversation continuity and learner personalization.

---

# Product Vision

Transform EthioBio from a stateless tutoring chatbot into a persistent adaptive educational intelligence platform where the tutor remembers:
- what was discussed in previous sessions
- where the Socratic dialogue left off
- the student's known misconceptions and weak areas
- preferred explanation styles and pacing

---

# What Already Exists (Do NOT Rebuild)

The following persistence infrastructure is already built and should be extended, not replaced:

| Existing System | What It Stores |
|---|---|
| `StudentMastery` | Per-topic mastery scores, severity, confidence, attempt count |
| `MisconceptionPattern` | Recurring wrong-answer patterns with frequency, resolved status |
| `TopicMasteryHistory` | Time-series snapshots of mastery changes |
| `StudentAbility` | Bayesian IRT ability estimates per user+topic |
| `SpacedRepetitionSchedule` | SM-2 review scheduling with intervals and ease factors |
| `StudentProfile` | Student metadata, topic_mastery dict, weak_areas list |
| `RecoveryPlan` / `RecoveryTask` | Remediation plan tracking |
| ChromaDB (via `VectorStoreAdapter`) | Curriculum content vector search |

The tutor pipeline (LangGraph or direct) does NOT read any of this data during tutoring — that is the core gap.

---

# Core Architecture

## Canonical Pipeline

All memory integration targets the **LangGraph pipeline**:
```
OrchestratorNode → RetrievalNode → TutorNode → SafetyNode
```
The direct `TutorAgent` path is legacy. Memory injection happens in `TutorNode`.

## Memory Injection Mechanism

Memory is injected as a structured **system prompt prefix** block in TutorNode:
```
Learner Context:
- Weak Topic: Cellular Respiration (confidence: low)
- Active Misconception: "Mitochondria produce oxygen" (frequency: 3)
- Socratic Stage: guided_discovery
- Last Session Summary: [compressed summary]
- Preferred Style: step-by-step explanations
```

Token budget: **1500 tokens max** for memory context. Curriculum RAG chunks fill the remaining window. Dynamic truncation by importance.

## Session Strategy

Stateless per-request with DB reads. Each tutor request:
1. Reads latest `SessionState` + `SocraticState` from DB
2. Retrieves relevant `EducationalSummary` from ChromaDB
3. Assembles memory block into system prompt
4. Calls LLM
5. Writes updated state + events back to DB

Sessions are defined implicitly by activity clusters (gap > 30min = new session).

---

# Components

## Component 1 — SessionState (New Table)

Stores active tutoring conversation context.

Table: `memory_sessions`
- `session_id` UUID (PK)
- `user_id` UUID (FK)
- `active_topic` varchar(300)
- `tutoring_mode` varchar(20) — "socratic" | "direct" | "quiz_prep"
- `educational_context` text — brief rolling summary
- `unresolved_questions` json — list of unanswered student questions
- `started_at` timestamptz
- `last_active_at` timestamptz
- `summary` text — compressed educational summary (populated on session close)

Lifetime: Created on first request, updated per-turn, closed after 30min inactivity.

---

## Component 2 — SocraticState (New Table)

Tracks multi-turn guided dialogue progression.

Table: `memory_socratic_states`
- `user_id` UUID (FK, PK)
- `topic` varchar(300)
- `socratic_stage` varchar(30) — LLM-determined: `guided_discovery` | `evaluation` | `correction` | `consolidation`
- `current_focus` varchar(500) — the concept being guided on
- `student_understanding` varchar(20) — LLM assessment: "none" | "partial" | "emerging" | "solid"
- `next_question` text — what to ask next
- `conceptual_gaps` json — gaps LLM has identified
- `updated_at` timestamptz

The LLM determines the stage, understanding level, and next question. Code only persists what the LLM outputs — no state machine transition rules.

---

## Component 3 — EducationalSummary (New Table)

Compressed, educationally-significant summaries of completed tutoring sessions.

Table: `memory_educational_summaries`
- `id` UUID (PK)
- `user_id` UUID (FK)
- `topic` varchar(300)
- `understanding_level` varchar(20)
- `key_misconceptions` json
- `confidence` float
- `next_learning_goal` text
- `tutoring_quality_notes` text (nullable)
- `embedding_id` varchar(100) — link to ChromaDB vector
- `created_at` timestamptz

Stored in both PostgreSQL (structured data) and ChromaDB (vector embeddings for semantic retrieval).

---

## Component 4 — Educational Events Log

Minimal logging table, not a full event system.

Table: `memory_events`
- `id` UUID (PK)
- `user_id` UUID (FK)
- `event_type` varchar(50) — e.g. "session_started", "session_closed", "misconception_detected", "socratic_breakthrough"
- `topic` varchar(300)
- `metadata` json
- `created_at` timestamptz

Existing domain-specific event tables (`QuizAttempt`, `RecoveryNotification`, `TopicMasteryHistory`) are NOT replaced. This table captures memory-specific lifecycle events for debugging and future analytics.

---

## Component 5 — Semantic Retrieval Orchestrator

Reads from ChromaDB (educational summaries collection) with custom ranking.

Retrieval inputs considered:
- semantic similarity (cosine distance)
- recency (decay weight)
- pedagogical importance (misconception severity, weak area status)
- confidence

Ranking produces a scored list. Token budget enforcement truncates by rank.

---

## Component 6 — Summarization Engine

Triggered when a session closes (30min inactivity or explicit end). Compresses the session's conversational context into an `EducationalSummary`.

Extracts:
- misconceptions detected
- conceptual progress
- unresolved confusion
- confidence
- next learning goals
- recommendations

Does NOT store: conversational filler, redundant messages, raw transcripts.

---

# What to Build (5 Ralph Passes)

## Pass 1 — Session + Socratic Memory
- Create `memory_sessions` and `memory_socratic_states` tables
- Implement session lifecycle tracking (create/read/update/close)
- Implement SocraticState read/write in TutorNode
- Wire session context into the existing LangGraph pipeline

## Pass 2 — Educational Summarization
- Create `memory_educational_summaries` table
- Create ChromaDB collection `educational_memories`
- Build summarization pipeline (LLM-based, triggered on session close)
- Generate and store embeddings for each summary

## Pass 3 — Semantic Retrieval + Ranking
- Implement retrieval from `educational_memories` ChromaDB collection
- Build ranking layer: semantic similarity + recency weight + confidence weight + pedagogical importance
- Implement token budget enforcement
- Add topic filtering support

## Pass 4 — Memory Injection into TutorNode
- Build memory context assembler (reads SessionState + SocraticState + top-N summaries + mastery/misconception data)
- Format as system prompt prefix (1500t cap)
- Modify TutorNode to include memory block before RAG context
- Ensure backward compatibility (no memory = current behavior)

## Pass 5 — Evaluation + Optimization
- Measure: retrieval latency, token efficiency, relevance accuracy, hallucinated memory frequency
- Implement safety safeguards (confidence thresholds before persistence, contradiction checks via recency)
- Benchmark and optimize retrieval ranking

---

# User Stories

## MEM-001 — Session Lifecycle
As a student, I want the tutor to remember the current tutoring conversation across turns so that I don't have to repeat myself.

Acceptance Criteria:
- Session state created on first message
- Session updated after each turn
- Session closed after 30min inactivity
- Session context available in TutorNode

Priority: 1

---

## MEM-002 — Socratic Continuity
As a student, I want guided Socratic dialogue to resume where it left off so that reasoning flows continue naturally across interruptions.

Acceptance Criteria:
- SocraticStage persisted
- Stage determined by LLM (guided_discovery/evaluation/correction/consolidation)
- Next question stored and retrievable
- No code-enforced state machine transitions

Priority: 1

---

## MEM-003 — Session Summarization
As a student, I want tutoring sessions summarized automatically so that long-term educational continuity is preserved efficiently.

Acceptance Criteria:
- Summaries generated on session close
- Misconceptions and progress extracted
- Embedding stored in ChromaDB
- Redundant content excluded

Priority: 2

---

## MEM-004 — Semantic Memory Retrieval
As a student, I want the tutor to recall relevant past educational discussions so that responses remain personalized.

Acceptance Criteria:
- Semantic retrieval from ChromaDB operational
- Ranking considers recency, confidence, topic relevance
- Token budget enforced (1500t max)
- Retrieval filtering by topic supported

Priority: 2

---

## MEM-005 — Memory Injection into Tutoring
As a student, I want the tutor to use my learning history when explaining concepts so that tutoring adapts to my needs.

Acceptance Criteria:
- System prompt prefix injected with learner context
- Active misconceptions visible in tutor behavior
- Socratic continuity maintained across sessions
- Backward compatible (no memory = current behavior)

Priority: 3

---

## MEM-006 — Educational Events Logging
As a developer, I want memory lifecycle events logged so that I can debug and analyze memory behavior.

Acceptance Criteria:
- memory_events table created
- Key events logged: session_started, session_closed, socratic_breakthrough
- Metadata captures relevant context
- Performance overhead minimal

Priority: 3

---

# Database Schema Extensions

## New Tables

```sql
CREATE TABLE memory_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    active_topic VARCHAR(300),
    tutoring_mode VARCHAR(20) DEFAULT 'direct',
    educational_context TEXT,
    unresolved_questions JSON DEFAULT '[]',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    summary TEXT
);

CREATE TABLE memory_socratic_states (
    user_id UUID NOT NULL REFERENCES users(id),
    topic VARCHAR(300) NOT NULL,
    socratic_stage VARCHAR(30) DEFAULT 'guided_discovery',
    current_focus VARCHAR(500),
    student_understanding VARCHAR(20) DEFAULT 'none',
    next_question TEXT,
    conceptual_gaps JSON DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, topic)
);

CREATE TABLE memory_educational_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    topic VARCHAR(300) NOT NULL,
    understanding_level VARCHAR(20),
    key_misconceptions JSON DEFAULT '[]',
    confidence FLOAT DEFAULT 0.0,
    next_learning_goal TEXT,
    tutoring_quality_notes TEXT,
    embedding_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE memory_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,
    topic VARCHAR(300),
    metadata JSON DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_memory_events_user ON memory_events(user_id, created_at DESC);
CREATE INDEX idx_memory_sessions_user ON memory_sessions(user_id, last_active_at DESC);
```

## Extended Types

Extend `MisconceptionPattern` with confidence and severity tracking:
- `confidence FLOAT DEFAULT 0.0` — how sure we are this is a real misconception
- `severity VARCHAR(20) DEFAULT 'low'` — "low" | "medium" | "high"

---

# API Endpoints

## Session
- `POST /memory/session/start` — create new session (user_id, topic)
- `GET /memory/session/{user_id}/active` — get active session
- `PUT /memory/session/{session_id}/heartbeat` — extend session TTL
- `POST /memory/session/{session_id}/close` — close session, trigger summarization

## Socratic
- `GET /memory/socratic/{user_id}/{topic}` — get current Socratic state
- `PUT /memory/socratic/{user_id}/{topic}` — update Socratic state

## Summaries
- `GET /memory/summaries/{user_id}` — list past summaries
- `GET /memory/summaries/{user_id}/{topic}` — filter by topic
- `POST /memory/summarize/{session_id}` — manually trigger summarization

## Events
- `POST /memory/events` — log an educational event
- `GET /memory/events/{user_id}` — query events

---

# Directory Structure

```
src/core/memory/
    __init__.py
    session_manager.py      — session lifecycle
    socratic_manager.py     — SocraticState read/write
    summarizer.py           — LLM-based session compression
    retrieval_orchestrator.py — ranking + token budgeting
    context_assembler.py    — build memory system prompt block
    event_logger.py         — lightweight event logging
    models.py               — Pydantic models for memory data
    router.py               — FastAPI router

    ChromaDB collection: "educational_memories"
```

---

# Non-Goals (Explicitly Out of Scope)

- Full adaptive learning engine
- Multi-agent memory governance
- Knowledge graph layer
- Dedicated lifecycle engine (decay/aging/pruning)
- Full event bus / event-driven architecture
- Teacher analytics dashboards
- Multi-subject abstraction
- WhatsApp integration
- Predictive grading

These can be added later when real usage data warrants.

---

# Risks

## R1 — Prompt Bloat
Memory context may crowd out curriculum content.
**Mitigation:** 1500t hard cap, dynamic truncation by rank.

## R2 — Incorrect Memory Persistence
LLM may hallucinate misconceptions or confidence levels.
**Mitigation:** Confidence scoring, recency weighting (old incorrect entries naturally fade).

## R3 — Retrieval Noise
Irrelevant memories reduce tutoring quality.
**Mitigation:** Topic filtering, recency weighting, ranking before injection.

## R4 — Memory Drift
Summaries may distort educational meaning.
**Mitigation:** LLM-generated summaries include confidence scores; evaluation pass (Pass 5) measures summary quality.

---

# Definition of Done

Feature is complete when:
- Session lifecycle works across multiple turns
- Socratic state persists and resumes correctly
- Educational summaries generated on session close
- Semantic retrieval operational from ChromaDB
- Retrieval ranking considers recency, confidence, relevance
- Memory context injected into TutorNode (1500t cap)
- Backward compatible (no memory = current behavior)
- Memory events logged for debugging
- All tests pass
- Typecheck passes
