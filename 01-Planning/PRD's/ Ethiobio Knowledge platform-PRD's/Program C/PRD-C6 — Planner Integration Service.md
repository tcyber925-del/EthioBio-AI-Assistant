# PRD-C6 — Planner Integration Service

**Program:** C – Retrieval Intelligence Platform

**Epic:** C6

**Status:** Ready for Implementation

**Priority:** Critical

---

# Executive Summary

The Planner Integration Service bridges Retrieval Intelligence with the AI orchestration layer.

Rather than sending user prompts directly to an LLM, the planner first determines the user's intent, decomposes complex requests into executable retrieval tasks, requests evidence packages, and assembles grounded context for generation.

This service makes the platform task-oriented instead of prompt-oriented.

---

# Goals

* Integrate retrieval with AI planning.
* Decompose complex educational requests.
* Coordinate multi-step retrieval.
* Build grounded AI context.
* Support future multi-agent workflows.

---

# Supported Planning Tasks

Educational

* Guided study
* Lesson planning
* Quiz generation
* Flashcard generation
* Concept explanation
* Homework assistance
* Curriculum mapping

Teacher

* Classroom planning
* Assessment generation
* Rubric creation
* Worksheet generation

School

* Policy lookup
* Administrative document retrieval
* Resource discovery

---

# Planning Pipeline

```text
User Request
      ↓
Intent Classification
      ↓
Task Decomposition
      ↓
Retrieval Planning
      ↓
Evidence Requests
      ↓
Evidence Packages
      ↓
Context Assembly
      ↓
LLM Generation
```

---

# Planner Responsibilities

* Identify user intent.
* Determine required evidence.
* Minimize retrieval cost.
* Merge multiple evidence packages.
* Resolve conflicts.
* Preserve citations.
* Return grounded generation context.

---

# Context Package

PlannerContext

```text
request_id
intent
workspace
tasks
evidence_packages
citations
trust_scores
constraints
generation_context
```

---

# Failure Handling

Support

* Missing evidence
* Low-confidence retrieval
* Conflicting sources
* Partial evidence
* Planner retries

---

# APIs

Internal

Commands

* Plan Request
* Execute Retrieval Plan

Queries

* Plan Status
* Planner Report

---

# Events

Publish

* PlanningStarted
* PlanGenerated
* PlanExecuted
* PlanningCompleted
* PlanningFailed

Consume

* RetrievalRequested
* RankingCompleted
* CitationGenerated

---

# Performance

Planning

<150 ms

Total planner orchestration

<500 ms

---

# Observability

Track

* Planning latency
* Retrieval stages
* Evidence utilization
* Plan complexity
* Planner success rate

---

# Testing

* Multi-step planning
* Complex educational workflows
* Planner recovery
* Retrieval coordination
* Regression corpus

---

# Acceptance Criteria

✓ Planner integration operational

✓ Task decomposition implemented

✓ Evidence orchestration complete

✓ Grounded context generation operational

✓ Metrics integrated

✓ Tests passing

---

# Task Packages

C6.1 Intent Classifier

C6.2 Task Decomposer

C6.3 Retrieval Planner

C6.4 Context Assembler

C6.5 Planner Orchestrator

C6.6 Planner Metrics

C6.7 Events

C6.8 Testing

---

# Definition of Done

* Planner integration complete
* Retrieval orchestration operational
* AI context generation implemented
* Documentation updated
* Tests passing
* CodeRabbit approved
