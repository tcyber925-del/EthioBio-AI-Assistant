# ADR-0001: Evidence Graph Stores Full Chunk Content

## Status

Accepted

## Context

Most RAG systems store only chunk references (IDs) in the evidence registry. The actual content is looked up on demand from the vector store. However, for EthioSci's Agentic RAG, evidence needs to be:

- **Immutable**: Vector store contents may change (re-indexing, deletion)
- **Self-contained**: No dependency on external store for verification
- **Auditable**: "What evidence supported this answer?" must be answerable
- **Reproducible**: Same evidence must produce same result regardless of vector store state

## Decision

Store the full chunk `content` alongside `chunk_id` in the `evidence_records` table.

The `EvidenceRecord` schema contains:

```python
class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    id: UUID
    session_id: UUID
    source_type: str
    source_name: str
    chunk_id: str | None        # reference to vector store
    content: str                # full chunk text (NEW)
    original_query: str
    retrieval_query: str
    retrieval_score: float
    rerank_score: float
    confidence: float
    retrieved_by: str
    created_at: datetime
```

## Consequences

### Positive

- Evidence is immutable and reproducible
- No dependency on vector store availability for verification
- Simpler debugging and evaluation
- Supports the "grounded response" requirement

### Negative

- Larger storage footprint (mitigated by session-scoped retention for MVP)
- Slightly slower writes (mitigated by batching)

### Mitigations

- Session-scoped evidence retention limits growth
- Future: add compression for large content fields
- Future: archive old evidence sessions to cold storage

## Related

- PRD-001B: Evidence Graph Specification
- `src/core/evidence/graph.py`
- `src/database/models.py` (EvidenceRecord)
