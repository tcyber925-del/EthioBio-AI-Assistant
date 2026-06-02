Perfect. Now we move from **decision intelligence** to **adaptive tutoring intelligence**.

This is where learners will start feeling the difference between:

```text
A chatbot that answers questions
```

and

```text
A personalized AI learning companion
```

---

# PRD — Tutor Learner Awareness & Adaptive Tutoring Engine

## Project: EthioBio AI Assistant

## Parent Initiative: Learning Intelligence Layer (LIL)

## Dependencies

* Learner Snapshot Builder
* Learning Recommendation Engine
* Educational Memory System
* Tutor Graph

## Status

Approved for Implementation

## Priority

Critical

## Type

Core Personalization Infrastructure

---

# Executive Summary

The Adaptive Tutoring Engine transforms the existing tutor from a context-aware system into a learner-aware system.

Currently the tutor receives:

```text
Conversation Context
+
Curriculum Retrieval Context
+
Memory Context
```

After implementation the tutor will receive:

```text
Conversation Context
+
Curriculum Retrieval Context
+
Memory Context
+
Learner Snapshot
+
Learning Recommendations
```

This enables personalized teaching strategies, adaptive difficulty, misconception remediation, and progress-aware tutoring.

---

# Problem Statement

Today the tutor can answer educational questions.

However it does not consistently know:

```text
What topics the student struggles with

What misconceptions repeatedly occur

What recovery plans are active

What reviews are overdue

What difficulty level is appropriate

What educational action should happen next
```

As a result:

```text
Every learner receives roughly the same tutoring behavior
```

regardless of mastery level.

---

# Goal

Create a learner-aware tutoring system that adapts explanations, questioning, guidance, and recommendations to the learner's educational state.

---

# Non-Goals

This PRD will NOT:

* Replace RAG
* Replace educational memory
* Replace recommendation engine
* Replace mastery calculations
* Replace recovery planning
* Generate new learner state

The tutor consumes intelligence.

It does not create intelligence.

---

# Architecture

## Current

```text
User Question
      ↓

Retrieval
      ↓

Memory
      ↓

Tutor
      ↓

Response
```

---

## Future

```text
User Question
      ↓

Retrieval
      ↓

Memory
      ↓

Learner Snapshot
      ↓

Recommendations
      ↓

Tutor Context Adapter
      ↓

Adaptive Tutor
      ↓

Response
```

---

# New Module

```text
src/core/learning_intelligence/tutor/
```

Structure:

```text
tutor/

├── tutor_context_adapter.py

├── learner_profile_builder.py

├── adaptive_strategy_selector.py

├── intervention_detector.py

├── recommendation_injector.py

└── tests/
```

---

# Core Concept

## Tutor Context Package

The tutor should never query educational systems directly.

Instead it receives:

```python
TutorContextPackage
```

---

## Model

```python
class TutorContextPackage:

    learner_snapshot

    top_recommendations

    active_misconceptions

    weak_topics

    strong_topics

    confidence_level

    ability_estimates

    active_recovery_plans

    due_reviews
```

---

# Learner Profile Builder

## Purpose

Transform raw snapshot data into tutoring signals.

---

## Example

Raw:

```json
{
  "mastery": 34,
  "ability": -0.5,
  "misconceptions": [...]
}
```

Converted to:

```json
{
  "difficulty_level": "beginner",

  "requires_scaffolding": true,

  "requires_concept_reinforcement": true
}
```

---

# Adaptive Difficulty Engine

## Purpose

Adjust explanation complexity.

---

# Difficulty Levels

```python
BEGINNER

DEVELOPING

PROFICIENT

ADVANCED
```

---

# Rules

## Beginner

Conditions:

```text
Critical mastery

Low confidence

Low ability
```

Behavior:

```text
Simpler language

Step-by-step explanations

More examples

Frequent comprehension checks
```

---

## Developing

Behavior:

```text
Moderate detail

Guided questioning

Applied examples
```

---

## Proficient

Behavior:

```text
More challenging questions

Higher-order reasoning

Connections across topics
```

---

## Advanced

Behavior:

```text
Socratic exploration

Problem-solving

Exam-style reasoning
```

---

# Misconception Intervention Engine

## Purpose

Detect and address known misconceptions.

---

# Example

Learner Snapshot:

```text
Dominant Gene Confusion
```

Student asks:

```text
What are dominant genes?
```

Tutor receives signal:

```text
Known misconception exists
```

Response behavior:

```text
Explain concept

Explicitly contrast misconception

Verify understanding
```

---

# Recovery Plan Awareness

## Purpose

Align tutoring with active recovery plans.

---

# Example

Active Recovery:

```text
Cell Division
```

Student asks unrelated question.

Tutor may include:

```text
You are also currently working on Cell Division.
Would you like a quick review afterwards?
```

---

# Recommendation Injection

## Purpose

Embed educational guidance naturally into tutoring.

---

# Example

Top Recommendation:

```text
Review Genetics
```

After answering:

```text
Based on your recent progress,
reviewing Genetics next would be valuable.
```

---

# Tutor Response Strategy Selection

New component:

```python
AdaptiveStrategySelector
```

---

# Supported Strategies

```python
DIRECT_EXPLANATION

SOCRATIC_GUIDANCE

MISCONCEPTION_REMEDIATION

CONFIDENCE_BUILDING

RECOVERY_SUPPORT

EXAM_PREPARATION
```

---

# Selection Logic

Uses:

```python
mastery

ability

confidence

recommendations

misconceptions
```

to select strategy.

---

# Tutor Graph Integration

Current graph:

```text
Orchestrator
    ↓

Retrieval
    ↓

Tutor
```

---

New graph:

```text
Orchestrator
      ↓

Retrieval
      ↓

Snapshot Retrieval
      ↓

Recommendation Retrieval
      ↓

Tutor Context Adapter
      ↓

Tutor
```

---

# Prompt Context Extension

New tutor prompt section:

```text
LEARNER PROFILE

Weak Topics:
...

Strong Topics:
...

Known Misconceptions:
...

Confidence:
...

Recommended Difficulty:
...

Top Learning Recommendations:
...
```

---

# API Support

New endpoint:

```http
GET /intelligence/tutor-context
```

Returns:

```json
{
  "difficulty_level": "developing",

  "weak_topics": [],

  "misconceptions": [],

  "recommendations": []
}
```

Useful for debugging and observability.

---

# Observability

Log:

```text
tutor_context_generated

adaptive_strategy_selected

misconception_detected

recommendation_injected

difficulty_level_selected
```

---

# Metrics

Track:

```text
adaptive_tutoring_sessions

misconception_interventions

recommendation_acceptance_rate

difficulty_distribution

learning_action_conversion_rate
```

---

# Testing Requirements

## Unit Tests

Validate:

* difficulty selection
* misconception intervention
* recommendation injection
* recovery awareness

---

## Integration Tests

Validate:

* snapshot retrieval
* recommendation retrieval
* tutor context assembly
* graph integration

---

## Behavioral Tests

Validate:

Same question asked by:

```text
Beginner learner

Advanced learner
```

produces meaningfully different tutoring behavior.

---

# Acceptance Criteria

## Functional

* Tutor receives Learner Snapshot.
* Tutor receives Recommendations.
* Tutor adapts difficulty.
* Tutor addresses known misconceptions.
* Tutor supports active recovery plans.
* Tutor incorporates learning recommendations.

---

## Performance

Additional personalization latency:

```text
< 300ms
```

---

## Architectural

* Tutor never directly queries educational models.
* Tutor only consumes TutorContextPackage.
* All personalization originates from Learning Intelligence Layer.

---

# Success Definition

EthioBio evolves from:

```text
Answering educational questions
```

to:

```text
Teaching each learner differently based on:

- mastery
- ability
- misconceptions
- confidence
- recovery status
- learning goals
```

This PRD creates the first truly personalized tutoring experience in the platform and serves as the primary consumer of the Learning Intelligence Layer.

---

