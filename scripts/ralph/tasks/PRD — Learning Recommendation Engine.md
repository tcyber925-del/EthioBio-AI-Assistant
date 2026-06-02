Here's the implementation-ready PRD for the next major component.

# PRD — Learning Recommendation Engine

## Project: EthioBio AI Assistant

## Parent Initiative: Learning Intelligence Layer (LIL)

## Dependency: Learner Snapshot Builder

## Status: Approved for Implementation

## Priority: Critical

## Type: Core Educational Intelligence Engine

---

# Executive Summary

The Learning Recommendation Engine transforms learner data into prioritized educational actions.

It is the first system responsible for answering:

> What should this learner do next?

The engine consumes a LearnerSnapshot and produces ranked recommendations that can be consumed by:

* Tutor Agent
* Continue Learning Dashboard
* Telegram Bot
* Recovery System
* Exam Readiness
* Future Teacher Intelligence
* Future Parent Intelligence

This is the decision-making layer of EthioBio.

---

# Problem Statement

EthioBio currently knows:

* mastery levels
* ability estimates
* misconceptions
* recovery plans
* due reviews
* educational memory
* engagement state

However, there is no centralized system that converts this information into actionable learning guidance.

Current state:

```text
Student Data
     ↓

Insights
     ↓

No Unified Decision Layer
```

Desired state:

```text
Student Data
      ↓

Learner Snapshot
      ↓

Recommendation Engine
      ↓

Prioritized Learning Actions
```

---

# Goal

Create a centralized recommendation engine that continuously determines the highest-value educational actions for each learner.

---

# Non-Goals

This project will NOT:

* replace mastery calculations
* replace recovery planning
* replace spaced repetition scheduling
* replace tutoring
* generate learning content
* create new educational storage systems

The engine only generates recommendations.

---

# Architecture

```text
Learner Snapshot
       ↓

Recommendation Engine
       ↓

Recommendation Service
       ↓

Consumers

├─ Tutor
├─ Dashboard
├─ Telegram
├─ Recovery
└─ Exam Readiness
```

---

# New Module

```text
src/core/learning_intelligence/recommendation/
```

Structure:

```text
recommendation/

├── models/
│   ├── recommendation.py
│   ├── action_type.py
│
├── rules/
│   ├── mastery_rules.py
│   ├── recovery_rules.py
│   ├── review_rules.py
│   ├── engagement_rules.py
│
├── scoring/
│   ├── priority_calculator.py
│
├── services/
│   ├── recommendation_engine.py
│   ├── recommendation_service.py
│
└── tests/
    ├── test_recommendation_engine.py
    ├── test_priority_calculator.py
```

---

# Core Domain Model

## LearningRecommendation

```python
class LearningRecommendation:
    id: str

    action_type: LearningActionType

    topic: str | None

    priority_score: float

    reason: str

    explanation: str

    generated_at: datetime

    metadata: dict
```

---

# Learning Action Types

```python
class LearningActionType(Enum):

    REVIEW_TOPIC = "review_topic"

    TAKE_QUIZ = "take_quiz"

    COMPLETE_RECOVERY_TASK = "complete_recovery_task"

    REVISE_MISCONCEPTION = "revise_misconception"

    STUDY_DIAGRAM = "study_diagram"

    READ_CONTENT = "read_content"

    ASK_TUTOR = "ask_tutor"

    EXAM_PRACTICE = "exam_practice"

    MAINTAIN_STREAK = "maintain_streak"
```

---

# Recommendation Sources

## Mastery Recommendations

Generated from:

```python
StudentMastery
```

Conditions:

```text
critical severity
moderate severity
rapid mastery decline
```

Examples:

```json
{
  "action": "REVIEW_TOPIC",
  "topic": "Genetics"
}
```

---

## Misconception Recommendations

Generated from:

```python
MisconceptionPattern
```

Conditions:

```text
frequency >= threshold
```

Example:

```json
{
  "action": "REVISE_MISCONCEPTION",
  "topic": "Genetics"
}
```

---

## Recovery Recommendations

Generated from:

```python
RecoveryPlan
RecoveryTask
```

Conditions:

```text
active recovery plan exists
unfinished tasks exist
```

Example:

```json
{
  "action": "COMPLETE_RECOVERY_TASK",
  "topic": "Cell Division"
}
```

---

## Review Recommendations

Generated from:

```python
SpacedRepetitionSchedule
```

Conditions:

```text
review due
review overdue
```

Example:

```json
{
  "action": "REVIEW_TOPIC",
  "topic": "Photosynthesis"
}
```

---

## Engagement Recommendations

Generated from:

```python
UserGamification
```

Conditions:

```text
streak at risk
activity declining
```

Example:

```json
{
  "action": "MAINTAIN_STREAK"
}
```

---

# Priority Scoring Engine

## Purpose

Rank recommendations by educational value.

---

# Scoring Formula

Initial implementation:

```python
priority_score = (
    mastery_score_weight
    + review_urgency_weight
    + misconception_weight
    + recovery_weight
    + engagement_weight
)
```

Normalize:

```python
0.0 → 1.0
```

---

# Weight Configuration

## Mastery Severity

```text
critical     +40
moderate     +25
mild         +10
good         +0
```

---

## Overdue Review

```text
1-3 days     +10
4-7 days     +20
8+ days      +30
```

---

## Misconceptions

```text
active misconception +20
```

---

## Recovery

```text
active plan +15

near completion +10
```

---

## Engagement

```text
streak risk +10

inactive learner +15
```

---

# Recommendation Limits

To prevent overload:

Maximum:

```python
TOP_RECOMMENDATIONS = 5
```

Return only highest-priority recommendations.

---

# Recommendation Engine

## File

```text
recommendation_engine.py
```

---

## Interface

```python
class RecommendationEngine:

    async def generate(
        self,
        snapshot: LearnerSnapshot
    ) -> list[LearningRecommendation]:
        ...
```

---

# Generation Pipeline

```text
Snapshot
    ↓

Generate Mastery Actions
    ↓

Generate Recovery Actions
    ↓

Generate Review Actions
    ↓

Generate Misconception Actions
    ↓

Generate Engagement Actions
    ↓

Calculate Priorities
    ↓

Sort Descending
    ↓

Return Top 5
```

---

# Recommendation Service

## Purpose

Single access point.

No component may instantiate the engine directly.

---

## Interface

```python
class RecommendationService:

    async def get_recommendations(
        self,
        user_id: UUID
    ) -> list[LearningRecommendation]:
        ...
```

---

# Caching

Cache recommendations separately.

Key:

```text
recommendations:{user_id}
```

TTL:

```text
5 minutes
```

---

# Invalidation Events

Invalidate recommendations when:

```text
Quiz completed

Recovery task completed

Recovery plan completed

Review submitted

Memory summary updated

Snapshot invalidated
```

---

# APIs

New module:

```text
src/api/intelligence/
```

---

## Get Recommendations

```http
GET /intelligence/recommendations
```

Response:

```json
[
  {
    "action_type": "REVIEW_TOPIC",
    "topic": "Genetics",
    "priority_score": 0.95,
    "reason": "critical mastery and overdue review"
  }
]
```

---

## Get Next Action

```http
GET /intelligence/next-action
```

Returns:

```json
{
  "action_type": "REVIEW_TOPIC",
  "topic": "Genetics",
  "priority_score": 0.95
}
```

Returns only highest-priority recommendation.

---

# Tutor Integration Contract

Future PRD dependency.

Tutor receives:

```python
top_recommendations
```

Example:

```json
[
  {
    "action_type": "REVISE_MISCONCEPTION",
    "topic": "Genetics"
  }
]
```

Tutor adapts explanation strategy accordingly.

---

# Continue Learning Contract

Dashboard consumes:

```http
GET /intelligence/recommendations
```

to render:

```text
Continue Learning

1. Review Genetics
2. Complete Recovery Task
3. Practice Cell Division
```

---

# Telegram Integration Contract

Examples:

```text
You have 2 overdue reviews.

Continue your Genetics recovery plan.

Your Biology mastery increased by 8%.
```

Generated from recommendation output.

---

# Observability

Log:

```text
recommendation_generation_started

recommendation_generation_completed

recommendation_cache_hit

recommendation_cache_miss

recommendation_generation_failed
```

---

# Metrics

Track:

```text
recommendations_generated

top_action_distribution

recommendation_click_rate

recommendation_completion_rate

cache_hit_rate

generation_time
```

---

# Testing Requirements

## Unit Tests

Validate:

* mastery recommendations
* review recommendations
* recovery recommendations
* misconception recommendations
* engagement recommendations

---

## Priority Tests

Validate:

* critical mastery outranks mild mastery
* overdue reviews outrank normal reviews
* misconception interventions rank correctly

---

## Service Tests

Validate:

```python
RecommendationService
```

returns expected recommendations.

---

## API Tests

Validate:

```http
GET /intelligence/recommendations

GET /intelligence/next-action
```

---

# Acceptance Criteria

## Functional

* Recommendations generated from LearnerSnapshot.
* Recommendations ranked by priority.
* Top recommendation always available.
* Maximum 5 recommendations returned.
* All recommendation sources integrated.

---

## Performance

* Cached response <100ms.
* Fresh generation <1 second.
* Recommendation cache hit rate >80%.

---

## Architectural

* No new educational source of truth.
* Consumes LearnerSnapshot only.
* Centralized recommendation generation.
* Reusable across all EthioBio surfaces.

---

# Success Definition

EthioBio transitions from:

```text
Knowing the learner's state
```

to:

```text
Actively guiding the learner's next best action.
```

This PRD establishes the decision-making core of the Learning Intelligence Layer and becomes the foundation for Tutor Personalization, Continue Learning, Exam Readiness, Teacher Intelligence, and Parent Intelligence.
