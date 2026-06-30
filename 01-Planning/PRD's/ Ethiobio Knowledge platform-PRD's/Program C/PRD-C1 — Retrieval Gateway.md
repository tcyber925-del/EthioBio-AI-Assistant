# PRD-C1 — Retrieval Gateway

**Program:** C – Retrieval Intelligence

**Epic:** C1

**Status:** Ready for Implementation

---

# Executive Summary

The Retrieval Gateway is the single entry point for every AI knowledge retrieval request.

No AI component accesses indexes directly. Every request flows through the gateway, ensuring consistency, security, observability, and policy enforcement.

---

# Goals

* Centralize retrieval
* Hybrid search orchestration
* Workspace isolation
* Query normalization
* Context injection
* Observability
* Policy enforcement

---

# Non-Goals

* LLM generation
* Educational reasoning
* Citation formatting

---

# Request Flow

```text
AI Request
      ↓
Authentication
      ↓
Authorization
      ↓
Query Normalization
      ↓
Workspace Context
      ↓
Knowledge Router
      ↓
Evidence Package Engine
      ↓
Response
```

---

# Functional Requirements

## Query Processing

Support:

* Natural language
* Keyword
* Educational questions
* Lesson planning
* Guided study
* Classroom planning
* School administration

---

## Context Injection

Automatically include

* Workspace
* Grade
* Subject
* Curriculum
* User role
* Collection filters
* Language
* Publication status

---

## Retrieval Modes

Support

* Semantic
* Lexical
* Hybrid
* Metadata
* Citation lookup
* Version-specific retrieval

---

## Response

Returns

* Ranked evidence
* Citations
* Confidence
* Retrieval metadata

---

# APIs

POST

/retrieval/query

POST

/retrieval/evidence

GET

/retrieval/status

---

# Events

Publish

* RetrievalStarted
* RetrievalCompleted
* RetrievalFailed

---

# Performance

Average latency

<300 ms

---

# Security

Workspace isolation mandatory.

Permission checks before retrieval.

---

# Testing

* Workspace isolation
* Hybrid search
* Large corpus
* Multi-workspace
* Performance
* Regression

---

# Acceptance Criteria

✓ Gateway operational

✓ Hybrid retrieval available

✓ Context injection complete

✓ APIs documented

✓ Tests passing

---

# Task Packages

C1.1 Gateway API

C1.2 Query Normalizer

C1.3 Context Injection

C1.4 Authorization

C1.5 Metrics

C1.6 Tests

---

# Definition of Done

* Gateway operational
* EOS compliant
* Tests passing
* Documentation updated
