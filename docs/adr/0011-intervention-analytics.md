# Intervention Analytics — Persistent Assignments and Effectiveness Measurement

The Intervention Analytics module (Wave 5) introduces a persisted `InterventionAssignment` model, CRUD API, outcome measurement via pre/post mastery comparison, and analytics aggregation. The existing `InterventionPlanner` is now wired to persist its computed interventions as actionable records.

**Status:** accepted

## Context

The existing `InterventionPlanner` at `src/core/learning_intelligence/readiness/intervention_planner.py` computed intervention recommendations on-the-fly as read-only Pydantic models — never persisted, never tracked, no lifecycle. The `InterventionEntity` schema at `src/schemas/entities.py` had the right shape but was not backed by a database model or wired to any endpoint. Multiple downstream consumers (teacher copilot `intervention_guidance` intent, classroom overview, school dashboard) reference intervention data that doesn't exist.

## Decision

1. **`InterventionAssignment` DB model** at `src/database/models.py`: Full lifecycle tracking with `status` (planned/active/completed/cancelled), `priority`, `estimated_impact`, and `effectiveness_score`. Linked to `User`, optionally to `Classroom` and `Teacher`.

2. **`InterventionService`** at `src/core/intervention/service.py`: CRUD operations plus:
   - `persist_planned()` — Accepts `InterventionPlanner` output and creates DB records
   - `compute_effectiveness()` — Queries `StudentMastery` records before and after the intervention's `assigned_at` date; the difference in `average_score` becomes the effectiveness score (clamped 0-100)
   - `get_analytics()` — Aggregates completion rates, average effectiveness, and breakdowns by intervention_type and topic

3. **REST API** at `src/api/intervention.py`: 7 endpoints covering create, read, update, list (by user/classroom/status), effectiveness computation, analytics summary, and bulk creation from readiness analysis.

4. **Dashboard** at `dashboard/src/app/interventions/`: Full CRUD UI with analytics cards, effectiveness bar charts by type/topic, and a "From Readiness" button that calls `InterventionPlanner` and persists the results.

## Consequences

- Interventions are now durable records with lifecycle. Teachers can assign, track, and measure outcomes.
- Effectiveness measurement requires pre-existing `StudentMastery` data. New students with no history will have `null` effectiveness until they complete enough assessments.
- The analytics endpoint returns computed-on-read aggregations (no materialized views). For large-scale deployments, a nightly rollup would be needed.
- The `InterventionAssignment` table is append-only for completed records — historical effectiveness data is preserved even if the student's mastery changes later.
- This does NOT replace `RecoveryPlan`/`RecoveryTask` — those are student-facing remediation plans. `InterventionAssignment` is teacher-facing analytics.
