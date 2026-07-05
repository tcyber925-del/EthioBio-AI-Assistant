# Glossary

## Execution Roadmap
Canonical implementation sequence at `01-Planning/ROADMAP.md`. 10 waves from Foundation Stabilization (Wave 0) through Multi-Agent System (Wave 10). Teacher Copilot MVP before infrastructure. Postgres-first. Event Bus deferred. Agents last.

## KML Strangler Fig (Architectural Decision)
The Knowledge Management Layer (KMAS/KLDMS) is built alongside the existing RAG system without modifying it. New features (Program D workspaces, Program E educational intelligence, Program F classroom) route through the KML gateway and get workspace scoping, layer routing, and provenance tracking. Existing graph nodes (`RetrievalNode`, `SearchFanoutNode`, `TutorNode`) keep their direct path through `VectorStoreAdapter` unchanged. Migration to the gateway happens incrementally per-feature when a feature needs workspace awareness or provenance.

## Knowledge Layers (logical)
The 7 layers defined in KMAS (Platform, Curriculum, Organization, Workspace, Personal, Memory, External) are a logical concept — a `layer` metadata field on Knowledge Objects and chunks, plus a route table mapping each layer to its storage backend. Not separate physical infrastructure per layer. The Retrieval Gateway uses this field to scope queries to the correct backends.

## Knowledge Router (facade)
The Knowledge Router (KMAS §4.3) is a thin facade for new KML consumers — it wraps the existing Orchestrator + PlanExecutor with workspace context and layer scoping. It does NOT replace `_route_after_orchestrator` or `PlanExecutor`. Existing graph nodes continue routing through the existing OrchestratorNode directly. The Router exists so new features (Program D/E/F) get workspace-aware, layer-scoped routing without touching the legacy pipeline internals.

## Planner vs Gateway responsibility
The Planner decides *what* to retrieve and *why* (subtasks, objectives, source types). The KML Retrieval Gateway decides *how* to retrieve it (depth, strategy, thresholds). The Planner can override defaults via the Retrieval Plan but isn't required to. KPPS/KROS/KASCS all inherit this boundary: Planner does educational reasoning, Gateway does retrieval mechanics.

## Legacy corpus vs KML migration
KMAS Step 1 (register existing corpus) and Step 5 (route through Retrieval Gateway) apply only to the new knowledge pipeline (Program B). The legacy Biology corpus stays in ChromaDB, accessed directly by existing graph nodes. When a future feature needs workspace-aware retrieval of the Biology corpus, that specific query path goes through the Gateway — which talks to the same ChromaDB with layer context added. No backfill unless/until the legacy corpus itself needs workspace integration.

## Knowledge Object (storage model)
Knowledge Object is a metadata record in PostgreSQL (identity, lifecycle state, ownership, provenance). Chunks remain in ChromaDB tagged by `knowledge_object_id`. The existing `VectorStoreAdapter.search()` path is unchanged — it queries ChromaDB as before. The KML Retrieval Gateway enriches search results by joining the chunk's `knowledge_object_id` with PostgreSQL metadata. New pipeline (Program B) creates KO records; legacy corpus has none.

## Knowledge Lifecycle states (user-visible)
Collapsed to 6 user-visible states: Uploaded → Processing → Published → Active → Archived → Deleted. Intermediate pipeline states (Validated, Registered, Enriched, Indexed) are internal progress, emitted as granular events for observability but not surfaced to the KO record. Users see "Processing" with a progress bar, not individual stage hops.

## Knowledge Relationships (split strategy)
Two categories: structured adjacency tables for high-frequency query-heavy types (prerequisites, alignment, derivation) using the ADR-0007 pattern, and a single generic `knowledge_relationships` table (source_id, target_id, relationship_type ENUM, metadata JSONB) for low-frequency types (contradicts, duplicates, belongs_to). Structured tables: `knowledge_prerequisites` (prerequisite_of, depends_on), `knowledge_alignment` (aligned_with, extends), `knowledge_derivation` (summarizes, explains, references, supersedes).

## Permissions (workspace-level only)
Permissions are enforced at workspace level (KWCAS membership model), not object level. Object-level ownership and viewer access inherit from the workspace the KO belongs to. The KLDMS object-level role table is a computed projection of workspace membership, not a separate table. AI Agent inherits the requesting user's permissions.

## KPPS Processing Queue (Redis Streams)
The processing queue uses Redis Streams (`knowledge:processing` consumer group) matching existing Redis infra. Workers for extraction, enrichment, chunking, embedding, indexing consume from this stream. Domain events (KnowledgePublished, KnowledgeArchived) continue using the existing `EventLogger` subscriber pattern for in-process consumers. No Kafka/RabbitMQ per ADR-0006.

## KPPS Content Extraction & Chunking
Stage 4 wraps existing `src/ingestion/` processors (docling, OCR, diagram) as Redis Stream consumers with no internal changes. Stage 5+7 replaces the existing token-based chunker with a new structure-aware chunker for the KML pipeline only (chapters → sections → topics → paragraphs → token limit). The existing token-based chunker stays for the legacy pipeline.

## KPPS Educational Enrichment (async)
Stage 6 runs asynchronously after publication. Pipeline publishes with minimal deterministic metadata (subject, grade, language) and a `status: enrichment_pending` flag. A separate enrichment worker extracts AI metadata (Bloom's, objectives, concepts, prerequisites) and updates the KO record. Program E workflows check enrichment status before generating artifacts. Stage 11 (Background Intelligence) triggers Program E subscribers on `KnowledgePublished` — it's a coordination pattern, not a separate generator implementation.

## KPPS Validation
Three lightweight checks: format rejection (unsupported types), size rejection (configurable limit), and checksum duplicate warning (SHA-256 against KOs in target workspace — creates a new version rather than silently duplicating). All non-blocking for pipeline entry.

## KPPS Relationship Extraction (async)
Stage 8 runs as part of the async enrichment workflow (not blocking publication). Outputs go into the `knowledge_relationships` generic table (KLDMS split strategy). Only free-form KO-to-KO relationships (`explains`, `summarizes`, `references`, `contradicts`, `supersedes`, `aligned_with`). The existing `TopicPrerequisite` model stays untouched — it governs curriculum-level prerequisites that are pre-defined, not AI-extracted.

## Evidence Package (KML path only)
Evidence Package is a new Pydantic model for the KML path only. Existing agentic path (`EvidenceGraphNode → SufficientContextNode → SynthesisNode → TutorNode`) keeps its current `evidence_items` dicts unchanged. Knowledge Router facade translates between the two when invoked by new consumers.

## Conflict Resolution (deferred)
Deferred to Phase 2. Phase 1 uses implicit trust via existing confidence scoring (`src/core/evidence/scoring.py` source quality weights: curriculum=0.95, memory=0.75, etc.) without explicit conflict detection. Reasoning agents receive evidence sorted by confidence — higher-confidence sources are presented first, both remain available for citation. Explicit conflict detection (flagging contradictory sources) comes when usage patterns justify it.

## Retrieval Hierarchy (layer priority on SearchFanout)
Layer priority is a pre-filter parameter on SearchFanout. KML Gateway passes `layer_priority` — SearchFanout queries layers in priority order and stops when `SufficientContextNode` threshold is met. Legacy path continues querying all layers in parallel (current behavior). Additive parameter change with default "all parallel" for backward compatibility.

## Workspace wraps ClassGroup
New `workspaces` table with nullable `class_group_id` FK to existing `ClassGroup`. When a teacher workspace is seeded from a ClassGroup, membership and context metadata are copied from the group. ClassGroup stays unchanged for legacy pipeline. New features use `workspaces` directly.

## Workspace Membership
Single `workspace_members` table (user_id, workspace_id, role ENUM). Seeded from ClassGroup: teacher_id → Owner+Teacher roles, enrolled students → Student role. After seeding, KWCAS membership logic applies (invitations, role changes). Existing `classroom_enrollments` stays as authoritative enrollment record for legacy pipeline.

## Multi-tenancy (org_id on workspace, deferred isolation)
Add `organization_id` (nullable) to `workspaces` table for Phase 1. ChromaDB stays shared; PostgreSQL isolation is natural via FK relationships (workspace → members → KO). Physical isolation (separate ChromaDB collections per org) deferred until volume proves it necessary. No `organization_id` on KO records — workspace membership is the isolation boundary.

## KASCS Services (logical packages, not microservices)
KASCS services are logical Python packages within the existing FastAPI monolith. Each has a public `__init__.py` exporting the service class, private internal modules, and no direct access to other services' tables (convention-enforced, not deployment-isolated). Existing `src/` modules superseded by a KASCS service get a thin wrapper package that delegates to existing code until migration is complete. These logical boundaries map 1:1 to future microservices if needed.

## Workspace Context Header (X-Workspace-Id)
Workspace context is a separate HTTP header, not embedded in the JWT. The API Gateway/BFF validates workspace membership and injects resolved workspace context into downstream services. Workspace switching is lightweight (no re-auth).

## Program A build order (Strangler Fig)
A1 (Knowledge Registry) built first — foundation for everything. A2 (Workspace Service) and A3 (Storage MVP) and A4 (scoped Event Infrastructure) built in parallel after A1. A3 MVP: file/blob storage for raw uploads only. A4 scoped: Redis Streams consumer group for pipeline, EventLogger for domain events — no DLQ, no external broker. A5 (Observability MVP): structured logging + pipeline stage metrics only; distributed tracing and dashboards deferred.

## Storage Platform (local FS + adapter interface)
MVP uses local filesystem (`./data/storage/{workspace_id}/{ko_id}/{filename}`) with a `StorageAdapter` interface (`store/retrieve`). S3/MinIO support added via the same interface when multi-server deployment warrants it.

## Upload Service endpoint
New `src/api/knowledge.py` router at `/api/v1/knowledge/upload`. POST multipart with file, workspace_id, collection_id (optional). Delegates to KML services: KnowledgeRegistry.register(), StorageAdapter.store(), emits KnowledgeUploaded to Redis Stream. Returns `{knowledge_object_id, status: "processing"}`. No existing router files modified.

## Knowledge Publication (gates on mandatory chain only)
Publication waits for mandatory chain: Validation → Parsing/OCR → Chunking → Embedding → Indexing. KO transitions to Published with `enrichment_status: pending`. Async enrichment (educational metadata, relationships) updates `enrichment_status: complete` later, emitting `KnowledgeEnriched`. Subscribers that need full metadata check `enrichment_status` before generating artifacts.

## Citation Engine (additive CitationFormatter)
New `CitationFormatter` service that transforms Evidence Package records into structured citations (source title, workspace, confidence badge, chunk excerpt). Consumed by: KML Gateway (new consumer responses), TutorNode via adapter (when workspace context available), frontend Program D (citation display). No existing `format_context()` code modified.

## Workspace pages (/workspace/*, V2 design)
New top-level routes under `/workspace/` using DashboardV2 design tokens directly (not `/v2/` prefix). Sidebar gets new "Workspace" section: Dashboard (D1), Upload (D2), Browse (D3), Search (D5), Processing (D6). Collections (D4) and Version History (D7) are sub-pages of Browse. Metadata Editor (D8) is a panel/overlay on KO detail.

## Processing progress (polling)
Frontend polls `GET /knowledge/{id}` every 3s for KOs in non-terminal state. Endpoint returns `lifecycle_state`, `enrichment_status`, `progress: {current_stage, total_stages, completed_stages}`. Polling stops once Published/Archived/Deleted. Processing dashboard (D6) fetches recent KO list with same status fields. SSE deferred — polling sufficient for MVP.

## Program E epics (existing stay legacy, KML additive)
Existing features (E4 QuizGen, E7 LessonPlanner, E8/E9 KnowledgeGraph) stay on legacy path with no changes. KML-enhanced versions are additive — new endpoints/parameters for workspace-aware consumers. E1 (Metadata Intelligence) is met by KPPS Stage 6 async enrichment. E2, E3, E5, E6 are net-new agents consuming KML Evidence Packages.

## Program F existing epics stay on ClassGroup
Existing F1 (Classroom Management) stays on `ClassGroup` for all current functionality. The workspace layer (wrapping ClassGroup) provides the same data for new workspace-dashboard consumers (Program D). No F1 rewrite. Net-new epics (F2 Assignments, F5 Classroom AI, F10 Calendar) use workspace model from day one.

## Program G (Strangler Fig rollout)
No cutover migration. Each KML feature goes live independently alongside existing system. G2 one-time script seeds workspace_members from existing ClassGroups. G1 per-epic feature flags (`kml_upload`, `kml_workspace_dashboard`). G3 (Knowledge Migration Pipeline), G4 (Compatibility Layer), G7–G10 removed — Strangler Fig achieves zero-downtime, no-data-loss, safe-rollback by design.

## Knowledge Registry interface (synthesized)
8 methods: `register`, `get`, `list`, `update_lifecycle`, `update_metadata`, `soft_delete`, `create_version`, `list_versions`. Typed lifecycle transitions. Events emitted as side-effect to EventLogger after commit (not event-sourced storage). Simple PG CRUD under the hood with auto-versioning on content changes. Metadata stored as JSONB dict.

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

## Educational Knowledge Graph Strategy (PRD-003)
Named adjacency tables in PostgreSQL with recursive CTEs instead of a generic Graph Abstraction Layer. Each relationship type gets its own table (`topic_prerequisites`, `student_misconceptions`, `intervention_outcomes`, `topic_misconceptions`). Prerequisite chain traversal uses `WITH RECURSIVE` CTEs. The graph builder/reasoning/query interfaces operate over named tables — no generic node/edge store. See ADR-0007.

## Educational Event System (MVP)
Minimal logging approach. No dedicated event bus. A lightweight `memory_events` log table with (user_id, event_type, topic, metadata JSONB, created_at). Existing event-like records (`QuizAttempt`, `RecoveryNotification`, `TopicMasteryHistory`, `FeedbackEvent`) handle domain-specific events. Full event-driven architecture deferred.

## Event Bus Strategy (PRD-002)
PRD-002's full Event Bus (publisher/broker/subscriber/registry/replay) is **not implemented as specified**. Instead, the existing `EventLogger` is evolved with schema validation and an in-process subscriber registry. Rationale: the current platform is a single deployed service (monolith) — a dedicated broker/queue/replay layer would be premature abstraction. The `MemoryEvent` table already serves as an append-only event store queryable via JSONB. The full event-driven architecture (Redis Streams → Kafka) will be introduced when multiple independent services require decoupling. See ADR-0006.

## Memory Event Storage
Flat JSONB column on `memory_events.event_metadata` rather than normalized `memory_event_metadata` / `memory_event_links` tables. Chosen because event metadata is inherently heterogeneous per event type. Queryable via PostgreSQL JSONB operators `@>` and `->>`. GIN indexing is available but deferred until query patterns emerge. See ADR-0005.

## Teacher Copilot Pipeline (PRD-004)
New LangGraph pipeline at `src/core/teacher_copilot/` with dedicated nodes for intent routing, educational reasoning, evidence engine, and response generation. Separate from the student tutoring pipeline but reuses shared infrastructure (memory layer, knowledge graph, learning intelligence, evidence graph). The pipeline supports 5 MVP Copilot Skills: Student Intelligence, Classroom Intelligence, Intervention Guidance, Curriculum Analysis, and Assessment Generation. Not a thin REST wrapper — the pipeline handles multi-source reasoning chains that cross memory, graph, and analytics boundaries.

**Pipeline Bugfix:** The original pipeline had `GatherDataNode` returning empty evidence (`[]`) and `ReasonNode` passing `None`/`[]` for all educational data. Both are now wired to `EvidenceEngine.gather_evidence()` (via `async_session_factory` for DB access) and pass structured data through the state to `ReasoningEngine.reason()`. The backend API also gained `GET /recovery/last-plan` at `src/api/recovery.py` for frontend convenience.

## Agent Memory Integration Strategy
Current agents (TutorAgent, QuizAgent, PlannerAgent) access memory via the existing `/memory/*` REST API. The formal `AgentMemoryClient` abstraction with `AgentMessage` protocol (PRD-010) is deferred until the Agent Orchestrator framework is built. The existing API surface is sufficient for current consumers and avoids building abstractions before the first multi-agent consumer (Teacher Copilot) exists. PRD-001's Phase 3 (Agent Integration) is subsumed by PRD-010.

## Procedural Memory (EMAS v1)
Not implemented. No table, no manager, no API. EMAS v1's "what works" strategy store is novel and has no precedent in the codebase. Deferred until Teacher Copilot usage patterns inform what strategies look like in practice.

## Memory Consolidation Engine
Not implemented. PRD-001's Phase 2 (daily → weekly → monthly → quarterly consolidation) has no code, no scheduled job, no scripts. The `consolidated_at` column on `semantic_facts` exists but is never written to. The session-level `Summarizer` at `src/core/memory/summarizer.py` handles per-session summarization, but cross-session aggregation is missing.

## Memory Service ABC
Removed. The `MemoryService` ABC at `src/core/memory/service.py` was a Wave-0 stub with 0 concrete implementations and 0 consumers. The real services (`RetrievalOrchestrator`, `SessionManager`, `EventLogger`, `SemanticFactManager`) don't inherit from it. The dead `src/core/learning_intelligence/schemas/` directory was also removed (empty schemas with no consumers).

## Vector Memory Store
Uses ChromaDB via `MemoryVectorStore` instead of pgvector as EMAS v1 specifies. The `VectorStoreAdapter` interface makes this swappable. Migration is deferred until ChromaDB proves insufficient.

## Pattern Retrieval Mode
PRD-001 specifies 5 retrieval modes. Direct, Semantic, and Timeline are implemented. Pattern (anomaly detection over memory events) and full Historical ("why is this student struggling" reasoning) are missing.

## Semantic Facts
Single `semantic_facts` table as the Semantic Memory Store, replacing the PRD-001's planned three-table normalized schema (semantic_memories + semantic_entities + semantic_relationships). Covers unstructured educational facts not stored in existing models (StudentMastery, MisconceptionPattern, StudentAbility, MemoryEducationalSummary): behavioral patterns, teacher/classroom preferences, discovered learning patterns. Table has user_id, fact (text), confidence (float 0-1), source, category (behavior/preference/pattern), expires_at. Entity/relationship graph semantics deferred to Educational Knowledge Graph (PRD-003).

## TopicPrerequisite Model
Adjacency table at `src/database/models.py` mapping topic→prerequisite relationships. Fields: `topic_id`, `prerequisite_topic_id` (both FK to `curriculum_topics`), `relationship_type` ("prerequisite"/"corequisite"/"recommended"), `grade_level`. This is the concrete implementation of the Educational Knowledge Graph Strategy — named adjacency tables per relationship type, no generic node/edge store. See ADR-0007.

**Model cleanup:** 5 duplicate model classes were removed from `models.py` that were defined a second time (same name, same/similar fields) causing Alembic autogenerate confusion: `TopicPrerequisite`, `SemanticFact`, `InterventionAssignment`, `InterventionKnowledgeEntry`, `MisconceptionKnowledgeEntry`. The broken FK `ForeignKey("classrooms.id")` → `ForeignKey("class_groups.id")` in the intervention models was also fixed. A duplicate `last_built_at` column on `StudentDigitalTwin` was removed.

## RelationshipBuilder
CRUD service at `src/core/knowledge_graph/builder/` for managing prerequisite edges. Supports single/batch add, get prerequisites and dependents, and removal. Each operation validates against existing edges to prevent duplicates.

## GraphReasoningEngine
Service at `src/core/knowledge_graph/engine.py` using `WITH RECURSIVE` CTEs for:
- **Prerequisite chain** — traverse `topic_prerequisites` upward (what must I know before this topic?)
- **Dependent chain** — traverse downward (what topics depend on this one?)
- **Gap analysis** — intersect prerequisite chain with `student_mastery` to find unmastered prerequisites

Both CTEs use cycle detection via `path` arrays to prevent infinite loops. Depth-limited to 5 levels by default.

## EKG API
`APIRouter(prefix="/ekg")` at `src/api/ekg.py`. 9 endpoints: CRUD for prerequisites (single/batch/list/delete), chain traversal (prerequisite/dependent), gap analysis, and topic listing.

**Registration fix:** This router was imported but never registered in `main.py` — all 9 endpoints were unreachable. Now registered alongside the legacy graph router.

## Timeline Memory Retrieval
Chronological endpoint `GET /memory/timeline/{user_id}` that composites events + summaries + semantic facts into a date-sorted narrative. Thin compositing layer over existing tables — no new storage. Powers Teacher Copilot's "Show me what happened" and classroom timeline features. Builds on top of the existing event/summary/semantic_facts tables.

## Event Schema Registry
8 known event types with validated field schemas in `SCHEMA_REGISTRY` at `src/core/memory/event_logger.py`: `session_started`, `quiz_completed`, `lesson_viewed`, `recovery_task_done`, `misconception_detected`, `xp_awarded`, `streak_updated`, `achievement_unlocked`. Each schema defines `required_fields`, `optional_fields`, and typed `metadata_schema`. Unknown event types are accepted with a warning — the registry is additive, not restrictive. Implemented per ADR-0009.

## Event Subscriber Registry
In-process callback registry on `EventLogger._subscribers`. Handlers register via `subscribe(event_type, handler)` or `subscribe_all(handler)` for all event types. On each `log()` call, subscribers are notified asynchronously with `(event_type, user_id, metadata, event_id)`. Supports both sync and async handlers. Errors in one subscriber don't affect others. Designed for monolith-scale — no external broker, no persistence, no replay. Full event bus (Redis Streams → Kafka) deferred to Wave 8+ of ROADMAP.md. Implemented per ADR-0009.

## Misconception Intelligence
Dedicated package at `src/core/misconception_intelligence/` with two components:
- **HeuristicDetector** — Scans LLM response text for 19 `MISCONCEPTION_INDICATORS` phrases, extracts correction sentences. Same logic as the inline `detect_misconception()` in the tutor modules, but reusable.
- **MisconceptionProfiler** — Aggregates `MisconceptionPattern` records into a student profile (by topic, frequent patterns, improvement trend). Supports resolving individual patterns or by-topic bulk resolution.

5 API endpoints under `/misconceptions/`: list (with resolved/topic filters), profile, analyze (heuristic text), resolve, resolve-topic. Dashboard component at `dashboard/src/components/misconceptions/MisconceptionPanel.tsx`.

**Registration fix:** The misconceptions, intervention, and teacher_copilot routers were all imported but never registered in `main.py` — their endpoints were unreachable. All are now registered.

## Teacher Copilot Dashboard
Chat UI at `dashboard/src/app/copilot/page.tsx` with example prompts, intent badges, evidence source citations, and streaming-style response display. Uses the `POST /copilot/query` endpoint with a 60s timeout. Follows DashboardV2 design language.

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

## Memory Consolidation Pipeline
Time-triggered background pipeline (cron/APScheduler) that runs daily, groups memory events by user+period, and generates consolidated summaries at daily → weekly → monthly → quarterly levels. Distinct from the session-level `Summarizer` — consolidation operates on aggregated events, not individual tutoring sessions. Implemented as `src/core/memory/consolidation/` with `scripts/run_consolidation.py`. Event-triggered and on-demand consolidation are future extensions.

## Memory Lifecycle Engine (MVP)
Not implemented as a dedicated subsystem for MVP. Replaced by simpler strategies: recency-weighted retrieval ranking, periodic summary compression (via consolidation pipeline), spaced-repetition-based confidence decay, and a retention policy (keep N most recent session summaries per user). Full lifecycle engine deferred until data volume warrants it.

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

## ContinueLearningFeed
Read-only computed projection over Recommendation Engine output. Groups recommendations by action_type into sections (recovery_actions, review_actions, quiz_opportunities, tutor_actions). Not persisted — generated on read. Contains `primary_action`, `sections` dict, and `summary` (estimated_minutes + xp_available).

## ContinueLearningService
Single service at `src/core/learning_intelligence/continue_learning/service.py`. No separate journey builder or action grouping modules. Calls `RecommendationService.get_recommendations()`, groups results by action_type, picks highest-scoring as primary action, decorates cards with estimated_minutes and xp_reward, attaches summary.

## LearningCard
Navigational display unit wrapping a `LearningRecommendation`. The `id` is the recommendation's UUID. XP is awarded by the underlying activity (quiz, recovery task, etc.), not by clicking the card. Cards are navigational only — they route to the relevant page.

## Feed Sections (Dynamic)
Sections render only when the Recommendation Engine has matching recommendations for that action_type. No independent generation logic per section. Empty state: when no recommendations exist, primary_action becomes a "Start with a Quiz" prompt with "Ask the Tutor" as secondary action.

## Activity Duration Lookup
`ACTIVITY_DURATION_LOOKUP` dict keyed by `LearningActionType` in the feed generator. Values are minutes (e.g., REVIEW_TOPIC=10, TAKE_QUIZ=15). Overridable via recommendation metadata.

## Card XP Reward
Sourced from `XP_SOURCES` in `src/api/gamification.py` mapped by activity type via `ACTION_TYPE_TO_XP_SOURCE_KEY`. Null when the action type has no corresponding XP source. The card shows "available XP" without awarding it.

## DailyLearningPath
Not a separate endpoint. The frontend derives duration and total XP from the `summary` field on `ContinueLearningFeed`. Feed response includes `summary: FeedSummary(estimated_minutes, xp_available)`.

## Tutor Integration (Next Action)
Frontend-appended. Dashboard and Telegram bot call `GET /intelligence/next-action/{user_id}` after rendering the tutor response and append a "Next: [action]" line. No LangGraph pipeline changes — recommendation is navigational, not pedagogical.

## Telegram Proactive Reminders
`scripts/send_proactive_reminders.py` run via cron. Follows the `send_digests.py` pattern. Single daily check for due reviews + active recovery plans. Sends via `telegram.Bot.send_message()` using the bot token from config. Only to users with a non-null `telegram_id`. Idempotent and safe to run multiple times.

## Completion Tracking
No dedicated completion-log table. Success is measured via existing downstream activity tables (QuizAttempt, RecoveryTask, SpacedRepetitionSchedule). Single structured log line for `continue_learning_generated` events. Detailed metrics deferred to a future analytics pass.

## ExamReadinessProfile
Computed, read-only profile answering "if the student took an exam today, how prepared are they?" Contains overall_readiness (0-100, average of topic readiness scores), readiness_band (Critical/Developing/Ready/Strong), topic_readiness list, and risk_topics list. Not persisted — generated on read from LearnerSnapshot.

## ReadinessService
Single service at `src/core/learning_intelligence/readiness/readiness_service.py`. Consumes LearnerSnapshot, computes per-topic readiness (from mastery average_score), determines risk factors (overdue_review, active_misconception, low_ability) via boolean checks on snapshot fields, derives risk_level from factor count (0=LOW through 3+=CRITICAL), assigns readiness_band from score range, and returns ExamReadinessProfile. No blended formula — readiness = actual performance.

## Topic Readiness Score
Per-topic readiness = `StudentMastery.average_score` (0-100). No weighted formula. Risk factors are overlays on top of the score, not math inside it. Empty state: when no mastery data exists, overall_readiness=0, band=Critical, empty topic list.

## Readiness Risk Factors
Three boolean checks against LearnerSnapshot: `overdue_review` (any due_review with next_review_at < now), `active_misconception` (any misconception with frequency >= 3), `low_ability` (ability_score < 0.3 or uncertainty > 2.0). Risk level derived from count: 0=LOW, 1=MODERATE, 2=HIGH, 3+=CRITICAL. Risk topics are those with HIGH or CRITICAL level.

## Readiness Bands
Score-to-band mapping: 0-39=Critical (high risk of failure), 40-59=Developing (significant preparation required), 60-79=Ready (reasonably prepared), 80-100=Strong (exam-ready). Same range structure as StudentMastery severity but with different semantics (prediction vs assessment).

## Continue Learning Readiness Integration
`ContinueLearningService.get_feed()` accepts optional `readiness_profile`. When provided, risk topics (`HIGH` or `CRITICAL` risk level) receive a +0.3 priority boost in their `LearningCard.priority_score` and `exam_impact` is set to `"high"`. The feed is re-sorted so risk-topics cards surface before same-score non-risk cards. Graceful degradation when readiness data is absent.

**Bugfix:** The readiness-boosted sort was silently overwritten by a second `sorted()` call that received the unboosted feed. The dead-call overwrite was removed from `continue_learning_router.py:37`.

## Readiness Boost Formula
Risk topics get `priority_score * 1.3` (30% boost) capped at 100. The boost is multiplicative so high-priority items get more absolute lift. Cards from non-risk topics are untouched. Sorting is stable — original Recommendation Engine priority order is preserved within each band.

## ClassroomProfile
Computed, read-only projection of classroom-wide educational intelligence. Generated on read — not persisted. Contains classroom_id, generated_at, total_students, average_readiness (0-100), readiness_distribution (count per band), risk_students list, intervention_candidates list, mastery_heatmap (topic → avg score).

## Classroom Health Score
The `average_readiness` field on `ClassroomProfile`. Computed as the mean of all enrolled students' `ExamReadinessProfile.overall_readiness` values. Students with no readiness data are skipped. 0-100 scale, inherits readiness band semantics (0-39=Critical, etc.).

## Readiness Distribution
Count of enrolled students per readiness band (Critical/Developing/Ready/Strong). Derived from each student's `ExamReadinessProfile.readiness_band`. The bands inherit their semantics from Readiness Bands.

## Mastery Heatmap
Per-topic average readiness score across all students in a classroom. Computed by grouping each student's `TopicReadiness.readiness_score` by topic and taking the mean. Not a separate model — a `dict[str, float]` field on `ClassroomProfile`.

## Intervention Queue
Sorted list of `Intervention` models (from readiness module) across all risk students in a classroom. Sorted by priority descending. Consumed by the teacher dashboard intervention widget. Empty when no students are at risk.

## TeacherService
Single service at `src/core/learning_intelligence/teacher/teacher_service.py`. Composes `ReadinessService` internally. Generates `ClassroomProfile` by calling readiness per student in parallel via `asyncio.gather()`. No separate engine files — aggregation logic lives in private methods on the service.

## Classroom API
`APIRouter(prefix="/teacher")` at `src/api/teacher.py`. Endpoints: classroom CRUD (create/list/roster/enroll) and intelligence (overview/risk-students/interventions/mastery-heatmap). Teacher ownership enforced via `_verify_teacher_owns_classroom()` helper returning 404 on mismatch.

## School
Database model at `src/database/models.py`. Simple table: id, name, created_at. Related to ClassGroup via school_id FK.

## SchoolProfile
Computed, read-only projection of school-wide educational intelligence. Generated on read by SchoolService. Contains school_id, generated_at, total_teachers, total_classrooms, total_students, avg_health, health_distribution (count per readiness band), teacher_metrics list, at_risk_classrooms list.

## SchoolHealthSnapshot
Database model storing daily health snapshots for trend lines. Columns: school_id, snapshot_date, avg_health, total_students, at_risk_count. Unique constraint on (school_id, snapshot_date).

## SchoolService
Single service at `src/core/learning_intelligence/school/school_service.py`. Composes `TeacherService` internally. Generates SchoolProfile by loading all class groups for a school and aggregating readiness profiles per student in parallel via asyncio.gather. Also handles snapshot creation and trend queries.

## ParentChild
Association table (`parent_children`) linking parent Users to student Users. Self-referential M2M via `User.children` and `User.parents` relationships on the User model. Constraints: composite PK on (parent_id, student_id).

## Parent API
`APIRouter(prefix="/parent")` at `src/api/parent.py`. Endpoints: `GET /parent/children` (list linked students with readiness), `GET /parent/children/{id}/progress` (mastery, quiz history, streak), `GET /parent/children/{id}/weekly-summary` (generate or fetch cached weekly report via `ParentSummaryAgent`). Auth guards: `_require_parent_role` + `_verify_child_ownership`.

## AgenticRAGState
Extended `AgentState` with additional fields for the Google-style Multi-Agent Agentic RAG platform. Adds `execution_plan`, `subtasks`, `rewritten_queries`, `evidence_ids`, `sufficiency_score`, `requires_planning`, and other state fields. Owned by the Agentic RAG pipeline but backward-compatible with the existing LangGraph pipeline.

## EvidenceGraph
Central evidence registry for the Agentic RAG platform. Persistent PostgreSQL repository — evidence is a first-class system artifact, not transient retrieval output. Sessions define provenance boundaries; the repository defines persistence. Stores full chunk content (not just references) for auditability and reproducibility. Hierarchy: `trace_id → session_id → evidence_id`. See ADR-0004.

## EvidenceRecord
Single immutable evidence unit. Contains: `id`, `trace_id`, `user_id`, `session_id`, `source_type` (curriculum/memory/learner_profile/misconceptions), `source_name`, `chunk_id`, `content` (full text), `original_query`, `retrieval_query`, `retrieval_score`, `rerank_score`, `confidence`, `retrieved_by`, `archived`, `expires_at`. Never deleted — only archived.

## EvidenceSession
Execution boundary for a single graph run. Groups EvidenceRecords by query/execution. Fields: `id`, `user_id`, `session_id`, `trace_id`, `status` (active/closed), `created_at`. A session is the grouping boundary, not the storage boundary.

## EvidenceSelector
Component that selects the top evidence bundle for generation. Ranks evidence by coverage contribution, confidence, source quality, relevance, and diversity. Caps at ~8-10 records per generation to fit context window. Operates between the Evidence Graph and the Tutor Synthesis Agent.

## PlanExecutor
LangGraph node that orchestrates sequential subtask execution. Runs `Rewriter → Fanout → Retrievers` per subtask, with parallel retrieval within each subtask. Manages the loop until all subtasks complete or stopping criteria are met.

## ClaimVerifier
Node between Tutor and Safety in the Agentic RAG pipeline. Extracts factual claims from the tutor's draft response, verifies each against the top evidence bundle, and calculates a groundedness score. Routes to `revise` if >20% unsupported, `reject` if >50% unsupported, `finalize` otherwise. Skips verification when `requires_planning=False` or `socratic_mode=True`.

## SocraticEvidenceBundle
Cached evidence for an active Socratic session. Populated on the first Socratic turn (which goes through the full Agentic RAG pipeline), then reused for follow-up turns without re-planning or re-retrieval. Managed via `socratic_session_active`, `socratic_evidence_bundle_id` state fields.

## QueryRewriter
LangGraph node that expands and refines retrieval queries for better evidence coverage. Supports single-query, multi-query, and cross-lingual expansion (English/Amharic). Decomposes complex queries into sub-queries based on plan subtasks. Routes to appropriate retriever based on query and subtask type.

## SearchFanout
LangGraph node that retrieves evidence from multiple indices in parallel. Supports curriculum, evidence, and cross_session indices. Deduplicates chunks across indices by content hash. Ranks results by score and returns top N results.

## SufficientContextNode
LangGraph node that evaluates whether collected evidence is sufficient to answer the user's question. Returns SUFFICIENT, MINOR_GAP, or MAJOR_GAP. Routes to tutor, rewrite (minor gaps), or replan (major gaps). Uses heuristic evaluation based on evidence count and coverage.

## ClaimVerifierNode
LangGraph node that extracts factual claims from tutor's response and verifies them against evidence. Calculates groundedness score. Routes to finalize, revise, or reject based on groundedness. Phase 1: heuristic verification. Phase 2+: LLM-based verification.

## PipelineMonitor
Monitoring and observability for Agentic RAG pipeline. Provides trace_id generation, performance metrics, and pipeline tracing. Tracks node-level timing, status, and metadata. Logs structured traces for observability.

## Unified Graph
Single graph that handles both legacy and agentic pipelines. Routes based on `requires_planning` after OrchestratorNode. Legacy pipeline: retrieve → tutor → safety. Agentic pipeline: planner → plan_executor → sufficient_context → tutor → claim_verifier → safety. Includes iterative retrieval loop and claim verification.

## Diagnostic Assessment
`POST /quiz/diagnostic` endpoint (`src/api/diagnostic.py`). Generates a multi-topic baseline pre-test by creating one `Quiz` per requested topic, all at EASY difficulty. Returns per-topic baselines with `TopicBaseline` (topic, score, total, correct, severity, questions). Overall severity is "pending" until the student submits answers via the standard `POST /quiz/submit` flow. See ADR-0010.

## Exit Ticket
Optional structured assessment appended to lesson plans. Three questions (MC/TF/short_answer) generated after the lesson plan by `LessonPlannerAgent._generate_exit_ticket()`. Triggered by `generate_exit_ticket: true` in the lesson plan request. Not persisted in the `LessonPlan` table — computed on-the-fly per generation. See ADR-0010.

## Teacher Copilot Assessment Route
Conditional edge in the Teacher Copilot pipeline (`src/core/teacher_copilot/pipeline.py`). When `IntentRouter` classifies a query as `assessment_creation`, the pipeline routes to `AssessmentCreatorNode` instead of the standard gather→reason path. Extracts grade (via regex) and topic (via keyword matching) from natural language, then calls `QuizAgent.generate()` to produce a real assessment. The generated questions are rendered in the response text.

## InterventionAssignment
Persisted database model at `src/database/models.py` for teacher-facing intervention tracking. Full lifecycle: `planned → active → completed | cancelled`. Fields: user_id, classroom_id, teacher_id, intervention_type (REVIEW_TOPIC, REVISE_MISCONCEPTION, RECOVERY_PLAN, TAKE_QUIZ, EXAM_PRACTICE, TUTOR_SESSION, ENGAGEMENT_BOOST), topic, priority (0.0-1.0), estimated_impact (0-100), effectiveness_score (nullable, computed after completion). See ADR-0011.

## InterventionAnalytics
Aggregated analytics endpoint `GET /interventions/analytics/summary`. Returns total_interventions, completed_count, active_count, completion_rate (%), average_effectiveness (%), effectiveness_by_type (dict), and effectiveness_by_topic (dict). Computed on-read by filtering completed interventions with non-null effectiveness scores and grouping by type/topic.

## Intervention Effectiveness
Computed by `InterventionService.compute_effectiveness()` which queries `StudentMastery` records before and after the intervention's `assigned_at` date. The difference in `average_score` becomes the effectiveness score (clamped 0-100). Requires pre-existing mastery data — returns `null` when unavailable.

## Lesson Differentiation
Three-track differentiation generated by `DIFFERENTIATION_PROMPT` in `LessonPlannerAgent`. Triggered by `generate_differentiation: true`. Creates three `DifferentiationActivity` objects per lesson: support (scaffolded), standard (grade-level), advanced (extended). Each has group, description, duration_minutes. Not persisted — computed on-the-fly. See ADR-0012.

## Diagram Suggestion
Topic-matched diagram suggestions generated by `DIAGRAM_SUGGESTION_PROMPT` in `LessonPlannerAgent`. Triggered by `generate_diagram_suggestions: true`. Returns `DiagramSuggestion` objects with title, description, and diagram_type (flowchart/labeling/concept_map/comparison/process/anatomy). Descriptive only — no diagram files are created. Future integration with the existing diagram labeling module. See ADR-0012.

## Assessment Studio
Dashboard page at `dashboard/src/app/assessment-studio/`. Aggregates all assessment types (diagnostic, quiz, adaptive quiz, exit ticket, teacher copilot assessment) with creation UI, status indicators, and reference table. Sidebar link under "Assessments" icon for admin/teacher roles.
