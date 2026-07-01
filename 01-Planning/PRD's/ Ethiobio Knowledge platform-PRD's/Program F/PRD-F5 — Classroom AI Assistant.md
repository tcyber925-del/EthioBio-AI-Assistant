# PRD-F5 — Classroom AI Assistant

**Program:** F – AI Classroom & School Management Platform

**Epic:** F5

**Status:** Ready for Implementation

---

# Executive Summary

The Classroom AI Assistant is an always-available educational copilot embedded inside every classroom. It provides contextual assistance to teachers and students using Retrieval Intelligence, Educational Intelligence, and classroom-specific knowledge.

Every response is grounded in approved educational knowledge and classroom materials.

---

# Goals

* Classroom-aware AI
* Teacher assistance
* Student tutoring
* Citation-backed answers
* Classroom context awareness
* Multi-turn educational conversations

---

# Supported Users

Teacher

Student

Teaching Assistant

School Administrator

---

# Teacher Capabilities

* Explain concepts
* Generate classroom activities
* Create worksheets
* Create quizzes
* Generate assignments
* Summarize uploaded documents
* Suggest remediation
* Build lesson plans
* Generate classroom announcements

---

# Student Capabilities

* Guided study
* Homework help
* Concept explanations
* Practice questions
* Flashcards
* Revision guides
* Exam preparation
* Study planning

---

# AI Pipeline

```text id="f5pipe"
User Request
      ↓
Planner
      ↓
Retrieval Intelligence
      ↓
Educational Intelligence
      ↓
Classroom Context
      ↓
Grounded Generation
      ↓
Citation Validation
      ↓
Response
```

---

# Context Sources

* Classroom materials
* Teacher uploads
* Published textbooks
* Lesson plans
* Assignments
* Student progress
* Curriculum

---

# Functional Requirements

Support

* Multi-turn conversations
* Conversation memory
* Citation display
* Suggested follow-up questions
* Context-aware recommendations
* Workspace isolation

---

# APIs

POST /assistant/chat

POST /assistant/explain

POST /assistant/lesson

GET /assistant/history

---

# Events

AssistantConversationStarted

AssistantResponseGenerated

CitationVerified

---

# Testing

Grounding

Hallucination prevention

Conversation quality

Permissions

Regression

---

# Acceptance Criteria

✓ AI assistant operational

✓ Citations preserved

✓ Classroom context integrated

✓ Tests passing

---

# Task Packages

F5.1 Conversation Engine

F5.2 Classroom Context Builder

F5.3 Citation Renderer

F5.4 Conversation History

F5.5 Testing

---

# Definition of Done

Classroom AI operational

Documentation complete

Tests passing
