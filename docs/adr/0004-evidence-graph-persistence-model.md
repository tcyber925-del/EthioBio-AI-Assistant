# ADR-0004: Evidence Graph Persistence Model

## Status

Accepted

## Context

The Evidence Graph is the central knowledge coordination layer of the Agentic RAG platform. It stores evidence records — immutable, self-contained pieces of retrieved content with provenance tracking.

Two competing persistence models exist:

**A: Session-scoped** — evidence is created, used, and discarded within a single graph execution. Sessions map 1:1 to queries. Storage stays lean but cross-query auditability is lost.

**B: Persistent repository** — evidence accumulates across queries. Sessions group related evidence for provenance, but the repository is the storage boundary. Enables cross-session analysis, retrieval effectiveness evaluation, and long-term audit.

The Evidence Graph is not merely temporary retrieval output. It serves multiple roles:
- Provenance store (what evidence supported this answer?)
- Evaluation store (was the evidence sufficient?)
- Audit store (what happened during this execution?)
- Observability store (which sources produced confident evidence?)
- Retrieval intelligence store (which retrieval paths perform best?)

## Decision

Choose **Option B: Persistent Repository** with session-scoped retrieval semantics for MVP.

Key principles:

1. **Evidence is a first-class system artifact.** It is not transient retrieval output. Sessions define provenance boundaries; the repository defines persistence.
2. **EvidenceRecord is immutable.** Once written, it is never modified or deleted. Lifecycle metadata (`archived`, `expires_at`) controls visibility without mutation.
3. **EvidenceSession groups execution runs.** Sessions map to a single graph execution (one query). Multiple records belong to one session. Multiple sessions can share a trace_id.
4. **trace_id links evidence to observability.** PipelineMonitor generates trace_ids. The hierarchy is: `trace_id → session_id → evidence_id`.
5. **MVP retrieval searches current session only.** Even though all evidence persists, the default retrieval scope is the current session. Future phases expand to conversation, user, and evaluation scopes.
6. **Lifecycle metadata is added now.** `retention_policy`, `archived`, `expires_at` columns are created in the initial schema to avoid future migration headaches.

## Consequences

### Positive

- Cross-session evidence analysis becomes possible (e.g., "what evidence supported meiosis remediation recommendations last week?")
- Retrieval effectiveness evaluation across queries is enabled
- Full audit trail for every answer is preserved
- No migration needed when cross-session features are implemented — data already exists
- trace_id provides direct link between observability and evidence

### Negative

- Storage grows over time (mitigated by lifecycle metadata and archiving)
- Slightly more complex retrieval logic to scope by session
- Initial MVP adds lifecycle columns that are unused until Phase 2+

### Neutral

- Existing EvidenceRecord and EvidenceSession tables already match this model closely
- EvidenceSession already has user_id, session_id, status
- Only trace_id, archived, expires_at need to be added

## Implementation

### Schema changes

Add to `EvidenceSession`:
- `trace_id: str` — links to PipelineMonitor trace

Add to `EvidenceRecord`:
- `trace_id: str` — links to PipelineMonitor trace
- `user_id: UUID | None` — direct user reference (currently via session)
- `archived: bool` — soft-delete flag
- `expires_at: datetime | None` — automatic expiration

### Code changes

- `EvidenceGraph.add()` accepts `session_id` from caller instead of generating one
- `EvidenceGraph.get_evidence_for_session()` remains the primary MVP retrieval method
- `EvidenceGraph.delete_session()` is removed — evidence is immutable
- `Evidence` dataclass gains `trace_id`, `user_id`, `archived`, `expires_at` fields

### Retrieval scope evolution

| Phase | Scope | Method |
|-------|-------|--------|
| 1 (MVP) | Session | `get_evidence_for_session(session_id)` |
| 2 | Conversation | `get_evidence_for_conversation(trace_id)` |
| 3 | User | `get_evidence_for_user(user_id)` |
| 4 | Evaluation | `search(filters={source_type, topic, confidence, ...})` |

## Alternatives Considered

### Pure session-scoped storage

Rejected because it loses all cross-query auditability. Answer provenance, retrieval debugging, and evaluation history are impossible without persistence. "Why did the system recommend meiosis remediation last week?" cannot be answered.

### Hybrid (session store + archive copy)

Rejected as premature optimization. PostgreSQL handles the expected volume (thousands of records per user over time) without issue. Lifecycle metadata provides future archiving capability without dual-storage complexity.

## References

- ADR-0001: Evidence Graph Stores Full Chunk Content
- PRD-005: Evidence Graph
- PRD-001B: Evidence Graph Specification
- `src/core/evidence/graph.py`
- `src/database/models.py` (EvidenceSession, EvidenceRecord)
- `src/core/monitoring.py` (PipelineMonitor, trace_id)
