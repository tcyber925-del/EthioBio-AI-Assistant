# Agentic RAG User Guide

## Overview

The EthioSci AI Assistant now includes an Agentic RAG (Retrieval-Augmented Generation) platform that handles complex educational queries requiring multi-step reasoning, iterative retrieval, and evidence verification.

## How It Works

### Simple Queries (Legacy Pipeline)
For straightforward questions like "What is photosynthesis?", the system uses the legacy pipeline:
1. **Orchestrator** classifies intent and complexity
2. **Retrieval** fetches relevant curriculum chunks
3. **Tutor** generates an answer with citations
4. **Safety** checks for hallucinations and revises if needed

### Complex Queries (Agentic Pipeline)
For multi-part questions like "Compare and contrast cellular respiration and photosynthesis, explain how they are connected, and discuss the role of mitochondria and chloroplasts", the system uses the agentic pipeline:
1. **Orchestrator** detects high complexity and routes to agentic pipeline
2. **Planner** breaks down the question into subtasks
3. **PlanExecutor** iterates each subtask, calling Query Rewriter + Search Fanout per step
4. **Evidence Graph** persists and scores retrieved evidence
5. **Sufficient Context** checks if coverage is adequate
6. **Synthesis** summarizes evidence into structured findings
7. **Tutor** generates a comprehensive answer (agentic path with citation maps)
8. **Hallucination** analyzes response against evidence
9. **Claim Verifier** verifies factual accuracy, routes to finalize/revise/reject
10. **Safety** performs final review

## Features

### Hybrid Routing
The system automatically routes queries based on complexity:
- **Simple queries** → Legacy pipeline (faster)
- **Complex queries** → Agentic pipeline (more thorough)

### Query Rewriting
For complex queries, the system expands your question into multiple variants to improve retrieval:
- Cross-lingual expansion (English/Amharic)
- Query decomposition for multi-part questions
- Target index selection based on query type

### Multi-Index Search
Evidence is retrieved from multiple sources:
- **Curriculum** — Ethiopian science textbooks
- **Evidence** — Past tutoring sessions
- **Cross-session** — Historical learning data

### Iterative Retrieval
If initial evidence is insufficient, the system:
1. Identifies missing information
2. Rewrites the query
3. Re-retrieves evidence
4. Repeats until sufficient or max iterations reached

### Claim Verification
Factual claims in tutor responses are verified against evidence:
- **Finalize** (≥60% grounded) → Response passes safely to output
- **Revise** (30-60% grounded, max 2 attempts) → Tutor regenerates with ungrounded claims feedback
- **Reject** (<30% grounded or max revisions exhausted) → Fails to safety check

### Performance Monitoring
Every request is traced with:
- Unique trace ID
- Node-level timing
- Status tracking (running/completed/failed)
- Structured logging for debugging

## API Usage

### Unified Chat Endpoint
```bash
curl -X POST http://localhost:8000/graph/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Compare and contrast cellular respiration and photosynthesis",
    "grade_level": 11,
    "topic": "Biology",
    "language": "en"
  }'
```

### Response Format
```json
{
  "answer": "Cellular respiration and photosynthesis are complementary processes...",
  "model_used": "gemma4:31b-cloud",
  "confidence": 0.85,
  "sources": ["Grade 11, Unit 2: Cell Biology, p. 45"],
  "status": "approved",
  "requires_teacher_review": false,
  "session_id": "abc123"
}
```

### Check Pipeline Status
```bash
curl http://localhost:8000/graph/status
```

### View Traces
```bash
# List recent traces
curl http://localhost:8000/graph/traces

# Get specific trace
curl http://localhost:8000/graph/traces/trace_abc123
```

## Performance

### Benchmarks
| Component | Mean (ms) | P95 (ms) |
|-----------|-----------|----------|
| Query Expansion | <1.0 | <1.0 |
| Chunk Deduplication | <5.0 | <5.0 |
| Chunk Ranking | <5.0 | <5.0 |
| Claim Verification | <1.0 | <1.0 |
| Plan Model Creation | <1.0 | <1.0 |

### Latency
- **Simple queries**: ~2-3 seconds
- **Complex queries**: ~5-8 seconds (includes planning and iterative retrieval)

## Troubleshooting

### Query Not Routing to Agentic Pipeline
Check if the query meets complexity threshold:
- Multi-hop reasoning required
- Comparison/contrast needed
- Cross-session context needed
- Multiple subtopics involved

### Evidence Insufficient
The system will automatically:
1. Identify missing information
2. Rewrite queries
3. Re-retrieve evidence
4. Repeat up to 3 times

If still insufficient, the tutor will answer with available evidence and note limitations.

### Claim Verification Failing
If claims are marked as ungrounded:
- Check if evidence was retrieved
- Verify topic matches curriculum content
- Review tutor response for factual accuracy

## Configuration

### Environment Variables
```bash
# Enable/disable agentic RAG
AGENTIC_RAG_ENABLED=true

# Complexity threshold (0.0-1.0)
AGENTIC_RAG_THRESHOLD=0.5

# Maximum retrieval iterations
AGENTIC_RAG_MAX_ITERATIONS=3

# Enable claim verification
CLAIM_VERIFICATION_ENABLED=true

# Groundedness threshold (0.0-1.0)
GROUNDEDNESS_THRESHOLD=0.6
```

### Tuning
- **Lower threshold** → More queries route to agentic pipeline
- **Higher threshold** → Fewer queries use agentic features
- **More iterations** → Better evidence coverage but higher latency
- **Lower groundedness** → More responses revised/rejected

## Examples

### Simple Query (Legacy Pipeline)
**User:** "What is DNA?"
**Pipeline:** Legacy (orchestrator → retrieve → tutor → safety)
**Response:** Direct answer with citations

### Complex Query (Agentic Pipeline)
**User:** "Compare and contrast cellular respiration and photosynthesis, explain how they are connected, and discuss the role of mitochondria and chloroplasts"
**Pipeline:** Agentic (planner → query_rewriter → search_fanout → sufficient_context → tutor → claim_verifier → safety)
**Response:** Comprehensive comparison with evidence from multiple sources

### Amharic Query
**User:** "ፎቶሲንቴ시스 ምንድን ነው?"
**Pipeline:** Agentic with cross-lingual expansion
**Response:** Amharic explanation with curriculum citations