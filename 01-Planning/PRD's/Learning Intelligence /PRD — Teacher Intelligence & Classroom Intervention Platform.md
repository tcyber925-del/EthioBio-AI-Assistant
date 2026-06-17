# PRD — Teacher Intelligence & Classroom Intervention Platform

## Project

EthioBio AI Assistant

## Parent Initiative

Learning Intelligence Layer (LIL)

## Dependencies

* Learner Snapshot Builder
* Recommendation Engine
* Adaptive Tutoring Engine
* Continue Learning System
* Exam Readiness Engine
* Existing `ClassGroup` + `ClassEnrollment` DB models
* Existing `UserRole.teacher` enum value

## Status

Approved for Implementation

## Priority

Strategic / High

## Type

Teacher Intelligence Platform

---

# Executive Summary

The Teacher Intelligence Platform transforms EthioBio from an individual tutoring system into a classroom intelligence system.

Teachers gain visibility into:
* classroom readiness
* mastery gaps
* misconceptions
* learning risks
* intervention priorities
* classroom performance trends

Instead of manually identifying struggling students, EthioBio continuously surfaces the highest-impact interventions.

---

# Core Principle

The system must answer:

> Which students need attention right now?

and

> What intervention will have the highest educational impact?

---

# Problem Statement

Teachers currently lack:

* Real-time mastery visibility
* Misconception visibility
* Readiness forecasting
* Intervention prioritization
* Classroom-level analytics

As student counts grow, manual tracking becomes impossible.

---

# Goals

Create a classroom intelligence layer that provides:
* classroom health scoring
* student risk analysis
* readiness distribution
* intervention recommendations
* mastery heatmap

---

# Non-Goals

This PRD will NOT:
* replace grading systems
* replace LMS platforms
* replace school SIS systems
* replace classroom instruction
* implement full auth/identity system (teacher identity is assumed via existing role)

It augments teacher decision-making.

---

# Architecture Decisions

## Classroom CRUD (baked in, not deferred)

The `ClassGroup` and `ClassEnrollment` DB models exist but have zero API endpoints. Without classroom CRUD, the intelligence layer has no students to analyze. Minimal classroom management is included:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST   | /teacher/classrooms | Create a class with student IDs |
| GET    | /teacher/classrooms | List teacher's classes (id, name, student count) |
| GET    | /teacher/classrooms/{id} | Roster — student list with readiness summary |
| POST   | /teacher/classrooms/{id}/enroll | Add students to an existing class |

No update/delete endpoints for MVP.

## Student Identity

Students are identified by UUID-truncated labels ("Student #abc12345"), matching the existing dashboard convention. A `display_name` field on `StudentProfile` is deferred as a future enhancement.

## Module Architecture

Single `TeacherService` pattern (matching `ReadinessService`, `RecommendationService`). Internally composes sub-detectors as private methods — not separate engine files.

## Intervention Model

Reuses `Intervention` from the readiness module (`src/core/learning_intelligence/readiness/models/intervention.py`). No new model created.

## Risk Detection

Reuses `ReadinessService.get_readiness()` per-student. Risk students = those with `readiness_band == "Critical"` plus any with `risk_topics`. Engagement risk approximated from `GamificationSummary.recent_activity_score`. Richer cross-student detection deferred to a future phase.

---

# User Stories

## TI-001 — Classroom CRUD API + Domain Models

**As a** teacher  
**I want** to create classes and enroll students via API  
**So that** the classroom intelligence layer has students to analyze.

### Acceptance Criteria
1. ClassroomProfile and StudentRisk Pydantic models created under `src/core/learning_intelligence/teacher/models/`
2. ClassroomProfile has: classroom_id, generated_at, total_students, average_readiness, readiness_distribution (dict per band), risk_students list, intervention_candidates list, mastery_heatmap dict
3. StudentRisk has: student_id, readiness_score, risk_level, risk_factors list, recommended_action
4. POST /teacher/classrooms creates a ClassGroup with teacher_id from request context (accepts name, grade_level, student_ids)
5. GET /teacher/classrooms returns list of teacher's classes with student count
6. GET /teacher/classrooms/{id} returns roster with each student's readiness summary
7. POST /teacher/classrooms/{id}/enroll accepts student_ids list and enrolls them
8. All endpoints return appropriate errors for non-existent classrooms/users
9. Typecheck passes
10. Tests pass

## TI-002 — TeacherService: Aggregation & Risk

**As a** teacher  
**I want** the system to aggregate my classroom's readiness data  
**So that** I see classroom-level intelligence without checking each student individually.

### Acceptance Criteria
1. `TeacherService` at `src/core/learning_intelligence/teacher/teacher_service.py`
2. `get_classroom_overview(classroom_id, teacher_id)` returns ClassroomProfile
3. Calls ReadinessService.get_readiness() for each enrolled student in parallel
4. Computes classroom_health score (0-100) = average of all student readiness scores
5. Builds readiness_distribution: count of students per readiness band (Critical/Developing/Ready/Strong)
6. Identifies risk_students: any student with readiness < 40 (Critical band) or having risk_topics
7. Gathers intervention_candidates: collects Intervention from each student's readiness profile
8. Computes mastery_heatmap: topic → average readiness_score across all students
9. Degrades gracefully when any student has no readiness data (skips them)
10. Typecheck passes
11. Tests pass

## TI-003 — Classroom Intelligence API Endpoints

**As a** teacher  
**I want** to fetch classroom intelligence via API  
**So that** the dashboard can display it.

### Acceptance Criteria
1. GET /teacher/classrooms/{id}/overview returns ClassroomProfile JSON
2. Response includes: classroom_health, readiness_distribution, risk_students list, mastery_heatmap, intervention_candidates
3. GET /teacher/classrooms/{id}/risk-students returns filtered list of StudentRisk with readiness < 40
4. GET /teacher/classrooms/{id}/interventions returns sorted intervention_candidates (highest priority first)
5. GET /teacher/classrooms/{id}/mastery-heatmap returns topic → average_score dict
6. Router lives at src/api/teacher.py with APIRouter(prefix="/teacher")
7. Router is imported and app.include_router'd in src/main.py
8. /teacher/:path* rewrite added to dashboard/next.config.js
9. Typecheck passes

## TI-004 — Classroom Overview Dashboard Page

**As a** teacher  
**I want** a classroom overview page in the dashboard  
**So that** I see health scores, risk students, and heatmaps at a glance.

### Acceptance Criteria
1. `/classroom/[id]` page at `dashboard/src/app/classroom/[id]/page.tsx`
2. Fetches from `/teacher/classrooms/{id}/overview`
3. Displays classroom_health as a large percentage with colored badge
4. Shows readiness_distribution as counts per band (Critical/Developing/Ready/Strong)
5. Lists risk_students with readiness score and risk level badges
6. Shows mastery_heatmap as a topic-score grid
7. Loading skeleton during fetch
8. Error state with retry button
9. Empty state when no data
10. Sidebar link to /classroom route (placeholder until teacher selects a class)
11. Typecheck passes

## TI-005 — Intervention Queue Widget

**As a** teacher  
**I want** to see a prioritized intervention queue for my classroom  
**So that** I know which action to take first.

### Acceptance Criteria
1. Intervention queue widget in the classroom overview page showing the intervention_candidates list
2. Each item shows: student label, topic, action_type, priority, estimated_impact
3. Sorted by priority descending
4. Empty state: "No interventions needed — all students on track"
5. Typecheck passes

## TI-006 — Teacher Ownership Guard

**As a** system  
**I want** to ensure a teacher can only access their own classrooms  
**So that** teachers cannot see or modify other teachers' classrooms.

### Acceptance Criteria
1. A reusable `_verify_teacher_owns_classroom(session, classroom_id, teacher_id)` helper
2. Checks that the ClassGroup's teacher_id matches the requesting teacher_id
3. Returns 404 (not 403) on mismatch to avoid leaking classroom existence
4. Applied to all classroom intelligence endpoints
5. Applied to classroom CRUD endpoints
6. Typecheck passes

---

# New Module Structure

```
src/core/learning_intelligence/teacher/
├── teacher_service.py
├── models/
│   ├── classroom_profile.py
│   └── __init__.py
├── __init__.py
└── tests/
```

# API Layer

```
POST   /teacher/classrooms
GET    /teacher/classrooms
GET    /teacher/classrooms/{id}
POST   /teacher/classrooms/{id}/enroll
GET    /teacher/classrooms/{id}/overview
GET    /teacher/classrooms/{id}/risk-students
GET    /teacher/classrooms/{id}/interventions
GET    /teacher/classrooms/{id}/mastery-heatmap
```

# Observability

Log:
* classroom_profile_generated
* student_risk_detected
* intervention_generated
* teacher_dashboard_loaded
* heatmap_generated

# Success Definition

EthioBio evolves from:

```
AI Tutor
```

to:

```
Learning Intelligence Platform
```

serving:
* Students
* Teachers

and laying the foundation for:
* Parent Intelligence
* School Intelligence
* Regional Learning Analytics
* Ministry/Institution Reporting

without requiring another major architectural redesign.
