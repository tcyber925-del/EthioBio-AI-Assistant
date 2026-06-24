# EthioBio v2 Implementation Roadmap

**Status:** Active
**Last Updated:** 2026-06-23
**Source:** Architecture grilling session + PRD-001→010 analysis

---

## Strategic Objective

Transform EthioBio from an AI Biology Assistant into an Educational Intelligence Platform using incremental value delivery.

---

## Wave 0 — Foundation Stabilization

**Priority:** CRITICAL
**Before building anything new.**

### Goals
- Stabilize existing architecture
- Reduce technical debt
- Prepare for intelligence systems

### Deliverables
- Existing Dashboard Redesign
- Design System (`components/ui`, tokens, spacing, typography, theme)
- Unified Entity Models (Student, Teacher, Classroom, Assessment, Intervention, Lesson)
- Event Schema Foundation (Pydantic schemas, not full Event Bus)
- Memory Interface Layer (`MemoryService` abstraction)

---

## Wave 1 — Teacher Copilot MVP

**Priority:** HIGHEST
**First visible user value.**

### Build
- Teacher Chat interface (new LangGraph pipeline at `src/core/teacher_copilot/`)
- Classroom Summary
- Student Summary
- Insight Generation
- RAG Integration
- Existing Analytics Integration

### Teacher Can Ask
```
Who needs attention?
Why is readiness dropping?
What topic should I reteach?
```

---

## Wave 2 — Memory Foundation

**Priority:** HIGH

### Build
- Episodic Memory (events for assessments, lessons, interventions, teacher actions)
- Timeline API (`GET /memory/timeline/{user_id}`)
- Classroom Timeline
- Memory Interface Layer implementation (backed by episodic store)

### Explicitly Out of Scope
- Semantic facts table (deferred)
- Advanced consolidation pipeline (deferred)
- Graph memory

---

## Wave 3 — Misconception Intelligence MVP

**Priority:** HIGH

### Build
- Rule-Based Detection
- Assessment Pattern Analysis
- Misconception Profiles
- Teacher Dashboard

### Focus Topics (Biology niche)
- Photosynthesis, Respiration, Genetics, Cell Division

---

## Wave 4 — Assessment Studio MVP

**Priority:** HIGH

### Build
- Quiz Generation
- Diagnostic Questions
- Diagram Assessments
- Misconception Assessments
- Integration with Teacher Copilot, Lesson Planner, Misconception Engine

---

## Wave 5 — Intervention Analytics

**Priority:** MEDIUM

### Build
- Intervention Tracking
- Outcome Measurement
- Effectiveness Scoring
- Recommendation Ranking

### Answers
```
What intervention works?
```

---

## Wave 6 — Knowledge Graph

**Priority:** MEDIUM

### Build
- Curriculum Graph (topic dependencies, prerequisites)
- Learning Objectives
- Misconception Links

### Architecture
Named adjacency tables in PostgreSQL with recursive CTEs (see ADR-0007).

---

## Wave 7 — Adaptive Lesson Planning

**Priority:** MEDIUM

### Build (after Wave 1–6 data exists)
- Lesson Generator
- Differentiation (advanced/standard/support groups)
- Activity Suggestions
- Diagram Suggestions

---

## Wave 8 — Event Bus

**Priority:** LOW

### Approach
Postgres Event Log first (evolve existing `EventLogger`). Redis Streams → Kafka deferred until multiple independent services exist (see ADR-0006).

---

## Wave 9 — Digital Twin

**Priority:** LOW
Only after sufficient assessment + intervention + memory history exists.

---

## Wave 10 — Multi-Agent System

**Priority:** LOWEST
Build last. Agents require memory, knowledge graph, assessment data, intervention data, and digital twins to be genuinely useful.

---

## Sprint Mapping

| Sprint | Wave | Key Deliverables |
|--------|------|-----------------|
| Sprint 1 | Wave 0 | Dashboard redesign, design system, entity models, memory interfaces |
| Sprint 2 | Wave 1 | Teacher Copilot MVP |
| Sprint 3 | Wave 2 | Episodic memory, timeline system |
| Sprint 4 | Wave 3 | Misconception Intelligence MVP |
| Sprint 5 | Wave 4 | Assessment Studio MVP |
| Sprint 6+ | Wave 5–10 | Remaining waves |

---

## ADR Index

| ADR | Title | Applies To |
|-----|-------|-----------|
| 0005 | Memory Event Storage — Flat JSONB | Wave 2 |
| 0006 | Event Bus — Evolutionary Approach | Wave 8 |
| 0007 | Knowledge Graph — Adjacency Tables | Wave 6 |

## Key Principles

1. **Teacher Copilot before infrastructure** — Build the consumer first, validate API shapes, then build the infrastructure
2. **Postgres-first** — Avoid dedicated infrastructure until scale demands it
3. **Biology niche first** — Focus misconception intelligence on photosynthesis, respiration, genetics, cell division
4. **Event Bus last** — The monolith doesn't need events; multiple services do
5. **Agents last** — Agents need data and history to be useful
