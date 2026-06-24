# Digital Twin Builder — Design Spec

**Date:** 2026-06-24
**Status:** Draft
**PRD:** PRD-009 — Student Digital Twin & Learning Simulation Engine (sub-project 1: Twin Builder)

## Overview

The Twin Builder creates and maintains a materialized `student_digital_twins` table that folds 6 learner dimensions into a single queryable snapshot per student. Dimensions are updated asynchronously via event bus events.

**Scope:** Twin data model + builder service + event subscription + GET endpoint + dashboard viewer + confidence metadata. No simulation/forecasting engine (sub-projects 2-3).

## Architecture

```
Student activity event (quiz_submit, lesson_complete, intervention_assigned, ...)
  → Event Bus (existing, PRD-002)
    → Twin Event Handler
      → TwinBuilder.rebuild(user_id)
        → gather_knowledge_state()
        → gather_mastery_state()
        → gather_misconception_state()
        → gather_retention_state()
        → gather_readiness_state()
        → gather_intervention_state()
        → compute_twin_confidence()
        → upsert student_digital_twins
        → emit twin_updated event
```

The rebuild is **full** (all 6 dimensions) on each trigger — simpler than delta-patching and data volume is low (< 100 rows per student per dimension). Each dimension gatherer handles its own failure with a graceful fallback.

## Data Model

### `student_digital_twins`

Single table, one row per user:

```sql
CREATE TABLE student_digital_twins (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    knowledge_state JSONB,      -- { topics: { "Cell Division": { score: 0.72, ... } }, ... }
    mastery_state JSONB,        -- { topics: { "Genetics": { mastery_score: 0.85, level: "proficient", ... } }, ... }
    misconception_state JSONB,  -- { topics: { "Photosynthesis": [ { pattern: "...", severity: "...", ... } ] }, ... }
    retention_state JSONB,      -- { topics: { "Ecology": { retention_score: 0.6, last_reviewed: "...", ... } }, ... }
    readiness_state JSONB,      -- { topics: { "Genetics": { readiness_score: 0.74, projected: 0.88, ... } }, ... }
    intervention_state JSONB,   -- { active: 2, completed: 5, responsiveness: 0.7, ... }
    overall_health TEXT,        -- 'healthy' | 'needs_attention' | 'at_risk' (derived from dimensions)
    confidence FLOAT,           -- 0.0-1.0 overall confidence across dimensions
    last_built_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Dimension JSON Structures

Each dimension JSONB stores a dict:

**knowledge_state:**
```json
{
  "overall": 0.75,
  "topics": {
    "Cell Division": { "score": 0.72, "data_points": 8, "last_updated": "2026-06-24T10:00:00Z", "confidence": 0.8 },
    "Genetics": { "score": 0.88, "data_points": 12, "last_updated": "2026-06-23T14:00:00Z", "confidence": 0.9 }
  }
}
```

**mastery_state:**
```json
{
  "overall": 0.81,
  "topics": {
    "Cell Division": { "mastery_score": 0.72, "level": "developing", "trend": "improving", "data_points": 5 }
  }
}
```

**misconception_state:**
```json
{
  "total_active": 2,
  "total_resolved": 8,
  "topics": {
    "Photosynthesis": [
      { "pattern": "Plants get food from soil", "severity": "misconception", "rank": 3, "active_since": "2026-06-01T00:00:00Z" }
    ]
  }
}
```

**retention_state:**
```json
{
  "overall": 0.68,
  "topics": {
    "Ecology": { "retention_score": 0.6, "last_reviewed": "2026-06-10T00:00:00Z", "days_since_review": 14, "forgetting_risk": "medium" }
  }
}
```

**readiness_state:**
```json
{
  "overall": 0.78,
  "topics": {
    "Genetics": { "readiness_score": 0.74, "prerequisites_met": true, "risk_level": "low" }
  }
}
```

**intervention_state:**
```json
{
  "active_count": 2,
  "completed_count": 5,
  "responsiveness": 0.7,
  "by_type": { "remediation": { "assigned": 3, "completed": 2, "avg_effectiveness": 0.65 } }
}
```

### Source Tables

| Dimension | Source Queries | Fallback |
|-----------|---------------|----------|
| knowledge | `StudentAbility` (ability_score per topic) | empty dict |
| mastery | `StudentMastery` (mastery_score, level per topic) | empty dict |
| misconception | `MisconceptionPattern` (pattern, severity, resolved) | empty dict |
| retention | `SpacedRepetitionSchedule` (retention_score, next_review) | empty dict |
| readiness | `StudentMastery` + `TopicPrerequisite` (prereq check) | empty dict |
| intervention | `InterventionAssignment` (counts, effectiveness) | empty dict |

## Confidence Computation

Per-dimension confidence: `(0.5 * freshness) + (0.5 * volume_clamped)`

- `freshness`: `max(0, 1 - hours_since_update / 168)` (decays to 0 over 7 days)
- `volume_clamped`: `min(data_points / 10, 1.0)` (capped at 10 data points = 1.0)
- Overall confidence: weighted average across dimensions with non-empty data

## Twin Builder Service

### `src/core/digital_twin/builder.py`

```python
class TwinBuilder:
    def __init__(self, session: AsyncSession, event_bus: EventBus):
        ...

    async def rebuild(self, user_id: UUID) -> dict:
        """Gather all 6 dimensions, compute confidence, upsert twin."""
        ...

    async def gather_knowledge_state(self, user_id: UUID) -> dict:
        """Query StudentAbility table, build topic map with scores."""
        ...

    async def gather_mastery_state(self, user_id: UUID) -> dict:
        """Query StudentMastery table."""
        ...

    async def gather_misconception_state(self, user_id: UUID) -> dict:
        """Query MisconceptionPattern table."""
        ...

    async def gather_retention_state(self, user_id: UUID) -> dict:
        """Query SpacedRepetitionSchedule table."""
        ...

    async def gather_readiness_state(self, user_id: UUID) -> dict:
        """Query StudentMastery + TopicPrerequisite."""
        ...

    async def gather_intervention_state(self, user_id: UUID) -> dict:
        """Query InterventionAssignment for counts + effectiveness."""
        ...

    def compute_health(self, state: dict) -> str:
        """Derive overall_health from dimension states."""
        ...

    def compute_confidence(self, state: dict) -> float:
        """Compute 0-1 confidence from freshness + volume."""
        ...
```

### `src/core/digital_twin/models.py`

SQLAlchemy model for `student_digital_twins` table.

## Event Subscription

### `src/core/digital_twin/events.py`

Subscribe to event types:

```python
EVENT_TYPES = [
    "assessment_completed",      # quiz submit → rebuild knowledge + mastery
    "lesson_delivered",          # lesson complete → rebuild readiness
    "intervention_completed",    # intervention done → rebuild intervention state
    "intervention_assigned",     # new assignment → rebuild intervention state
    "misconception_detected",    # new misconception → rebuild misconception state
    "misconception_resolved",    # resolved → rebuild misconception state
]
```

Handler pattern:
1. Extract `user_id` from event payload
2. Call `TwinBuilder.rebuild(user_id)` in background task
3. Emit `twin_updated` event with new twin state summary

## API

### `GET /digital-twin/{user_id}`

Returns the full twin for a student. 404 if no twin exists yet.

Response:
```json
{
  "user_id": "uuid",
  "knowledge_state": { ... },
  "mastery_state": { ... },
  "misconception_state": { ... },
  "retention_state": { ... },
  "readiness_state": { ... },
  "intervention_state": { ... },
  "overall_health": "needs_attention",
  "confidence": 0.85,
  "last_built_at": "2026-06-24T10:00:00Z"
}
```

### `POST /digital-twin/{user_id}/rebuild`

Force a rebuild (e.g., after migration or data fix). Returns the new twin.

## Dashboard

### `GET /digital-twin/{user_id}/dashboard`

Aggregated view for the Student Twin Viewer page. Returns the twin state plus pre-computed display-friendly data:

```json
{
  "overall_health": "needs_attention",
  "dimension_summary": {
    "knowledge": { "score": 0.75, "confidence": 0.8 },
    "mastery": { "score": 0.81, "confidence": 0.9 },
    "misconceptions": { "active": 2, "resolved": 8 },
    "retention": { "score": 0.68, "confidence": 0.7 },
    "readiness": { "score": 0.78, "confidence": 0.75 },
    "interventions": { "active": 2, "completed": 5 }
  },
  "risk_indicators": [
    { "topic": "Cell Division", "type": "retention", "severity": "medium" },
    { "topic": "Photosynthesis", "type": "misconception", "severity": "high" }
  ],
  "last_built_at": "..."
}
```

The page is at `/digital-twin` with a user selector, showing dimension cards using the existing InsightCard pattern, plus risk indicators.

## File Map

| Action | Path |
|--------|------|
| Create | `src/core/digital_twin/__init__.py` |
| Create | `src/core/digital_twin/builder.py` |
| Create | `src/core/digital_twin/models.py` |
| Create | `src/core/digital_twin/events.py` |
| Create | `src/api/digital_twin.py` |
| Modify | `src/database/models.py` (add StudentDigitalTwin model) |
| Modify | `src/main.py` (register digital_twin router) |
| Modify | `dashboard/src/components/dashboard-v2/SidebarV2.tsx` (add Digital Twin link) |
| Create | `dashboard/src/app/digital-twin/page.tsx` |
| Create | `tests/test_digital_twin.py` |

## Test Plan

- **Builder unit:** `gather_knowledge_state()` returns correct structure from mock `StudentAbility`
- **Builder unit:** `gather_mastery_state()` returns correct structure from mock `StudentMastery`
- **Builder unit:** `compute_health()` returns correct health level based on dimension scores
- **Builder unit:** `compute_confidence()` returns 0-1 range with expected decay
- **Builder integration:** `rebuild()` upserts twin and returns complete state
- **Event unit:** handler calls `rebuild()` with correct user_id
- **API unit:** `GET /digital-twin/{id}` returns 200 with twin data
- **API unit:** `GET /digital-twin/{id}` returns 404 for missing twin
- **API unit:** `POST /digital-twin/{id}/rebuild` triggers rebuild
