Excellent. We have now built the backend intelligence foundation:

```text
Architecture Blueprint
        ↓
Learner Snapshot
        ↓
Recommendation Engine
        ↓
Adaptive Tutor
```

The next PRD is where EthioBio starts behaving like a true learning platform rather than an AI chat application.

---

# PRD — Continue Learning Experience & Proactive Guidance System

## Project: EthioBio AI Assistant

## Parent Initiative: Learning Intelligence Layer (LIL)

## Dependencies

* Learner Snapshot Builder
* Recommendation Engine
* Adaptive Tutoring Engine
* Recovery System
* Spaced Repetition System

## Status

Approved for Implementation

## Priority

Critical

## Type

Core Student Experience Layer

---

# Executive Summary

The Continue Learning System becomes the primary entry point into EthioBio.

Instead of asking:

> "What do you want to learn today?"

EthioBio proactively guides students toward their highest-value learning actions.

The system converts educational intelligence into a structured daily learning journey.

---

# Vision

Current experience:

```text
Student opens EthioBio

↓

Blank chat

↓

Student decides what to do
```

Future experience:

```text
Student opens EthioBio

↓

Continue Learning

↓

Recommended next actions

↓

Guided learning progression
```

---

# Core Principle

Every learner should immediately know:

> What should I do next?

without needing to ask.

---

# Problem Statement

Current systems know:

* weak topics
* mastery gaps
* misconceptions
* overdue reviews
* recovery plans

But these insights remain hidden.

Students must manually decide:

```text
What topic to study

What quiz to take

What review is due

What recovery task matters most
```

This increases friction and reduces engagement.

---

# Goals

Create:

```python
ContinueLearningFeed
```

that presents:

* prioritized recommendations
* recovery actions
* review actions
* tutor actions
* quiz actions

in a single guided experience.

---

# Non-Goals

This PRD does NOT:

* Replace dashboard
* Replace tutoring
* Replace recovery plans
* Replace SRS

It orchestrates them.

---

# Architecture

```text
Learner Snapshot
        ↓

Recommendation Engine
        ↓

Continue Learning Generator
        ↓

Dashboard
Telegram
Tutor
Mobile App
```

---

# New Module

```text
src/core/learning_intelligence/continue_learning/
```

Structure:

```text
continue_learning/

├── feed_generator.py

├── learning_journey_builder.py

├── action_grouping.py

├── progress_tracker.py

├── models/
│   ├── continue_learning_feed.py
│   ├── learning_card.py
│
└── tests/
```

---

# Core Domain Model

## ContinueLearningFeed

```python
class ContinueLearningFeed:

    user_id: UUID

    generated_at: datetime

    primary_action: LearningCard

    recommended_actions: list[LearningCard]

    recovery_actions: list[LearningCard]

    review_actions: list[LearningCard]

    achievement_actions: list[LearningCard]
```

---

# LearningCard

```python
class LearningCard:

    id: str

    title: str

    description: str

    action_type: str

    priority_score: float

    estimated_minutes: int

    xp_reward: int | None

    metadata: dict
```

---

# Feed Sections

## Section 1 — Primary Action

Always one item.

Highest-priority recommendation.

Example:

```text
Continue Learning

Review Genetics

Mastery is declining and review is overdue.

10 minutes
+20 XP
```

---

## Section 2 — Recovery Actions

Generated from:

```text
RecoveryPlan
RecoveryTask
```

Example:

```text
Recovery Progress

Cell Division

3 of 5 tasks completed

Next Task Available
```

---

## Section 3 — Due Reviews

Generated from:

```text
SpacedRepetitionSchedule
```

Example:

```text
Due Reviews

Genetics

Photosynthesis

Cell Structure
```

---

## Section 4 — Quiz Opportunities

Generated from:

```text
Weak Topics

Ability Estimates

Mastery Gaps
```

Example:

```text
Take Adaptive Quiz

Focus: Genetics

Estimated Time: 8 Minutes
```

---

## Section 5 — Tutor Actions

Generated from:

```text
Recommendations
```

Example:

```text
Ask Tutor

Clarify dominant gene misconceptions
```

---

# Learning Journey Builder

## Purpose

Transform recommendations into a guided sequence.

---

# Example

Instead of:

```text
10 recommendations
```

Generate:

```text
1. Review Genetics

2. Complete Recovery Task

3. Take Adaptive Quiz

4. Discuss with Tutor
```

This creates progression.

---

# Daily Learning Path

New concept:

```python
DailyLearningPath
```

Generated every day.

Contains:

```python
top_actions

estimated_duration

xp_available

completion_progress
```

---

# Progress Tracking

Track:

```text
Recommendations Completed

Reviews Completed

Recovery Tasks Completed

Quiz Completion
```

---

# Daily Completion Score

Example:

```text
Today's Learning Progress

7/10 actions completed

70%
```

---

# Gamification Integration

Each learning card can award:

```text
XP

Badges

Streak Progress
```

---

# New Achievements

Examples:

```text
Recommendation Follower

Recovery Champion

Review Master

Consistent Learner
```

---

# Dashboard Integration

New dashboard section:

```text
Continue Learning
```

Position:

```text
Top of Student Dashboard
```

Above:

```text
History

Reports

Achievements
```

---

# Telegram Integration

Generate proactive messages.

---

## Due Review Reminder

```text
You have 3 reviews due today.

Complete them to maintain mastery.
```

---

## Recovery Reminder

```text
Your Cell Division recovery plan is 80% complete.

One task remains.
```

---

## Learning Path Reminder

```text
Today's learning path is ready.

Estimated time: 20 minutes.
```

---

# Tutor Integration

After tutoring session:

Tutor receives:

```python
next_recommendation
```

Can suggest:

```text
Your next recommended action is a Genetics review.
```

---

# API Layer

New endpoints:

---

## Continue Learning Feed

```http
GET /intelligence/continue-learning
```

---

Response:

```json
{
  "primary_action": {},
  "recommended_actions": [],
  "review_actions": [],
  "recovery_actions": []
}
```

---

## Daily Learning Path

```http
GET /intelligence/daily-path
```

---

Response:

```json
{
  "estimated_duration": 20,

  "xp_available": 120,

  "actions": []
}
```

---

# Observability

Log:

```text
continue_learning_generated

daily_path_generated

recommendation_completed

learning_card_clicked

learning_card_completed
```

---

# Metrics

Track:

```text
Recommendation Completion Rate

Daily Path Completion Rate

Review Completion Rate

Recovery Completion Rate

Learning Session Starts

Daily Active Learners
```

---

# Testing Requirements

## Unit Tests

Validate:

* feed generation
* action prioritization
* journey building
* daily path creation

---

## Integration Tests

Validate:

* recommendation integration
* snapshot integration
* recovery integration
* SRS integration

---

## UX Tests

Validate:

Every learner receives:

```text
At least one actionable recommendation
```

and

```text
A complete learning path
```

---

# Acceptance Criteria

## Functional

* Continue Learning feed generated.
* Primary action always available.
* Recovery actions included.
* Due reviews included.
* Quiz opportunities included.
* Tutor actions included.

---

## Performance

Feed generation:

```text
<500ms
```

Cached retrieval:

```text
<100ms
```

---

## Architectural

* Consumes Recommendation Engine.
* Consumes Learner Snapshot.
* Does not create educational state.
* Centralized student guidance layer.

---

# Success Definition

EthioBio evolves from:

```text
Student asks questions when needed
```

to:

```text
Student follows a personalized learning journey every day
```

powered by:

```text
Learner Snapshot
        ↓

Recommendation Engine
        ↓

Adaptive Tutor
        ↓

Continue Learning
```

---

# Next PRD (Recommended)

After this, the next highest-leverage initiative is:

## Exam Readiness & Mastery Prediction Engine

This is where EthioBio starts predicting:

* readiness
* risk areas
* expected performance
* intervention urgency

and becomes a true academic guidance platform rather than only a tutoring platform.
