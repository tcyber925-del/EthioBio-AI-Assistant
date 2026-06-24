# Educational Memory Architecture Specification (EMAS v1)

**Project:** EthioBio AI Platform
**Document Type:** Core Architecture Specification
**Status:** Approved Foundation Architecture
**Priority:** CRITICAL
**Version:** 1.0

---

# Purpose

The Educational Memory Layer serves as the central intelligence substrate of EthioBio.

Every major platform capability must read from and write to this layer.

Without it:

* Teacher Copilot becomes stateless
* Learning Intelligence becomes fragmented
* Interventions cannot learn
* Digital Twins cannot exist
* Agents cannot collaborate

The Educational Memory Layer becomes the long-term institutional memory of learning.

---

# Architectural Vision

Traditional educational systems store data.

EthioBio stores understanding.

Instead of:

```text
Student → Assessment → Score
```

We want:

```text
Student
 ↓
Learning History
 ↓
Mastery Evolution
 ↓
Misconceptions
 ↓
Interventions
 ↓
Growth Patterns
 ↓
Predictions
```

Memory becomes a living model of learning.

---

# Core Design Principles

## Principle 1

Memory Is A Platform Capability

Not:

```text
Feature Memory
```

But:

```text
Shared Platform Memory
```

All services consume the same memory layer.

---

## Principle 2

Everything Important Becomes Memory

Examples:

* Quiz completion
* Readiness changes
* Intervention launches
* Learning breakthroughs
* Persistent misconceptions
* Goal achievement

---

## Principle 3

Memory Must Be Explainable

Every recommendation should answer:

```text
Why?
```

Teacher Copilot should be able to say:

> Student was recommended because readiness dropped 18% across the last three assessments.

---

## Principle 4

Memory Must Support Agents

Future agents:

* Teacher Agent
* Assessment Agent
* Curriculum Agent
* Intervention Agent
* Diagram Agent

Must all access the same memory layer.

---

# Memory Taxonomy

The system contains five memory types.

---

# Memory Type 1: Episodic Memory

Stores educational events.

Represents:

```text
What Happened
```

Examples:

```text
Student completed assessment

Teacher launched intervention

Student achieved mastery

Readiness dropped

Forgetting risk increased
```

Storage:

```text
event_store
```

Schema:

```text
event_id
actor_id
event_type
timestamp
metadata
```

Example:

```json
{
  "event": "assessment_completed",
  "student": "123",
  "score": 82,
  "topic": "Cell Biology"
}
```

---

# Memory Type 2: Semantic Memory

Stores stable educational facts.

Represents:

```text
What We Know
```

Examples:

```text
Student struggles with Genetics

Teacher prefers inquiry-based learning

Classroom performs strongly in Biology

Photosynthesis is prerequisite for Ecology
```

Storage:

```text
semantic_facts
```

Schema:

```text
id
user_id (nullable; for classroom/teacher facts)
fact (text)
confidence (float 0-1)
source (tutor_session | teacher_input | consolidation)
category (behavior | preference | pattern)
expires_at (nullable)
created_at
```

Note: The architecture originally envisioned a normalized three-table schema (semantic_memories + semantic_entities + semantic_relationships). This was collapsed into a single semantic_facts table after implementation review. Most "entity" and "relationship" semantics are served by existing models (StudentMastery, MisconceptionPattern, StudentAbility) and the future Educational Knowledge Graph (PRD-003). The facts table fills only the unstructured gap — behavioral/preference/pattern facts discovered during tutoring and teacher interaction.

---

# Memory Type 3: Procedural Memory

Stores successful educational strategies.

Represents:

```text
What Works
```

Examples:

```text
Retrieval practice improves retention

Diagrams improve mastery

Peer tutoring reduces risk
```

Future use:

Teacher Copilot

Lesson Planner

Intervention Planner

Digital Twin

---

# Memory Type 4: Vector Memory

Stores semantic embeddings.

Represents:

```text
What Is Similar
```

Examples:

```text
Similar students

Similar misconceptions

Similar interventions

Similar classrooms
```

Storage:

```text
pgvector
```

Recommended:

```text
PostgreSQL + pgvector
```

Avoid introducing external vector databases until scale demands it.

---

# Memory Type 5: Graph Memory

Stores educational relationships.

Represents:

```text
How Things Connect
```

Example:

```text
Student
 ↓
misunderstands
 ↓
Cellular Respiration
```

Example:

```text
Topic
 ↓
depends_on
 ↓
Cell Structure
```

Future implementation:

Educational Knowledge Graph

---

# Educational Memory Hierarchy

---

## Level 1: Student Memory

Stores:

```text
Learning history

Mastery evolution

Assessment history

Goals

Misconceptions

Interventions

Predictions
```

Most important memory type.

---

## Level 2: Classroom Memory

Stores:

```text
Classroom readiness

Classroom misconceptions

Classroom interventions

Learning trends
```

Used by Teacher Intelligence.

---

## Level 3: Teacher Memory

Stores:

```text
Teaching preferences

Intervention preferences

Planning preferences

Successful strategies
```

Supports Teacher Copilot.

---

## Level 4: Curriculum Memory

Stores:

```text
Objectives

Dependencies

Coverage

Topic mastery
```

Supports Curriculum Intelligence.

---

## Level 5: School Memory

Future layer.

Stores:

```text
School readiness

School interventions

School trends
```

Supports School Intelligence Hub.

---

# Memory Lifecycle

Every memory follows:

```text
Capture
 ↓
Store
 ↓
Retrieve
 ↓
Reason
 ↓
Update
 ↓
Archive
```

---

# Capture Layer

Sources:

```text
Assessments

Quizzes

Teacher actions

Student actions

Interventions

Learning sessions

Predictions
```

Everything produces events.

---

# Retrieval Layer

Three retrieval modes.

---

## Mode 1

Direct Retrieval

Example:

```text
Get student mastery
```

---

## Mode 2

Semantic Retrieval

Example:

```text
Find similar misconceptions
```

Uses vector memory.

---

## Mode 3

Graph Retrieval

Example:

```text
Find prerequisite topics
```

Uses knowledge graph.

---

# Memory Service Architecture

```text
src/core/memory/
```

Proposed structure:

```text
memory/

├── episodic/
├── semantic/
├── procedural/
├── vector/
├── graph/
│
├── retrieval/
├── ingestion/
├── indexing/
├── summarization/
├── consolidation/
│
└── services/
```

---

# Memory Consolidation Layer

Critical future component.

Raw memories accumulate endlessly.

System periodically creates:

```text
Memory Summaries
```

Example:

Instead of:

```text
500 assessment events
```

Store:

```text
Student steadily improved
in Genetics over 3 months.
```

This becomes long-term memory.

---

# Agent Integration

Every agent interacts through memory.

---

## Read

```text
Memory Query API
```

---

## Write

```text
Memory Event API
```

---

## Reflect

```text
Memory Reflection API
```

Agents learn from historical outcomes.

---

# Teacher Copilot Dependency

Teacher Copilot should never access raw databases.

Instead:

```text
Teacher Copilot
 ↓
Memory Layer
 ↓
Intelligence Layer
 ↓
Response
```

Memory becomes the context engine.

---

# Digital Twin Dependency

Digital Twin requires:

```text
Historical memory

Interventions

Predictions

Relationships

Outcomes
```

Without memory:

Digital Twin impossible.

---

# Success Criteria

The memory layer is complete when:

### Student

Can reconstruct full learning history.

---

### Teacher

Can ask:

> Why is this student struggling?

and receive evidence-backed explanations.

---

### Copilot

Can reason across months of educational activity.

---

### Agents

Can share intelligence through memory.

---

### Future Systems

Can build:

* Digital Twin
* School Intelligence
* Educational Forecasting

without redesigning architecture.

---

# Implementation Recommendation

After approving EMAS v1, immediately create:

### PRD-001

Unified Educational Memory Layer

which should implement:

1. Episodic Memory
2. Semantic Memory
3. Vector Memory
4. Memory Retrieval APIs
5. Memory Consolidation
6. Agent Memory Integration

Graph Memory should be integrated in **PRD-003 Educational Knowledge Graph**, not in the initial memory implementation.

This keeps implementation manageable while still establishing the foundation for the entire EthioBio Educational Intelligence Platform.
