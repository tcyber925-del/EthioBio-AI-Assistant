# PRD-F2 — Assignment Management

**Program:** F – AI Classroom & School Management Platform

**Epic:** F2

**Status:** Ready for Implementation

---

# Executive Summary

The Assignment Management Engine manages the complete assignment lifecycle from creation through submission, grading, AI feedback, revision, and analytics.

---

# Goals

* Assignment lifecycle
* AI-assisted creation
* Submission management
* Automated feedback
* Teacher review

---

# Assignment Types

* Homework
* Quiz
* Project
* Lab
* Essay
* Worksheet
* Presentation

---

# Assignment Workflow

```text id="f2flow"
Create
   ↓
Publish
   ↓
Student Submission
   ↓
AI Review
   ↓
Teacher Review
   ↓
Feedback
   ↓
Revision
   ↓
Completed
```

---

# Features

Support

* Due dates
* Rubrics
* Attachments
* AI-generated hints
* Multiple attempts
* Group assignments

---

# Submission

Track

* Submission time
* Late status
* Version history
* Similarity analysis
* AI feedback

---

# APIs

POST /assignments

GET /assignments

POST /submissions

GET /grades

---

# Events

AssignmentCreated

SubmissionReceived

SubmissionReviewed

AssignmentCompleted

---

# Testing

Submission flow

Large classes

Feedback

Regression

---

# Acceptance Criteria

✓ Assignment lifecycle operational

✓ AI feedback operational

✓ Rubrics supported

✓ Tests passing

---

# Task Packages

F2.1 Assignment Service

F2.2 Submission Engine

F2.3 Rubric Manager

F2.4 Feedback Engine

F2.5 Testing

---

# Definition of Done

Assignment management operational

Documentation complete

Tests passing
