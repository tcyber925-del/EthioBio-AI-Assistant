# Feature PRD — Socratic Tutoring Mode

## Project
EthioBio AI Assistant

## Branch
feature/socratic-tutoring

---

# Overview

Implement a Socratic tutoring mode that guides students toward answers through progressively adaptive questioning instead of immediately revealing answers.

The goal is to improve:
- active recall,
- reasoning,
- conceptual understanding,
- retention,
- metacognition.

The AI should behave like a biology tutor rather than an answer engine.

---

# Goals

- Increase student engagement
- Encourage reasoning before answer exposure
- Reduce passive answer consumption
- Improve biology concept retention
- Create adaptive guided tutoring flows

---

# Non-Goals

- Full conversational memory across sessions
- Voice tutoring
- Real-time classroom collaboration
- Long-term personalized pedagogy optimization

---

# Core UX Flow

1. Student asks a biology question
2. Student enables "Socratic Mode"
3. AI responds with:
   - guiding question,
   - hint,
   - analogy,
   - partial clue,
   - misconception correction
4. Student attempts answer
5. AI evaluates reasoning quality
6. AI continues scaffolding
7. Final explanation revealed only after attempts or explicit request

---

# AI Behavior Rules

## AI Must:
- Ask questions before giving direct answers
- Encourage reasoning
- Detect misconceptions
- Adapt difficulty
- Provide hints progressively
- Encourage confidence-building

## AI Must Not:
- Immediately reveal final answers
- Overwhelm with long explanations
- Ask unrelated questions
- Punish incorrect reasoning

---

# Prompting Strategy

System prompt additions:
- "Act as a biology tutor using Socratic questioning."
- "Guide students toward answers using active recall."
- "Avoid directly giving answers unless necessary."
- "Reveal answers progressively."

---

# User Stories

## ST-001 — Toggle Socratic Mode

As a student,
I want to enable Socratic tutoring,
so that I can learn through guided reasoning.

Acceptance Criteria:
- Toggle exists in chat UI
- State persists during session
- Messages use Socratic prompting
- Default mode remains normal chat

Priority: 1

---

## ST-002 — Guided Question Generation

As a student,
I want the AI to ask guiding questions,
so that I can think critically before answering.

Acceptance Criteria:
- AI asks at least one guiding question
- Question relates to current biology topic
- Question difficulty adapts to context

Priority: 1

---

## ST-003 — Hint Progression System

As a student,
I want hints to become progressively more helpful,
so that I can eventually solve the problem.

Acceptance Criteria:
- Hints progress from broad to specific
- Maximum 3 hint levels
- Final answer optionally revealable

Priority: 2

---

## ST-004 — Misconception Detection

As a student,
I want incorrect assumptions corrected gently,
so that I do not reinforce wrong biology concepts.

Acceptance Criteria:
- AI detects obvious conceptual errors
- Corrections remain supportive
- AI explains why reasoning is incorrect

Priority: 2

---

## ST-005 — Reveal Answer Fallback

As a student,
I want to reveal the answer after multiple attempts,
so that I do not get stuck indefinitely.

Acceptance Criteria:
- Reveal button exists
- Final answer includes explanation
- Attempt count tracked

Priority: 2

---

# Data Requirements

## Session State
- socraticMode: boolean
- hintLevel: integer
- attemptCount: integer
- revealedAnswer: boolean

---

# API Requirements

## POST /chat
Input:
- message
- socraticMode
- hintLevel
- attemptCount

Output:
- tutorResponse
- responseType
- nextHintAvailable

---

# Quality Checks

- Prompt behavior validation
- Typecheck
- Lint
- Chat flow tests
- Misconception detection tests

---

# Definition of Done

Feature is complete when:
- Socratic mode works end-to-end
- Hint progression works
- Final answer reveal works
- Prompt routing works
- Tests pass
- Documentation updated