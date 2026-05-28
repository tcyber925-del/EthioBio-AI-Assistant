# Glossary

## Persistent Learning State
The database-level records of student mastery, misconceptions, weak areas, and ability estimates that survive across sessions. Already implemented via `StudentMastery`, `MisconceptionPattern`, `TopicMasteryHistory`, `StudentAbility`, `SpacedRepetitionSchedule`, and `StudentProfile` models.

## Conversational Memory Layer
The system that tracks what happened during an active tutoring conversation — current topic, recent turns, Socratic stage, unresolved questions — and persists that context across tutoring sessions. This does NOT exist yet. This is the gap the Persistent Educational Memory feature addresses.

## SessionState
New database table for conversation continuity during an active tutoring session. Genuinely missing — no equivalent exists today.

## SocraticState
New database table for multi-turn Socratic dialogue tracking (reasoning stage, pedagogical trajectory, next guiding question). Genuinely missing — current `socratic_mode` is only a boolean toggle.

## EducationalSummary
New database table for compressed, educationally-significant summaries of completed tutoring sessions. Genuinely missing.

## Existing tables (do NOT duplicate)
Tables that already exist and should be extended rather than replaced: `student_profiles`, `student_mastery`, `misconception_patterns`, `student_abilities`, `spaced_repetition_schedule`, `topic_mastery_history`, `recovery_plans`, `recovery_tasks`, `recovery_notifications`, `user_gamification`, `xp_events`.

## Canonical Tutor Pipeline
The LangGraph pipeline (OrchestratorNode → RetrievalNode → TutorNode → SafetyNode) is the canonical tutoring path. The direct `TutorAgent` (`src/agents/tutor.py`) should be considered legacy or a thin wrapper. All memory integration targets the LangGraph pipeline.

## Educational Event System (MVP)
Minimal logging approach. No dedicated event bus. A lightweight `memory_events` log table with (user_id, event_type, topic, metadata JSON, created_at). Existing event-like records (`QuizAttempt`, `RecoveryNotification`, `TopicMasteryHistory`, `FeedbackEvent`) handle domain-specific events. Full event-driven architecture deferred.

## Memory Conflict Resolution
Confidence-based natural resolution. No dedicated conflict resolver. The retrieval ranking prefers recent, high-confidence memories. Corrected misconceptions naturally rank higher via recency + confidence. Old entries fade via recency decay. Sufficient for MVP.

## Token Budgeting for Memory Injection
Memory context capped at 1500 tokens in the tutor system prompt: ~200t for structured learner context (mastery, misconceptions, preferences), ~1200t for 1-2 recent educational summaries, ~100t for Socratic state. Curriculum RAG context fills the remaining window. Dynamic truncation by importance when budget exceeded.

## Socratic State Machine (MVP)
LLM-determined state with 4 stages: `guided_discovery`, `evaluation`, `correction`, `consolidation`. The LLM outputs the current stage and next question after each response. Code persists the state — it does not enforce transition rules. State machine complexity deferred until dialogue patterns are understood from real usage.

## Session Memory Strategy
Stateless per-request with DB reads. Each tutor request reads latest `SessionState` + `SocraticState` from DB, writes back updated state after response. Sessions defined by clusters of activity (gap > 30min = new session). No LangGraph checkpointing or in-memory session tracking for MVP.

## Memory Injection Mechanism
Memory is injected into the LangGraph TutorNode as a structured **system prompt prefix** block (e.g., "Learner Context: ..."). This keeps memory instructional (how to tutor) separate from RAG context (what to teach), enables conditional inclusion, precise token budgeting, and follows the existing `{context}` placeholder pattern.

## Implementation Passes (Memory Feature)
1. **Pass 1 — Session + Socratic Memory** — new `SessionState` and `SocraticState` tables, conversation tracking, multi-turn state machine
2. **Pass 2 — Educational Summarization** — session summarizer, summary persistence, ChromaDB collection for summaries
3. **Pass 3 — Semantic Retrieval + Ranking** — vector search over summaries, recency weighting, relevance ranking, token budgeting
4. **Pass 4 — Memory Injection into TutorNode** — prompt assembly with active misconceptions, mastery context, recent summaries, Socratic state; modify LangGraph pipeline to add memory context
5. **Pass 5 — Memory Evaluation + Optimization** — latency, token efficiency, quality metrics, safeguards

## Vector Storage for Educational Memory
Reuses the existing ChromaDB via `VectorStoreAdapter` with a separate collection for educational summaries/semantic memories. No new vector infrastructure for MVP. pgvector integration is deferred — the adapter interface makes this swappable.

## Memory Lifecycle Engine (MVP)
Not implemented as a dedicated subsystem for MVP. Replaced by simpler strategies: recency-weighted retrieval ranking, periodic summary compression, spaced-repetition-based confidence decay, and a retention policy (keep N most recent session summaries per user). Full lifecycle engine deferred until data volume warrants it.
