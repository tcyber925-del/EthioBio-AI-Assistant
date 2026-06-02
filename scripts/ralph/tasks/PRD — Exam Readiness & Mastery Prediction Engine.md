# PRD — Exam Readiness & Mastery Prediction Engine

## Project: EthioBio AI Assistant

## Parent Initiative: Learning Intelligence Layer (LIL)

## Dependencies

* Learner Snapshot Builder
* Recommendation Engine
* Adaptive Tutoring Engine
* Continue Learning System
* StudentMastery
* StudentAbility (IRT/Bayesian Ability)
* Spaced Repetition System
* Recovery Planning System

## Status

Approved for Implementation

## Priority

High

## Type

Predictive Educational Intelligence

---

# Executive Summary

The Exam Readiness & Mastery Prediction Engine is EthioBio's first predictive educational system.

Current systems describe:

```text
What the learner has done
```

This system predicts:

```text
What the learner is likely to achieve
```

It continuously evaluates:

* readiness for exams
* topic-level risk
* mastery stability
* forgetting risk
* intervention urgency
* probability of success

and converts educational data into actionable academic forecasts.

---

# Vision

Current EthioBio:

```text
Reactive Learning System
```

Future EthioBio:

```text
Predictive Learning Intelligence Platform
```

---

# Core Principle

The system should answer:

> If the student took an exam today, how prepared are they?

and

> What should be improved before the exam?

---

# Problem Statement

EthioBio currently tracks:

* mastery
* ability
* quizzes
* misconceptions
* reviews
* recovery plans

However it cannot answer:

```text
Is the student exam-ready?

Which topics are highest risk?

Which interventions matter most?

How likely is mastery regression?
```

Students, parents, and teachers need predictive insights.

---

# Goals

Create:

```python
ExamReadinessProfile
```

that predicts:

* overall readiness
* topic readiness
* risk topics
* confidence level
* intervention priorities
* projected performance

---

# Non-Goals

This PRD will NOT:

* replace mastery calculations
* replace IRT ability calculations
* replace quizzes
* replace recommendation engine
* guarantee exam outcomes

The engine provides probabilistic educational guidance.

---

# Architecture

```text
Learner Snapshot
        ↓

Readiness Engine
        ↓

Prediction Models
        ↓

Risk Analysis
        ↓

Readiness Profile
        ↓

Dashboard
Tutor
Recommendations
Teacher Reports
Parent Reports
```

---

# New Module

```text
src/core/learning_intelligence/readiness/
```

Structure:

```text
readiness/

├── readiness_engine.py

├── readiness_calculator.py

├── risk_analyzer.py

├── mastery_predictor.py

├── forgetting_risk.py

├── intervention_planner.py

├── models/
│   ├── readiness_profile.py
│   ├── topic_readiness.py
│   ├── intervention.py
│
└── tests/
```

---

# Core Domain Models

## ExamReadinessProfile

```python
class ExamReadinessProfile:

    user_id: UUID

    generated_at: datetime

    overall_readiness: float

    readiness_band: str

    confidence_score: float

    projected_exam_score: float

    topic_readiness: list[TopicReadiness]

    risk_topics: list[str]

    recommended_interventions: list[Intervention]
```

---

## TopicReadiness

```python
class TopicReadiness:

    topic: str

    readiness_score: float

    mastery_score: float

    ability_score: float

    confidence_score: float

    risk_level: str

    review_status: str
```

---

## Intervention

```python
class Intervention:

    topic: str

    priority: float

    action_type: str

    estimated_impact: float

    reason: str
```

---

# Readiness Scoring Engine

## Purpose

Compute exam readiness from multiple educational signals.

---

# Inputs

## Mastery

Source:

```text
StudentMastery
```

Weight:

```text
40%
```

---

## Ability

Source:

```text
StudentAbility
```

Weight:

```text
25%
```

---

## Spaced Repetition

Source:

```text
SpacedRepetitionSchedule
```

Weight:

```text
15%
```

---

## Recovery Progress

Source:

```text
RecoveryPlan
```

Weight:

```text
10%
```

---

## Misconceptions

Source:

```text
MisconceptionPattern
```

Weight:

```text
10%
```

---

# Formula

Initial implementation:

```python
readiness_score =
(
    mastery_component +
    ability_component +
    retention_component +
    recovery_component -
    misconception_penalty
)
```

Normalize:

```python
0 → 100
```

---

# Readiness Bands

## Critical

```text
0-39
```

Meaning:

```text
High risk of failure
```

---

## Developing

```text
40-59
```

Meaning:

```text
Significant preparation required
```

---

## Ready

```text
60-79
```

Meaning:

```text
Reasonably prepared
```

---

## Strong

```text
80-100
```

Meaning:

```text
Exam-ready
```

---

# Topic-Level Readiness

Generated for every tracked topic.

Example:

```json
{
  "topic": "Genetics",

  "readiness_score": 42,

  "risk_level": "high",

  "review_status": "overdue"
}
```

---

# Risk Analysis Engine

## Purpose

Identify academic danger zones.

---

# Risk Categories

## Knowledge Risk

Triggered when:

```text
Mastery < threshold
```

---

## Retention Risk

Triggered when:

```text
Reviews overdue
```

---

## Misconception Risk

Triggered when:

```text
Persistent misconception frequency high
```

---

## Engagement Risk

Triggered when:

```text
Low activity
Declining streak
```

---

## Ability Risk

Triggered when:

```text
Ability estimate low
Uncertainty high
```

---

# Risk Levels

```python
LOW

MODERATE

HIGH

CRITICAL
```

---

# Mastery Stability Predictor

## Purpose

Estimate likelihood of future mastery decline.

---

# Signals

Uses:

```text
Review consistency

Mastery trend

Ability trend

Recovery completion
```

---

# Output

Example:

```json
{
  "topic": "Photosynthesis",

  "stability_score": 0.88
}
```

Meaning:

```text
Mastery likely stable
```

---

# Forgetting Risk Engine

## Purpose

Predict forgetting probability.

---

# Inputs

```text
Days overdue

Ease factor

Review count

Mastery score
```

---

# Output

```json
{
  "topic": "Cell Division",

  "forgetting_risk": 0.74
}
```

---

# Projected Exam Score

## Purpose

Estimate current exam performance.

---

# Inputs

```text
Mastery

Ability

Topic coverage

Readiness
```

---

# Output

```json
{
  "projected_exam_score": 72.5
}
```

---

# Intervention Planner

## Purpose

Generate highest-impact actions.

---

# Example

Input:

```text
Critical readiness

Overdue reviews

Misconception present
```

Output:

```json
{
  "topic": "Genetics",

  "action": "REVISE_MISCONCEPTION",

  "estimated_impact": 12.5
}
```

---

# Integration with Recommendation Engine

Recommendations gain new signals.

---

Example:

Before:

```text
Review Genetics
```

After:

```text
Review Genetics

High Exam Impact
```

---

# Tutor Integration

Tutor receives:

```python
ReadinessContext
```

Example:

```json
{
  "overall_readiness": 58,

  "risk_topics": [
    "Genetics",
    "Cell Division"
  ]
}
```

---

Tutor can say:

```text
This topic is currently one of your highest-risk exam areas.
```

---

# Continue Learning Integration

Learning Path prioritizes:

```text
High-impact interventions
```

before lower-value actions.

---

# Dashboard Experience

New dashboard section:

```text
Exam Readiness
```

---

## Overview Card

Example:

```text
Exam Readiness

72%

READY
```

---

## Topic Breakdown

```text
Genetics ........ 42%

Photosynthesis .. 81%

Ecology ......... 74%
```

---

## Risk Areas

```text
Highest Risk Topics

1. Genetics

2. Cell Division

3. DNA Replication
```

---

# API Layer

## Get Readiness Profile

```http
GET /intelligence/readiness
```

---

Response:

```json
{
  "overall_readiness": 72,

  "readiness_band": "ready",

  "projected_exam_score": 75,

  "risk_topics": []
}
```

---

## Topic Readiness

```http
GET /intelligence/readiness/topics
```

---

Response:

```json
[
  {
    "topic": "Genetics",

    "readiness_score": 42
  }
]
```

---

# Observability

Log:

```text
readiness_generated

readiness_requested

risk_topic_detected

intervention_generated

prediction_completed
```

---

# Metrics

Track:

```text
Readiness Distribution

Risk Topic Frequency

Intervention Acceptance Rate

Readiness Improvement Rate

Projected Score Trend

Prediction Confidence Trend
```

---

# Testing Requirements

## Unit Tests

Validate:

* readiness calculation
* risk analysis
* forgetting prediction
* intervention generation

---

## Integration Tests

Validate:

* snapshot integration
* recommendation integration
* tutor integration
* dashboard integration

---

## Regression Tests

Validate:

* readiness score stable
* scoring reproducible
* risk levels correct

---

# Acceptance Criteria

## Functional

* Readiness profile generated.
* Topic readiness generated.
* Risk topics identified.
* Interventions generated.
* Projected exam score available.

---

## Performance

Readiness generation:

```text
<1 second
```

Cached retrieval:

```text
<100ms
```

---

## Architectural

* Consumes Learner Snapshot.
* Does not create new educational state.
* Reuses existing educational systems.
* Integrates with recommendations and tutoring.

---

# Success Definition

EthioBio evolves from:

```text
Personalized tutoring
```

to:

```text
Predictive academic guidance
```

where the platform can:

* estimate readiness,
* identify risk before failure,
* prioritize interventions,
* forecast outcomes,
* guide learners toward exam success.

---

## Recommended Next Major PRD

After this, the highest-leverage initiative is:

### Teacher Intelligence & Classroom Intervention Platform

This would elevate EthioBio from a learner-centric system into a multi-stakeholder educational platform, enabling teachers to monitor readiness, mastery gaps, risk clusters, intervention opportunities, and classroom-wide learning trends.
