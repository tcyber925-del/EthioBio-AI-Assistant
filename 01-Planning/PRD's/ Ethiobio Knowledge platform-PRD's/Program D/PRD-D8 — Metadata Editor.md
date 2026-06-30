# PRD-D8 — Metadata Editor

**Program:** D – Knowledge Workspace

**Epic:** D8

**Status:** Ready for Implementation

---

# Executive Summary

The Metadata Editor enables authorized users to review, edit, enrich, and validate document metadata and educational metadata before or after publication. It supports manual corrections while preserving provenance and audit history.

---

# Goals

* Metadata editing
* Educational metadata review
* Validation
* Bulk editing
* Provenance tracking

---

# Editable Metadata

General

* Title
* Description
* Tags
* Author
* Language
* Subject
* Grade
* Curriculum

Educational

* Learning objectives
* Concepts
* Keywords
* Bloom level
* Difficulty
* Prerequisites

Administrative

* Collection
* Visibility
* Publication schedule

---

# Validation

Validate

* Required fields
* Metadata consistency
* Curriculum alignment
* Duplicate values
* Controlled vocabularies

---

# Bulk Editing

Support

* Tags
* Subject
* Grade
* Curriculum
* Collection
* Visibility

---

# Audit

Track

* Previous value
* New value
* User
* Timestamp
* Reason

---

# APIs

GET /metadata/{knowledgeId}

PATCH /metadata/{knowledgeId}

POST /metadata/bulk

---

# Events

Publish

MetadataUpdated

MetadataValidated

Consume

KnowledgePublished

VersionCreated

---

# Performance

Metadata updates

<100 ms

---

# Testing

Validation

Bulk editing

Permissions

Audit

Regression

---

# Acceptance Criteria

✓ Metadata editor operational

✓ Educational metadata editable

✓ Audit history maintained

✓ Bulk editing supported

✓ Tests passing

---

# Task Packages

D8.1 Metadata Forms

D8.2 Validation Engine

D8.3 Bulk Editor

D8.4 Audit Logger

D8.5 APIs

D8.6 Testing

---

# Definition of Done

Metadata editor complete

Audit operational

Documentation updated

Tests passing
