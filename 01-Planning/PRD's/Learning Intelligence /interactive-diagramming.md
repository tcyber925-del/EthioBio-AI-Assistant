# Feature PRD — Interactive Biology Diagramming

## Project
EthioBio AI Assistant

## Branch
feature/interactive-diagramming

---

# Overview

Implement an interactive biology diagram system where students can:
- generate biology diagrams,
- label structures,
- complete drag-and-drop exercises,
- practice visual biology learning.

---

# Goals

- Improve visual learning
- Reinforce biology structure recognition
- Increase interactive engagement
- Support diagram-based assessment

---

# Non-Goals

- Full CAD drawing system
- Advanced image editing
- Teacher collaborative whiteboards

---

# Core UX Flow

1. Student requests diagram
2. AI generates diagram or labeling exercise
3. Student labels structures
4. System validates labels
5. AI explains mistakes

---

# User Stories

## US-001 — Add diagram_attempts table to database

As a developer,
I need a database table to store student diagram attempt data.

Acceptance Criteria:
- Add diagram_attempts model with fields: user_id, topic, score, difficulty, completed_at
- Run migration successfully

Priority: 1

---

## US-002 — Create diagram generation API endpoint

As a developer,
I need a POST /diagram/generate endpoint that returns a diagram with labels and metadata.

Acceptance Criteria:
- POST /diagram/generate accepts prompt and topic parameters
- Returns diagram, labels, and metadata in response
- Supported topics: cells, organ systems, genetics, anatomy
- Integrates with AI image generation or SVG rendering

Priority: 2

---

## US-003 — Create diagram validation API endpoint

As a developer,
I need a POST /diagram/validate endpoint that scores labels and returns corrections with explanations.

Acceptance Criteria:
- POST /diagram/validate accepts label submissions
- Returns score, corrections, and explanations
- Structure matching and label correctness scoring implemented
- Saves attempt record to diagram_attempts table

Priority: 3

---

## US-004 — Build diagram request UI

As a student,
I want to request biology diagrams by topic so that I can study visually.

Acceptance Criteria:
- Prompt input field for requesting diagrams
- Topic selector: cells, organ systems, genetics, anatomy
- Difficulty selector: Beginner, Intermediate, Advanced
- Generated diagram displayed with annotation overlay

Priority: 4

---

## US-005 — Build interactive labeling UI

As a student,
I want to drag-and-drop or select labels on a diagram so that I can test my visual understanding.

Acceptance Criteria:
- Labels are draggable or selectable on the diagram
- Submit button sends labels for validation
- Correctness feedback displayed per label
- Validation results shown inline on the diagram

Priority: 5

---

## US-006 — Build diagram explanation feedback UI

As a student,
I want explanations for incorrect labels so that I can learn from my mistakes.

Acceptance Criteria:
- Incorrect labels are highlighted with explanations
- Explanations generated based on correct answer
- Retry button allows re-labeling incorrect items

Priority: 6

---

## US-007 — Add difficulty level selector to diagram system

As a student,
I want diagrams at different difficulty levels so that learning adapts to my ability.

Acceptance Criteria:
- Beginner/Intermediate/Advanced modes functional
- Label quantity increases with difficulty
- Difficulty selection persisted in diagram_attempts table

Priority: 7

---



---

# Technical Requirements

## Diagram Engine
Support:
- AI image generation
- SVG rendering
- Annotation overlays

## Validation Engine
- Structure matching
- Label correctness scoring

---

# Database Requirements

## diagram_attempts
- user_id
- topic
- score
- difficulty
- completed_at

---

# API Requirements

## POST /diagram/generate
Returns:
- diagram
- labels
- metadata

## POST /diagram/validate
Returns:
- score
- corrections
- explanations

---

# Quality Checks

- Diagram rendering tests
- Label validation tests
- Mobile responsiveness
- Accessibility checks

---

# Definition of Done

- Diagram generation functional
- Label interaction functional
- Validation works
- Feedback generation works
- Difficulty system works