# PRD: Agentic RAG Phase 2 — Query Rewriter, Search Fanout, Claim Verifier

## Overview
Enhance the Agentic RAG pipeline with LLM-based query rewriting, multi-index search fanout, and claim verification. These components improve evidence coverage and factual accuracy for complex educational queries.

## Goals
1. Improve retrieval quality via LLM-based query expansion
2. Enable parallel multi-index search for better evidence coverage
3. Ensure factual accuracy through claim verification

## User Stories

### Story 1: LLM-Based Query Rewriter
**As a** student asking a complex question  
**I want** the system to expand my query for better retrieval  
**So that** I get more relevant evidence  

**Acceptance Criteria:**
- [ ] LLM expands query into 2-3 variants
- [ ] Supports cross-lingual expansion (English/Amharic)
- [ ] Decomposes multi-part questions into sub-queries
- [ ] Preserves original query as primary
- [ ] Routes to appropriate indices based on query type

**Technical Details:**
- Extend `QueryRewriterNode` with LLM calls
- Use existing `ModelRouter` for LLM access
- Store expanded queries in `AgentState.retrieval_queries`

---

### Story 2: Multi-Index Search Fanout
**As a** student with a complex question  
**I want** evidence from multiple sources (curriculum, past sessions, learner profile)  
**So that** I get comprehensive answers  

**Acceptance Curriculum:**
- [ ] Searches curriculum, evidence, and cross_session indices
- [ ] Deduplicates chunks across indices
- [ ] Ranks results by relevance score
- [ ] Returns top N results (configurable)
- [ ] Handles index-specific errors gracefully

**Technical Details:**
- Extend `SearchFanoutNode` with parallel async searches
- Use `asyncio.gather()` for parallel index queries
- Implement chunk deduplication by content hash
- Rank by weighted score (relevance + recency + diversity)

---

### Story 3: LLM-Based Claim Verification
**As a** student receiving an answer  
**I want** the system to verify factual claims against evidence  
**So that** I can trust the information  

**Acceptance Criteria:**
- [ ] Extracts factual claims from tutor response
- [ ] Verifies each claim against evidence bundle
- [ ] Calculates groundedness score (0.0-1.0)
- [ ] Routes to revise if <60% grounded
- [ ] Routes to finalize if ≥60% grounded
- [ ] Logs verification results for observability

**Technical Details:**
- Extend `ClaimVerifierNode` with LLM-based extraction
- Use existing `EvidenceGraph` for evidence lookup
- Store verification results in `AgentState`

---

### Story 4: Performance Monitoring
**As a** developer  
**I want** to monitor pipeline performance  
**So that** I can identify bottlenecks  

**Acceptance Criteria:**
- [ ] Trace ID generation for each request
- [ ] Node-level timing (ms)
- [ ] Status tracking (running/completed/failed)
- [ ] Structured logging for observability
- [ ] API endpoint for trace retrieval

**Technical Details:**
- Extend `PipelineMonitor` with trace storage
- Add `/graph/traces` endpoint for trace retrieval
- Store traces in Redis with TTL

---

## Technical Architecture

### Graph Topology (Updated)
```
orchestrator → planner → query_rewriter → search_fanout
    → sufficient_context → tutor → claim_verifier → safety
```

### New Components
1. **LLMQueryRewriter** — LLM-based query expansion
2. **AsyncSearchFanout** — Parallel multi-index retrieval
3. **LLMClaimVerifier** — LLM-based claim extraction and verification
4. **TraceStorage** — Redis-backed trace storage

### State Extensions
```python
# New fields in AgentState
expanded_queries: list[str]  # LLM-expanded queries
verification_results: dict  # Claim verification details
trace_id: str  # Request trace ID
```

---

## Implementation Plan

### Phase 2.1: LLM Query Rewriter
1. Extend `QueryRewriterNode` with LLM calls
2. Add cross-lingual expansion logic
3. Add query decomposition for multi-part questions
4. Write unit tests

### Phase 2.2: Async Search Fanout
1. Extend `SearchFanoutNode` with `asyncio.gather()`
2. Implement chunk deduplication
3. Add weighted ranking
4. Write unit tests

### Phase 2.3: LLM Claim Verifier
1. Extend `ClaimVerifierNode` with LLM extraction
2. Add evidence verification logic
3. Implement groundedness scoring
4. Write unit tests

### Phase 2.4: Performance Monitoring
1. Extend `PipelineMonitor` with trace storage
2. Add `/graph/traces` endpoint
3. Write integration tests

---

## Success Metrics
- Retrieval quality: +20% relevance score
- Evidence coverage: +30% multi-source retrieval
- Factual accuracy: ≥90% groundedness score
- Latency: <5s for complex queries

---

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| LLM latency | Cache expanded queries, use smaller models |
| Index availability | Graceful degradation, fallback to curriculum |
| Verification false positives | Tune thresholds, human-in-the-loop for critical |

---

## Dependencies
- Existing `ModelRouter` for LLM access
- Existing `VectorStoreAdapter` for retrieval
- Existing `EvidenceGraph` for evidence storage
- Redis for trace storage