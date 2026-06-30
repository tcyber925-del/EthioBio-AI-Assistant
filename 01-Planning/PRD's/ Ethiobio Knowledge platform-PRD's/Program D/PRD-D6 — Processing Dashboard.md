# PRD-D6 — Processing Dashboard

**Program:** D – Knowledge Workspace

**Epic:** D6

**Status:** Ready for Implementation

---

# Executive Summary

The Processing Dashboard provides complete visibility into the Knowledge Processing Pipeline, allowing users and administrators to monitor uploads from submission through publication, diagnose failures, retry processing, and review processing reports.

---

# Goals

* Transparent processing
* Real-time status
* Failure diagnostics
* Retry controls
* Operational visibility

---

# Dashboard Sections

* Active Jobs
* Processing Timeline
* Queue Status
* Failed Jobs
* Completed Jobs
* Processing Metrics

---

# Processing Stages

* Upload
* Validation
* Parsing
* Metadata
* Chunking
* Embeddings
* Indexing
* Publication

---

# Features

* Live updates
* Progress bars
* Retry failed jobs
* Cancel processing
* Download reports
* View logs (permission-based)

---

# APIs

GET /processing

GET /processing/{id}

POST /processing/{id}/retry

POST /processing/{id}/cancel

---

# Events

Consume

ProcessingStarted

ProcessingCompleted

ProcessingFailed

PublicationCompleted

---

# Performance

Live updates

<2 seconds refresh interval

---

# Testing

Live updates

Retry

Failure recovery

Permissions

Regression

---

# Acceptance Criteria

✓ Dashboard operational

✓ Live status operational

✓ Retry supported

✓ Reports available

✓ Tests passing

---

# Task Packages

D6.1 Timeline UI

D6.2 Live Status

D6.3 Retry Controls

D6.4 Reports

D6.5 Metrics

D6.6 Testing

---

# Definition of Done

Processing dashboard complete

Responsive

Accessible

Tests passing
