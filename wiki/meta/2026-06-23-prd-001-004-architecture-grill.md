---
type: session
title: "PRD-001–004 Architecture Grilling Session"
created: 2026-06-23
updated: 2026-06-23
tags:
  - architecture
  - memory-layer
  - knowledge-graph
  - event-bus
  - teacher-copilot
  - prd-review
status: developing
related:
  - "[[CONTEXT.md]]"
  - "[[docs/adr/0005-memory-event-flat-json.md]]"
  - "[[docs/adr/0006-event-bus-evolutionary-approach.md]]"
  - "[[docs/adr/0007-knowledge-graph-adjacency-tables.md]]"
  - "[[01-Planning/PRD's/Educational Intelligence Platform-PRD's/PRD-001 — Unified Educational Memory Layer (UEML).md]]"
  - "[[01-Planning/PRD's/Educational Intelligence Platform-PRD's/PRD-002 — Educational Event Bus (EEB).md]]"
  - "[[01-Planning/PRD's/Educational Intelligence Platform-PRD's/PRD-003 — Educational Knowledge Graph (EKG).md]]"
  - "[[01-Planning/PRD's/Educational Intelligence Platform-PRD's/PRD-004 — Teacher Copilot Workspace.md]]"
  - "[[01-Planning/PRD's/Educational Intelligence Platform-PRD's/PRD-010 — Educational Multi-Agent Intelligence System (EMAIS).md]]"
  - "[[01-Planning/Architectures/Educational Intelegence-Architecture/Educational Memory Architecture Specification (EMAS v1).md]]"
  - "[[01-Planning/Architectures/Educational Intelegence-Architecture/EthioBio AI Platform Vision & Target Architecture (v1).md]]"
sources:
  - "[[01-Planning/PRD's/Educational Intelligence Platform-PRD's/]]"
decision_date: 2026-06-23
status: active
---

# PRD-001–004 Architecture Grilling Session

## Context

Grilling session using the `grill-with-docs` skill to stress-test the PRD-001 through PRD-004 specifications against the existing codebase. The current codebase already has significant memory infrastructure (MemorySession, MemorySocraticState, MemoryEducationalSummary, MemoryEvent, ConversationTurn models with full REST APIs) — the PRDs were evaluated for what gaps remain.

## Decisions Made

### 1. Memory Event Storage (ADR-0005)

**Decision:** Keep flat JSONB `event_metadata` column on `memory_events`. Reject the PRD-001's normalized `memory_event_metadata` + `memory_event_links` tables.

**Rationale:** Event metadata is inherently heterogeneous per event type. Normalizing would require per-type tables or an EAV anti-pattern. PostgreSQL JSONB with GIN indexes is sufficient. Links table is additive later if needed.

**PRD amendment:** Updated PRD-001 Component 3 section to reflect single `semantic_facts` table.

### 2. Semantic Memory Store

**Decision:** Single `semantic_facts` table instead of the three-table normalized schema (semantic_memories + semantic_entities + semantic_relationships).

**Rationale:** Most semantic facts are already stored in existing models (StudentMastery, MisconceptionPattern, StudentAbility, MemoryEducationalSummary). The entity/relationship semantics belong in PRD-003 (Knowledge Graph). The `semantic_facts` table fills the unstructured gap — behavioral/preference/pattern facts discovered during tutoring and teacher interaction.

**PRD amendment:** Updated PRD-001 and EMAS documents.

**Implementation tasks:** DB model, SemanticFactManager, API endpoints, SnapshotBuilder loader, health endpoint.

### 3. Memory Consolidation Pipeline

**Decision:** Time-triggered cron pipeline (not event-triggered or lazy).

**Rationale:** Background job is the standard, predictable approach. Daily cron groups events by user+period and generates consolidated summaries at daily → weekly → monthly → quarterly levels. Distinct from session-level Summarizer.

**Implementation tasks:** `src/core/memory/consolidation/` package, `scripts/run_consolidation.py`, API endpoints, dashboard views.

### 4. Agent Memory Integration

**Decision:** Defer to PRD-010 (Multi-Agent Intelligence System). Current agents use existing `/memory/*` REST API.

**Rationale:** The formal `AgentMemoryClient` with `AgentMessage` protocol should be built when the Agent Orchestrator framework is designed. Building it now, before any multi-agent consumer exists, would be premature. PRD-001 Phase 3 is subsumed by PRD-010.

### 5. Timeline API

**Decision:** Build lightweight `GET /memory/timeline/{user_id}` endpoint.

**Rationale:** Thin compositing layer over existing tables (memory_events + memory_educational_summaries + semantic_facts). No new storage. Powers Teacher Copilot's "Show me what happened" queries. Harder to retrofit later.

### 6. Event Bus Strategy (ADR-0006)

**Decision:** Evolve EventLogger with schema validation + in-process subscriber registry. Reject full PRD-002 Event Bus with dedicated broker/queue/replay.

**Rationale:** Current platform is a single deployed service (monolith). Full broker/queue infrastructure would be premature abstraction. Existing `MemoryEvent` table is an append-only event store queryable via JSONB. The formal Event Bus (Redis Streams → Kafka) will be introduced when multiple independent services require decoupling.

**PRD amendment:** PRD-002 specification superseded by evolutionary approach.

**Implementation:** Pydantic event schema validation, enum-based event categories, in-process SubscriberRegistry with callbacks.

### 7. Knowledge Graph Architecture (ADR-0007)

**Decision:** Named adjacency tables in PostgreSQL with recursive CTEs. Reject generic Graph Abstraction Layer.

**Rationale:** Each relationship type gets its own table (`topic_prerequisites`, `student_misconceptions`, `intervention_outcomes`, `topic_misconceptions`). Prerequisite chain traversal uses `WITH RECURSIVE` CTEs. Self-documenting (each table name describes the relationship), performant for known patterns, no new infrastructure. Generic graph layers are over-engineered for the query patterns the platform actually needs.

**PRD amendment:** Updated PRD-003 Graph Architecture and Core Components sections.

**Implementation tasks:** TopicPrerequisite, InterventionOutcome, TopicMisconception models; RelationshipBuilder, GraphReasoningEngine, EKG API endpoints, GraphUpdateSubscriber.

### 8. Teacher Copilot Pipeline (PRD-004)

**Decision:** New LangGraph pipeline at `src/core/teacher_copilot/`. Separate from student tutor pipeline, reuses shared infrastructure.

**Rationale:** Consistent with existing LangGraph architecture. The evidence/graph/reasoning nodes will be reused by PRD-010 agents later. A thin REST wrapper cannot handle the multi-source reasoning chains (memory + graph + analytics + curriculum) that Teacher Copilot needs. Supports 5 MVP skills: Student Intelligence, Classroom Intelligence, Intervention Guidance, Curriculum Analysis, Assessment Generation.

**Implementation tasks:** Pipeline scaffold, IntentRouter, ReasoningEngine, EvidenceEngine, API endpoints, dashboard chat UI.

## Current Codebase State (at time of session)

### Already exists:
- MemorySession, MemorySocraticState, MemoryEducationalSummary, MemoryEvent, ConversationTurn models
- Full REST API under `/memory/*` (sessions, socratic state, events, summaries, search, health)
- SessionManager, SocraticManager, Summarizer, EventLogger, CrossSessionRecall
- MemoryVectorStore (ChromaDB) + RetrievalOrchestrator with recency/confidence/similarity ranking
- ContextAssembler with token budgeting (1500 tokens)
- Learning Intelligence engine (recommendations, readiness, teacher, school, parent services)
- Gamification, recovery plans, adaptive quiz engine
- Agentic RAG pipeline with EvidenceGraph, PlannerAgent, PlanExecutor, ClaimVerifier

### Needs building (from this session):
- SemanticFact model + manager + API
- Consolidation engine + cron script
- Timeline endpoint
- Knowledge Graph adjacency tables + builder + reasoning engine + API + subscriber
- EventLogger evolution (schema validation + subscriber registry)
- Teacher Copilot pipeline (intent router + reasoning + evidence + API + UI)

## Total Implementation Tasks

23 tasks across PRD-001→004 implementation. Prioritized by dependency chain: semantic_facts first, then consolidation/timeline, then EventLogger evolution, then Knowledge Graph, then Teacher Copilot.
