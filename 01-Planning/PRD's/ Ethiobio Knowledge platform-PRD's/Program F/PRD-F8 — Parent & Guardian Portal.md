# PRD-F8 — Parent & Guardian Portal

**Program:** F – AI Classroom & School Management Platform

**Epic:** F8

**Status:** Ready for Implementation

---

# Executive Summary

The Parent & Guardian Portal provides families with secure access to student learning progress, attendance, assignments, reports, school communications, and AI-generated progress summaries.

---

# Goals

* Family engagement
* Progress visibility
* Attendance monitoring
* Assignment tracking
* Communication

---

# Portal Features

* Student dashboard
* Attendance
* Grades
* Assignments
* Progress reports
* Teacher messages
* AI summaries
* Notifications

---

# AI Features

Generate

* Weekly summaries
* Learning highlights
* Areas needing support
* Suggested home study activities

---

# Functional Requirements

Parents can

* View progress
* Receive notifications
* Download reports
* View attendance
* Track assignments

Cannot

* Edit grades
* Access other students
* Modify classroom content

---

# APIs

GET /parent/dashboard

GET /parent/student/{id}

GET /parent/reports

---

# Events

GuardianInvited

ProgressShared

ReportPublished

---

# Testing

Permissions

Privacy

Notifications

Regression

---

# Acceptance Criteria

✓ Parent portal operational

✓ Privacy enforced

✓ Reports available

✓ Tests passing

---

# Task Packages

F8.1 Parent Dashboard

F8.2 Progress Reports

F8.3 Notification Center

F8.4 APIs

F8.5 Testing

---

# Definition of Done

Parent portal operational

Documentation complete

Tests passing
