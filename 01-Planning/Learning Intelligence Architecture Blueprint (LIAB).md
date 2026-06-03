# Learning Intelligence Architecture Blueprint (LIAB)

## Project: EthioBio AI Assistant

## Status: Architecture Approved

## Priority: Critical

## Type: Core Educational Intelligence Layer

---

# 1. Executive Summary

EthioBio already possesses strong educational foundations:

* Curriculum RAG
* Tutoring System
* Educational Memory
* Mastery Tracking
* IRT Ability Modeling
* Recovery Planning
* Spaced Repetition
* Gamification

However, these systems currently operate largely as independent educational subsystems.

The next architectural evolution is not a Learner State Engine rewrite.

Instead, EthioBio should introduce a centralized:

```text
Learning Intelligence Layer (LIL)
```

whose purpose is to transform educational data into educational decisions.

---

# Vision

Move EthioBio from:

```text
AI Tutor
```

to:

```text
Adaptive Learning Intelligence Platform
```

---

# Core Principle

Every educational interaction should answer:

> What is the best next learning action for this student?

---

# 2. Current Architecture

## Existing Educational Data Layer

Already Implemented

### Quiz Intelligence

```text
QuizAttempt
QuestionAttempt
Question Difficulty
```

---

### Mastery Intelligence

```text
StudentMastery
StudentAbility
TopicMasteryHistory
MisconceptionPattern
```

---

### Recovery Intelligence

```text
RecoveryPlan
RecoveryTask
RecoveryNotification
```

---

### Retention Intelligence

```text
SpacedRepetitionSchedule
```

---

### Educational Memory

```text
EducationalSummary
Misconceptions
Understanding Level
Confidence
Learning Goals
```

---

### Engagement Intelligence

```text
UserGamification
Streaks
XP
Levels
```

---

# Existing Problem

Current architecture:

```text
Quiz
Recovery
SRS
Tutor
Memory
Gamification

operate independently
```

Result:

```text
Fragmented educational decision-making
```

---

# Desired Architecture

```text
Learning Events
        ↓

Educational State
        ↓

Learning Intelligence Layer
        ↓

Recommendations
        ↓

Tutor
Recovery
Dashboard
Telegram
Exams
```

---

# 3. Core Domain Model

The primary entity of EthioBio becomes:

```text
Learner Progress
```

Everything exists to improve learner progress.

Not:

```text
Conversation
Quiz
Recovery Plan
```

Those become supporting mechanisms.

---

# 4. Learning Intelligence Layer

New Module:

```text
src/core/learning_intelligence/
```

Structure:

```text
learning_intelligence/

├── snapshot/
│   ├── learner_snapshot.py
│   ├── snapshot_builder.py
│
├── recommendation/
│   ├── recommendation_engine.py
│   ├── action_prioritizer.py
│
├── tutor/
│   ├── tutor_context_adapter.py
│
├── readiness/
│   ├── exam_readiness_engine.py
│
├── models/
│   ├── learner_snapshot.py
│   ├── recommendation.py
│   ├── learning_action.py
│
└── services/
    ├── intelligence_service.py
```

---

# 5. Learner Snapshot Builder

## Purpose

Provide a unified educational profile.

---

## Important Rule

LearnerSnapshot is:

```text
Computed
Read-only
Non-persistent
```

It is NOT:

```text
Database Table
New Source of Truth
```

---

## Inputs

### StudentMastery

Provides:

```text
Average Score
Confidence
Severity
```

---

### StudentAbility

Provides:

```text
Ability Score
Uncertainty
```

---

### MisconceptionPattern

Provides:

```text
Known Misconceptions
Frequency
```

---

### Recovery Plans

Provides:

```text
Active Recovery
Progress
```

---

### Spaced Repetition

Provides:

```text
Due Reviews
Retention Signals
```

---

### Educational Memory

Provides:

```text
Understanding Level
Learning Goals
Tutor Observations
```

---

### Gamification

Provides:

```text
Streaks
Engagement
XP
```

---

## Output Model

```python
LearnerSnapshot
```

Contains:

```python
user_id

mastery_by_topic

ability_by_topic

misconceptions

weak_topics

strong_topics

active_recovery_plans

due_reviews

educational_memory

engagement_metrics

learning_goals

gamification_state
```

---

# 6. Recommendation Engine

## Purpose

Answer:

> What should this learner do next?

---

## Input

```python
LearnerSnapshot
```

---

## Output

```python
LearningRecommendation
```

---

## Example

```json
{
  "priority": 0.95,
  "action": "REVIEW_TOPIC",
  "topic": "Genetics",
  "reason": "Critical mastery and overdue review"
}
```

---

# Recommendation Categories

```python
REVIEW_TOPIC

TAKE_QUIZ

COMPLETE_RECOVERY_TASK

STUDY_DIAGRAM

EXAM_PRACTICE

ASK_TUTOR

READ_CONTENT

REVISE_MISCONCEPTION
```

---

# Recommendation Priority Factors

## Mastery Severity

Weight:

```text
High
```

---

## Review Overdue

Weight:

```text
High
```

---

## Active Misconceptions

Weight:

```text
High
```

---

## Recovery Progress

Weight:

```text
Medium
```

---

## Engagement Risk

Weight:

```text
Medium
```

---

## Exam Proximity

Weight:

```text
High
```

Future phase.

---

# 7. Tutor Learner Awareness

## Current State

Tutor receives:

```text
Memory Context
Retrieved Curriculum Context
```

---

## Future State

Tutor receives:

```text
Memory Context

Curriculum Context

Learner Snapshot Summary
```

---

## Example Tutor Context

```text
Grade: 10

Weak Topics:
- Genetics
- Cell Division

Known Misconceptions:
- Dominant Gene Confusion

Confidence:
Low

Recommended Difficulty:
Beginner
```

---

# Expected Outcome

Tutor explanations become:

```text
Personalized
Adaptive
Progress-Aware
```

instead of merely context-aware.

---

# 8. Continue Learning System

## Purpose

Provide a single educational starting point.

---

## Dashboard Widget

```text
Continue Learning

1. Review Genetics
2. Complete Recovery Task
3. Take Adaptive Quiz
4. Practice Cell Diagram
```

Generated entirely from recommendations.

---

## Telegram Integration

Examples:

```text
You have 2 overdue reviews.

Complete Genetics Recovery Task #3.

Your Ecology mastery improved by 12%.
```

---

# 9. Educational Intelligence API

New API Module:

```text
src/api/intelligence/
```

---

## Endpoints

### Learner Snapshot

```http
GET /intelligence/snapshot
```

---

### Recommendations

```http
GET /intelligence/recommendations
```

---

### Next Action

```http
GET /intelligence/next-action
```

---

### Readiness

```http
GET /intelligence/readiness
```

Future phase.

---

# 10. Exam Readiness Engine (Phase 2)

Not implemented initially.

Depends on:

```text
Learner Snapshot
Recommendation Engine
```

being stable.

---

## Inputs

```text
StudentMastery

StudentAbility

Misconceptions

Recovery Completion

Review Completion
```

---

## Outputs

```json
{
  "overall_readiness": 0.74,

  "weak_topics": [],

  "risk_topics": []
}
```

---

# 11. Architectural Rules

## Rule 1

Do NOT create:

```text
LearnerState Table
```

---

## Rule 2

Do NOT replace:

```text
StudentMastery
StudentAbility
RecoveryPlan
```

---

## Rule 3

Do NOT rewrite existing systems.

---

## Rule 4

Learning Intelligence consumes existing systems.

Existing systems remain authoritative.

---

## Rule 5

Tutor must never directly query dozens of educational models.

Always use:

```python
LearnerSnapshot
```

---

## Rule 6

Future educational features must integrate through:

```text
Learning Intelligence Layer
```

not create parallel educational decision engines.

---

# 12. Implementation Roadmap

## Phase 1

### Learner Snapshot Builder

Duration:

```text
1 Week
```

---

Deliverables:

```text
LearnerSnapshot model

SnapshotBuilder

Snapshot API
```

---

## Phase 2

### Recommendation Engine

Duration:

```text
1–2 Weeks
```

---

Deliverables:

```text
Action Prioritizer

Recommendation Engine

Recommendations API
```

---

## Phase 3

### Tutor Learner Awareness

Duration:

```text
1 Week
```

---

Deliverables:

```text
Tutor Context Adapter

Snapshot Injection

Personalized Tutor Behavior
```

---

## Phase 4

### Continue Learning

Duration:

```text
1 Week
```

---

Deliverables:

```text
Dashboard Widget

Telegram Recommendations

Proactive Guidance
```

---

## Phase 5

### Exam Readiness

Duration:

```text
2 Weeks
```

---

Deliverables:

```text
Readiness Engine

Readiness API

Exam Dashboard
```

---

# Success Criteria

EthioBio should evolve from:

```text
Answering educational questions
```

to:

```text
Understanding the learner

Predicting educational needs

Recommending optimal actions

Guiding mastery progression
```

The Learning Intelligence Layer becomes the central educational brain that coordinates all existing educational systems while preserving the current architecture and avoiding large-scale refactoring.
