# PRD — Learner Snapshot Builder

## Project: EthioBio AI Assistant

## Parent Initiative: Learning Intelligence Layer (LIL)

## Status: Approved for Implementation

## Priority: Critical

## Type: Core Educational Intelligence Infrastructure

---

# Executive Summary

The Learner Snapshot Builder creates a unified, computed educational profile for each learner by aggregating data from existing EthioBio systems.

It becomes the canonical educational context consumed by:

* Recommendation Engine
* Tutor Personalization
* Continue Learning Dashboard
* Exam Readiness
* Future Teacher Intelligence
* Future Parent Intelligence

This feature does not introduce new educational storage systems.

Instead, it creates a centralized educational projection layer built on top of existing sources of truth.

---

# Problem Statement

Currently educational intelligence is fragmented.

Different services independently query:

```text
StudentMastery
StudentAbility
MisconceptionPattern
RecoveryPlan
SpacedRepetitionSchedule
EducationalMemory
UserGamification
```

This creates:

* duplicated logic
* inconsistent learner understanding
* poor scalability of personalization
* difficult future integrations

There is no unified educational profile.

---

# Goal

Create:

```python
LearnerSnapshot
```

as the single educational profile used throughout the platform.

---

# Non-Goals

This project will NOT:

* Create new mastery systems
* Replace StudentMastery
* Replace StudentAbility
* Replace RecoveryPlan
* Replace SpacedRepetitionSchedule
* Introduce event sourcing
* Introduce microservices
* Create a LearnerState database table

Existing systems remain authoritative.

---

# Architecture

```text
Existing Educational Systems
        ↓

Snapshot Builder
        ↓

LearnerSnapshot
        ↓

Recommendation Engine
Tutor
Dashboard
Telegram
Exam Readiness
```

---

# New Module

```text
src/core/learning_intelligence/
```

Structure:

```text
learning_intelligence/

├── models/
│   └── learner_snapshot.py
│
├── snapshot/
│   ├── snapshot_builder.py
│   ├── snapshot_service.py
│   └── cache_manager.py
│
├── schemas/
│   └── learner_snapshot.py
│
└── tests/
    ├── test_snapshot_builder.py
    ├── test_snapshot_cache.py
```

---

# Learner Snapshot Domain Model

## LearnerSnapshot

```python
class LearnerSnapshot:
    user_id: UUID

    generated_at: datetime

    mastery_by_topic: dict

    ability_by_topic: dict

    weak_topics: list[str]

    strong_topics: list[str]

    misconceptions: list[MisconceptionSummary]

    active_recovery_plans: list[RecoverySummary]

    due_reviews: list[ReviewSummary]

    educational_memory: EducationalMemorySummary

    engagement_metrics: EngagementMetrics

    gamification_state: GamificationSummary

    learning_goals: list[str]
```

---

# Sub Models

## MisconceptionSummary

```python
class MisconceptionSummary:
    topic: str
    pattern_type: str
    frequency: int
```

---

## RecoverySummary

```python
class RecoverySummary:
    topic: str
    progress_pct: float
    completed_tasks: int
    total_tasks: int
    status: str
```

---

## ReviewSummary

```python
class ReviewSummary:
    topic: str
    next_review_at: datetime
    days_overdue: int
```

---

## EngagementMetrics

```python
class EngagementMetrics:
    current_streak: int
    longest_streak: int

    total_xp: int
    level: int

    recent_activity_score: float
```

---

## EducationalMemorySummary

```python
class EducationalMemorySummary:
    understanding_level: str | None

    confidence: float | None

    active_learning_goals: list[str]

    recent_topics: list[str]
```

---

# Data Sources

## StudentMastery

Source:

```text
StudentMastery
```

Populate:

```python
mastery_by_topic
weak_topics
strong_topics
```

Rules:

```text
critical
moderate
mild
good
```

must remain unchanged.

---

## StudentAbility

Source:

```text
StudentAbility
```

Populate:

```python
ability_by_topic
```

---

## MisconceptionPattern

Source:

```text
MisconceptionPattern
```

Populate:

```python
misconceptions
```

Only include:

```text
frequency > 0
```

---

## RecoveryPlan

Source:

```text
RecoveryPlan
RecoveryTask
```

Populate:

```python
active_recovery_plans
```

Only:

```text
status = active
```

---

## Spaced Repetition

Source:

```text
SpacedRepetitionSchedule
```

Populate:

```python
due_reviews
```

Rules:

```text
next_review_at <= now()
```

---

## Educational Memory

Source:

```text
core/memory
```

Use latest educational summaries.

Populate:

```python
educational_memory
learning_goals
```

---

## Gamification

Source:

```text
UserGamification
```

Populate:

```python
gamification_state
engagement_metrics
```

---

# Snapshot Builder

## File

```text
snapshot_builder.py
```

---

## Interface

```python
class SnapshotBuilder:

    async def build(
        self,
        user_id: UUID
    ) -> LearnerSnapshot:
        ...
```

---

# Build Flow

```text
Load Mastery
      ↓

Load Ability
      ↓

Load Misconceptions
      ↓

Load Recovery
      ↓

Load Reviews
      ↓

Load Memory
      ↓

Load Gamification
      ↓

Assemble Snapshot
```

---

# Performance Requirements

Data retrieval must be parallelized where possible.

Use:

```python
asyncio.gather()
```

for independent queries.

---

# Snapshot Service

## File

```text
snapshot_service.py
```

---

## Purpose

Single access point.

No service may build snapshots directly.

---

## Interface

```python
class SnapshotService:

    async def get_snapshot(
        self,
        user_id: UUID
    ) -> LearnerSnapshot:
        ...
```

---

# Caching Strategy

## Strategy

Hybrid Cache

Approved Architecture.

---

## Cache Key

```text
learner_snapshot:{user_id}
```

---

## Cache TTL

```text
5 minutes
```

---

# Cache Invalidation Events

Invalidate snapshot cache when:

## Quiz Completion

```text
QuizAttempt.completed = True
```

---

## Recovery Task Completion

```text
RecoveryTask.is_completed = True
```

---

## Recovery Plan Completion

```text
RecoveryPlan.status = completed
```

---

## SRS Review Submission

```text
SpacedRepetition review processed
```

---

## Educational Summary Update

```text
New memory summary generated
```

---

# API

New module:

```text
src/api/intelligence/
```

---

## Endpoint

### GET /intelligence/snapshot

Response:

```json
{
  "user_id": "...",
  "generated_at": "...",

  "weak_topics": [],
  "strong_topics": [],

  "misconceptions": [],

  "active_recovery_plans": [],

  "due_reviews": [],

  "engagement_metrics": {}
}
```

---

# Error Handling

## User Not Found

```http
404
```

---

## Snapshot Build Failure

```http
500
```

Log detailed internal diagnostics.

Return generic client error.

---

# Observability

Log:

```text
snapshot_generation_started

snapshot_generation_completed

snapshot_cache_hit

snapshot_cache_miss

snapshot_generation_failed
```

---

# Metrics

Track:

```text
Average Snapshot Build Time

Cache Hit Rate

Cache Miss Rate

Snapshot Requests Per Day

Snapshot Failures
```

---

# Security

LearnerSnapshot is user-scoped.

Students may only access:

```text
their own snapshot
```

Future teacher/admin access must be implemented separately.

---

# Testing Requirements

## Unit Tests

Validate:

* mastery aggregation
* ability aggregation
* misconception aggregation
* recovery aggregation
* review aggregation
* memory aggregation

---

## Cache Tests

Validate:

* cache hit
* cache miss
* invalidation

---

## API Tests

Validate:

```text
GET /intelligence/snapshot
```

returns expected structure.

---

# Acceptance Criteria

## Functional

* Snapshot builds successfully for any learner.
* Snapshot aggregates all existing educational systems.
* Snapshot contains educational + engagement data.
* Snapshot service is centralized.
* Snapshot API returns complete learner profile.

---

## Performance

* Cached retrieval < 100ms.
* Fresh build < 2 seconds.
* Cache hit rate > 80%.

---

## Architectural

* No database schema changes.
* No existing educational systems modified.
* No duplicate learner-state logic introduced.
* Snapshot becomes the canonical educational profile.

---

# Success Definition

EthioBio gains a unified educational representation of every learner.

Future systems must consume:

```python
snapshot = snapshot_service.get_snapshot(user_id)
```

instead of independently querying educational models.

This establishes the foundation for:

1. Recommendation Engine
2. Tutor Learner Awareness
3. Continue Learning
4. Exam Readiness
5. Teacher Intelligence
6. Parent Intelligence

without requiring a major architectural rewrite.
