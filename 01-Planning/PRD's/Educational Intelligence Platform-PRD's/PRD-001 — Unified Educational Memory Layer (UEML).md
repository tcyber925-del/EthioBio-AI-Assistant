Excellent. We now have enough strategic foundation to begin writing the implementation PRDs.

The next PRD should be the most important infrastructure project in the entire EthioBio roadmap:

# PRD-001 — Unified Educational Memory Layer (UEML)

**Project:** EthioBio AI Platform
**Status:** Planned
**Priority:** CRITICAL
**Type:** Core Architecture
**Dependencies:** Existing Memory System, Learning Intelligence Engine, RAG Infrastructure

---

# Executive Summary

The Unified Educational Memory Layer (UEML) establishes a shared memory platform that captures, stores, retrieves, consolidates, and reasons over educational experiences across students, teachers, classrooms, interventions, and curriculum objectives.

The system transforms EthioBio from a collection of AI features into a continuously learning educational intelligence platform.

Every future capability—including Teacher Copilot, Misconception Intelligence, Digital Twins, Adaptive Planning, and Educational Forecasting—depends on UEML.

---

# Problem Statement

Current educational information exists across multiple systems:

* Assessment history
* Mastery snapshots
* Readiness predictions
* Intervention records
* Learning sessions
* RAG knowledge
* User interactions

These systems are partially connected but do not form a unified memory model.

As a result:

* Context is fragmented
* Historical reasoning is limited
* Agent collaboration is weak
* Long-term personalization is constrained
* Explanations lack continuity

---

# Goals

## Primary Goals

Create a unified educational memory platform.

Support long-term educational reasoning.

Provide shared memory for all agents.

Enable evidence-backed explanations.

Create foundations for future Digital Twin systems.

---

## Secondary Goals

Improve retrieval quality.

Reduce duplicate storage logic.

Simplify future feature development.

Improve teacher-facing intelligence.

---

# Non-Goals

This project will NOT:

Build the Educational Knowledge Graph.

Build Teacher Copilot.

Build Digital Twin simulations.

Build School Intelligence.

These will consume UEML later.

---

# Memory Architecture

## Memory Types

### Episodic Memory

Educational events.

Examples:

* Assessment completed
* Intervention launched
* Goal achieved
* Readiness changed

---

### Semantic Memory

Educational facts.

Examples:

* Student struggles with Genetics
* Classroom has strong Biology mastery

---

### Vector Memory

Similarity retrieval.

Examples:

* Similar misconceptions
* Similar students
* Similar interventions

---

### Consolidated Memory

Long-term summaries.

Examples:

> Student demonstrated steady improvement in Genetics between March and June.

---

# System Architecture

```text
Educational Memory Layer

├── Memory Ingestion Service
│
├── Episodic Memory Store
│
├── Semantic Memory Store
│
├── Vector Memory Store
│
├── Memory Consolidation Engine
│
├── Memory Retrieval Engine
│
├── Memory Query APIs
│
└── Memory Event APIs
```

---

# Core Components

## Component 1

Memory Ingestion Service

### Responsibilities

Convert platform activity into memory records.

### Sources

Assessments

Mastery updates

Readiness updates

Interventions

Learning sessions

Teacher actions

Agent actions

---

### Example

Input:

```json
{
  "event": "assessment_completed",
  "student_id": "123",
  "topic": "Cell Biology",
  "score": 82
}
```

Output:

```json
{
  "memory_type": "episodic",
  "event_type": "assessment_completed"
}
```

---

## Component 2

Episodic Memory Store

### Responsibilities

Store educational events.

### Storage

PostgreSQL

### Core Tables

```text
memory_events

memory_event_metadata

memory_event_links
```

---

### Event Categories

Assessment Events

Learning Events

Intervention Events

Prediction Events

Teacher Events

System Events

---

## Component 3

Semantic Memory Store

### Responsibilities

Store stable educational facts not covered by existing models (StudentMastery, MisconceptionPattern, StudentAbility, MemoryEducationalSummary).

### Examples

```text
Student struggles with Genetics

Teacher prefers diagrams

Classroom shows retention decline

Student loses focus after 20 minutes
```

---

### Core Table

```text
semantic_facts
```

A single lightweight table instead of the previously planned three-table normalized schema (semantic_memories + semantic_entities + semantic_relationships).

Columns: id, user_id (nullable for classroom/teacher facts), fact (text), confidence (float 0-1), source (e.g. tutor_session, teacher_input, consolidation), category (e.g. behavior, preference, pattern), expires_at (nullable), created_at.

**Rationale:** Most "semantic facts" are already stored in dedicated models (StudentMastery, MisconceptionPattern, StudentAbility, MemoryEducationalSummary). The three-entity schema belongs in the Educational Knowledge Graph (PRD-003). What's missing is a home for unstructured behavioral/preference/pattern facts discovered during tutoring and teacher interaction. A single table keeps this additive, searchable via text search + category filter, and avoids graph infrastructure before the Knowledge Graph exists. (See ADR-0005 and docs/adr/0005-memory-event-flat-json.md).

---

## Component 4

Vector Memory Store

### Responsibilities

Semantic retrieval.

### Technology

PostgreSQL + pgvector

---

### Supports

Student similarity

Intervention similarity

Misconception similarity

Classroom similarity

---

### Retrieval Examples

```text
Find similar students

Find similar interventions

Find related misconceptions
```

---

## Component 5

Memory Consolidation Engine

### Responsibilities

Convert raw events into meaningful summaries.

---

### Example

Input

```text
300 assessment events
```

Output

```text
Student mastery increased
consistently over 8 weeks.
```

---

### Consolidation Levels

Daily

Weekly

Monthly

Quarterly

---

### Generated Artifacts

Learning summaries

Growth summaries

Intervention summaries

Classroom summaries

---

## Component 6

Memory Retrieval Engine

### Responsibilities

Unified retrieval across memory types.

---

### Retrieval Modes

Direct Retrieval

Semantic Retrieval

Timeline Retrieval

Pattern Retrieval

Historical Retrieval

---

### Example Queries

```text
Why is this student struggling?

What interventions worked before?

How has mastery changed?

What misconceptions persist?
```

---

# APIs

## Memory Write API

```typescript
writeMemory({
  type,
  entity,
  content,
  metadata
})
```

---

## Memory Read API

```typescript
readMemory({
  entityId,
  memoryType
})
```

---

## Memory Search API

```typescript
searchMemory({
  query,
  filters
})
```

---

## Timeline API

```typescript
getTimeline({
  entityId,
  startDate,
  endDate
})
```

---

# Agent Integration

All future agents must use memory.

---

## Read

Memory Query API

---

## Write

Memory Event API

---

## Reflect

Memory Consolidation API

---

# Security Requirements

Student memories must be isolated.

Role-based access control.

Teacher access limited to authorized classrooms.

Memory audit trail required.

PII separation required.

---

# Dashboard Requirements

Administrative memory inspection.

Memory timeline viewer.

Memory search interface.

Memory debugging tools.

Memory statistics dashboard.

---

# Performance Requirements

Memory write:

<100ms

Memory retrieval:

<300ms

Vector search:

<500ms

Timeline generation:

<1 second

---

# Success Metrics

## Technical

95%+ memory ingestion success.

<300ms average retrieval.

Zero memory loss.

---

## Product

Teacher explanations improve.

Agent context quality improves.

Intervention recommendations improve.

Long-term personalization improves.

---

# Future Features Unlocked

Immediately after UEML completion:

### PRD-002

Educational Event Bus

---

### PRD-003

Educational Knowledge Graph

---

### PRD-004

Teacher Copilot

---

### PRD-005

Misconception Intelligence Engine

---

### PRD-010

Classroom Digital Twin

---

# Implementation Recommendation

Implement in three phases:

### Phase 1

Memory Infrastructure

* Memory stores
* APIs
* Ingestion

### Phase 2

Consolidation

* Summaries
* Historical reasoning
* Timeline generation

### Phase 3

Agent Integration

* Shared memory APIs
* Agent reflection
* Cross-agent memory access

This PRD should be treated as the single highest-priority architecture initiative in the EthioBio roadmap because nearly every future intelligence capability depends upon it.
