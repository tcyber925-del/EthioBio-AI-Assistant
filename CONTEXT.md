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

## Learning Intelligence Layer (LIL)
Centralized orchestration layer at `src/core/learning_intelligence/` that transforms educational data into educational decisions. Consumes existing systems (StudentMastery, StudentAbility, etc.) without replacing them. Follows the existing `src/core/memory/` module convention.

## LearnerSnapshot
Computed, read-only, non-persistent educational profile of a learner. Built by SnapshotBuilder on demand (or served from cache). NOT a database table — it is a projection over existing sources of truth.

## SnapshotBuilder
The single component responsible for assembling a LearnerSnapshot. Loads all educational data sources in parallel via `asyncio.gather()` then assembles the result. Located at `src/core/learning_intelligence/snapshot/snapshot_builder.py`.

## GamificationSummary
Single collapsed view of a learner's gamification state. Contains current_streak, longest_streak, total_xp, level, and computed recent_activity_score. Replaces the separate engagement_metrics and gamification_state fields from the original PRD draft — they were redundant views over the same UserGamification record.

## Weak Topics (threshold)
Topics with StudentMastery.severity equal to "critical" or "moderate". Defined by existing convention in `weak_topic_detection.py`, not a new classification.

## Strong Topics (threshold)
Topics with StudentMastery.severity equal to "good". Topics with severity "mild" are neither weak nor strong.

## Recent Activity Score
Computed field on GamificationSummary using a weighted heuristic: `0.6 * recency + 0.4 * streak_factor`, where recency decays over 30 days of inactivity and streak_factor caps at a 14-day streak. Requires no extra DB queries beyond the UserGamification record.

## Snapshot Domain Models
All sub-models in the LearnerSnapshot tree (MisconceptionSummary, RecoverySummary, ReviewSummary, EducationalMemorySummary, GamificationSummary) are Pydantic BaseModel classes, not dataclasses or NamedTuples. Kept in `src/core/learning_intelligence/models/` rather than `src/schemas/` to distinguish domain projections from API request/response shapes.

## SnapshotBuilder Degradation
Any source loader that fails (exception or missing data) produces a None/default for that field rather than failing the entire snapshot. The resulting LearnerSnapshot carries a `degraded: bool` flag and `degraded_sources: list[str]` to signal incompleteness. Consumers (Recommendation Engine, Tutor Adapter) can decide whether to proceed with partial data.

## Source Loaders
SnapshotBuilder delegates each data source to a dedicated async loader function in `src/core/learning_intelligence/snapshot/loaders/`. Each loader takes an AsyncSession and user_id, catches its own exceptions, and returns data or None. This keeps per-source error isolation and makes partial degradation natural.

## Snapshot Cache Backend
Redis, consistent with existing infra (docker-compose + config.py redis_url). Thin wrapper via CacheManager — get/set/delete with TTL. Worker-safe for multi-process uvicorn.

## LearnerSnapshot API
GET /intelligence/snapshot returns the full LearnerSnapshot model verbatim (not a trimmed view). The SnapshotService exposes a single public method: `get_snapshot(user_id: UUID) -> LearnerSnapshot`. No invalidate/refresh methods until a consumer needs them.

## User Existence Check
The API layer (endpoint handler) performs an explicit lightweight user existence check before calling SnapshotService. The SnapshotBuilder itself does not validate user existence — it builds from whatever data exists for the given user_id.

## LearningRecommendation
The domain model for the Recommendation Engine. Contains action_type, topic, priority_score (0.0-1.0), reason, explanation, generated_at, and metadata. Defined in `src/core/learning_intelligence/recommendation/models/recommendation.py`.

## Recommendation Engine Degradation
The engine does not explicitly check the snapshot's `degraded` flag. It reads whatever fields are populated — if a source field is empty (e.g., `mastery_by_topic == {}`), no recommendations are generated from that source. If all sources are empty, the engine returns an empty list. The snapshot's partial degradation design (ADR 0001) naturally propagates through.

## Recommendation Rule Files
Each recommendation source has its own rule file under `src/core/learning_intelligence/recommendation/rules/`: `mastery_rules.py`, `recovery_rules.py`, `review_rules.py`, `misconception_rules.py`, `engagement_rules.py`. Misconception rules are separate from mastery rules — they treat each `MisconceptionSummary` as its own recommendation, not a derived property of a mastery record.

## LearningActionType Enum
Phase 1 implements only the 4 action types with explicit rules: `REVIEW_TOPIC`, `COMPLETE_RECOVERY_TASK`, `REVISE_MISCONCEPTION`, and `MAINTAIN_STREAK`. The other action types (`TAKE_QUIZ`, `STUDY_DIAGRAM`, `READ_CONTENT`, `ASK_TUTOR`, `EXAM_PRACTICE`) exist in the enum as stubs for future phases — no rule produces them yet.

## Recommendation Priority Scoring
Additive weight system with fixed normalization denominator. Each rule assigns a raw score (e.g., critical mastery = +40, overdue 8+ days = +30, active misconception = +20). Multiple signals for the same topic stack additively. After all rules run, recommendations sharing the same (action_type, topic) pair are deduplicated (higher score wins). Raw scores are normalized to 0.0–1.0 by dividing by `MAX_POSSIBLE_SCORE = 120`, clamped to `[0.0, 1.0]`. The constant is adjusted when new weights are added.
