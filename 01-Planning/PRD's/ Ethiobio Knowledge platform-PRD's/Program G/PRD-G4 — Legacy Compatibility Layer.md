# PRD-G4 — Legacy Compatibility Layer

**Program:** G – Migration & Rollout

**Epic:** G4

**Status:** Ready for Implementation

---

# Executive Summary

Provide compatibility adapters that allow the existing frontend and API clients to continue functioning while requests are progressively routed through the new architecture.

---

# Goals

* Backward compatibility
* Transparent routing
* Incremental adoption
* Legacy API preservation

---

# Compatibility Scope

Support

* Existing REST APIs
* Existing authentication
* Existing chat workflow
* Existing retrieval flow
* Existing frontend

---

# Routing Model

```text id="g4route"
Legacy Request
      ↓
Compatibility Layer
      ↓
Planner
      ↓
Retrieval
      ↓
Educational Intelligence
      ↓
Response
```

---

# Requirements

* No frontend breakage
* Response compatibility
* Header compatibility
* Error compatibility

---

# APIs

Compatibility adapters

---

# Events

LegacyRequestHandled

CompatibilityFallback

---

# Testing

API compatibility

Response validation

Regression

---

# Acceptance Criteria

✓ Existing APIs preserved

✓ Frontend unchanged

✓ Compatibility verified

✓ Tests passing

---

# Task Packages

G4.1 API Adapters

G4.2 Response Mapper

G4.3 Compatibility Tests

G4.4 Monitoring

G4.5 Testing

---

# Definition of Done

Compatibility layer operational

Regression complete

Tests passing
