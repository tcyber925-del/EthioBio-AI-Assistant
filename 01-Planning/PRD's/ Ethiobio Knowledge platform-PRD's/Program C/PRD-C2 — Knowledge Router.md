# PRD-C2 — Knowledge Router

**Program:** C – Retrieval Intelligence

**Epic:** C2

**Status:** Ready for Implementation

---

# Executive Summary

The Knowledge Router determines **where** and **how** information should be retrieved.

Rather than searching every knowledge source equally, the router intelligently selects the optimal retrieval strategy based on user intent, workspace context, document provenance, educational metadata, and publication status.

It is the decision-making layer of the retrieval system.

---

# Goals

* Route retrieval intelligently.
* Prioritize authoritative knowledge.
* Support multiple knowledge sources.
* Optimize retrieval quality.
* Reduce latency.
* Enable future retrieval strategies.

---

# Knowledge Sources

The router can retrieve from:

## Platform Knowledge

* Biology textbooks
* Official curriculum
* Built-in educational resources

Priority: Highest

---

## Workspace Knowledge

* Uploaded textbooks
* Teacher lesson plans
* Notes
* Worksheets
* Assessments
* Research materials

Priority: Configurable

---

## Classroom Knowledge

* Shared classroom resources
* Assignments
* Learning materials

---

## School Knowledge

* School policies
* Internal documents
* Shared curriculum

---

## Future Sources

* Internet search
* Scientific journals
* LMS integrations
* Institutional repositories

---

# Routing Pipeline

```text
User Query
      ↓
Intent Detection
      ↓
Workspace Resolution
      ↓
Source Selection
      ↓
Retrieval Strategy Selection
      ↓
Evidence Requests
      ↓
Merge Results
```

---

# Routing Strategies

Support:

* Platform-first
* Workspace-first
* Hybrid
* Curriculum-priority
* Metadata-priority
* Version-specific
* Collection-specific

Strategies are configurable per workspace.

---

# Intent Categories

Recognize:

* Guided study
* Question answering
* Lesson planning
* Quiz generation
* Flashcard generation
* Assignment creation
* Classroom management
* Administrative queries
* Document search

---

# Routing Policies

Examples:

Student asks Biology question

↓

Platform textbook first

↓

Teacher-uploaded materials

↓

Student notes

---

Teacher creates lesson plan

↓

Teacher workspace

↓

Platform curriculum

↓

Official textbooks

---

# APIs

Internal service.

Commands

* Route Retrieval

Queries

* Routing Decision
* Source Statistics

---

# Events

Publish

* RoutingStarted
* RoutingCompleted
* RoutingFailed

Consume

* RetrievalRequested

---

# Performance

Routing decision

<50 ms

---

# Security

Router must never expose inaccessible knowledge sources.

Permission evaluation occurs before route generation.

---

# Testing

* Routing correctness
* Workspace isolation
* Intent classification
* Multi-source retrieval
* Regression corpus

---

# Acceptance Criteria

✓ Intelligent routing operational

✓ Source prioritization implemented

✓ Routing strategies configurable

✓ Workspace isolation maintained

✓ Tests passing

---

# Task Packages

C2.1 Intent Analyzer

C2.2 Source Resolver

C2.3 Strategy Engine

C2.4 Route Optimizer

C2.5 Policy Engine

C2.6 Events

C2.7 Testing

---

# Definition of Done

* Routing engine operational
* Strategy framework implemented
* Performance targets met
* Documentation updated
* CodeRabbit approved
