# PRD-F1 — Classroom Management

**Program:** F – AI Classroom & School Management Platform

**Epic:** F1

**Status:** Ready for Implementation

---

# Executive Summary

The Classroom Management module enables teachers to create, organize, and manage AI-enabled classrooms that integrate learning resources, assignments, assessments, discussions, attendance, and AI learning support.

---

# Goals

* Classroom lifecycle management
* Student enrollment
* Resource organization
* Attendance tracking
* Classroom announcements
* AI classroom support

---

# Functional Requirements

Support

* Create classroom
* Archive classroom
* Invite students
* Remove students
* Assign co-teachers
* Classroom templates

---

# Classroom Structure

```text id="f1cls"
School
    ↓
Grade
    ↓
Section
    ↓
Classroom
    ↓
Students
```

---

# Classroom Features

* Materials
* Lessons
* Assignments
* Attendance
* Discussions
* AI Assistant
* Calendar
* Grades

---

# Classroom Dashboard

Display

* Upcoming lessons
* Pending assignments
* Student participation
* AI recommendations
* Attendance summary
* Recent activity

---

# APIs

POST /classrooms

GET /classrooms

PATCH /classrooms/{id}

DELETE /classrooms/{id}

---

# Events

ClassroomCreated

StudentJoined

StudentRemoved

AttendanceRecorded

---

# Testing

Enrollment

Permissions

Attendance

Performance

Regression

---

# Acceptance Criteria

✓ Classroom lifecycle complete

✓ Attendance operational

✓ AI integration operational

✓ Tests passing

---

# Task Packages

F1.1 Classroom Service

F1.2 Enrollment Manager

F1.3 Attendance Module

F1.4 Dashboard

F1.5 APIs

F1.6 Testing

---

# Definition of Done

Classroom management operational

Documentation complete

Tests passing
