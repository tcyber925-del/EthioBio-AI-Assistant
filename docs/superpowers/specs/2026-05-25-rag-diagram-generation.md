# RAG Diagram Generation with Textbook Context

> **Driven by:** US-008 (PRD priority 8)
> **Status:** Design — pending approval

## Problem

DiagramAgent generates SVG diagrams using only the user's prompt topic + difficulty. Labels may use generic or non-curriculum terminology. We need to inject textbook-accurate terminology by retrieving relevant diagram captions from the Ethiopian biology textbooks.

## Approach

Use ChromaDB semantic search on textbook diagram captions at generation time. The captions were already extracted in US-005 and stored in PostgreSQL in US-006, but were never indexed into ChromaDB.

## Architecture

```
DiagramAgent.generate()
  │
  ├── VectorStoreAdapter.query(topic, source_type="textbook_diagram", grade=grade, k=3)
  │     └── ChromaDB: embedded diagram captions
  │     └── Returns: list of TextbookDiagramChunk (grade, unit, figure_number, caption)
  │
  ├── If results found:
  │     inject into system prompt as curriculum reference
  │     build textbook_references list for response
  │
  └── If no results:
        use current behavior (no RAG context)
```

## Changes

### 1. Extend `scripts/index_diagrams.py`

The skeleton from US-006 currently only scans filesystem and logs. Wire it to:

- Connect to PostgreSQL via `src/database/session.py:get_session()`
- Query all `TextbookDiagram` records (or a filtered subset via `--grade`)
- For each record, compute embedding of `caption` text using the existing `embedding_model` from `src/retrieval/adapter.py` (or create a lightweight one if none exists)
- Upsert into ChromaDB via `VectorStoreAdapter.add_documents()` with:
  - `documents`: `f"[Grade {grade_level}] {caption}"`
  - `metadatas`: `{source_type: "textbook_diagram", grade_level: int, unit: str, topic: str, figure_number: int, image_path: str}`
  - `ids`: `f"diagram_caption_{id}"`
- Dry-run mode (`--dry-run`) to preview what would be indexed
- Progress logging per grade

The VectorStoreAdapter already has `add_documents()` and `query()` methods. No new class needed.

### 2. Modify `DiagramAgent`

In `src/agents/diagram.py`:

- Add `adapter: Optional[VectorStoreAdapter] = None` parameter to `__init__()` (same pattern as QuizAgent)
- Add `grade: int` parameter to `generate()` (optional, defaults to grade 10)
- Before calling `_call_llm()`:
  1. Build `RetrievalFilter(grade_level=grade)` 
  2. Call `await self.adapter.search(query=topic, n_results=3, filter_obj=filter_obj)`
  3. Build `textbook_references` list from results with fields: `{grade, unit, figure_number, caption}`
  4. Format context via `self.adapter.format_context(results)`
- If >= 1 result found, inject context into system prompt:

```
Curriculum reference materials (textbook diagrams with captions):
{formatted references}

Use the exact biological terminology from these references when labeling diagram structures.
```

- Pass `textbook_references` through to the response

### 3. Extend Response Schema

In `src/schemas/diagram.py`:

- Add `TextbookReference(BaseModel)` with fields: `grade: int`, `unit: str`, `figure_number: int`, `caption: str`
- Add `textbook_references: list[TextbookReference] = []` to `DiagramGenerateResponse`

### 4. Wire Grade Through API

In `src/api/diagram.py`:

- `DiagramGenerateRequest` already has `topic` and `difficulty`. Add optional `grade: int = Field(default=10, ge=7, le=12)`.
- Pass `request.grade` to `DiagramAgent.generate()`

## Error Handling

| Scenario | Behavior |
|----------|----------|
| ChromaDB unavailable (no Rust bindings) | Log warning, fall through to current behavior (no RAG) |
| No matching captions found | Current behavior (no RAG) |
| Embedding computation fails | Skip that caption, continue with rest |
| All captions fail | Fall through to current behavior |

## Testing

| Test | What it validates |
|------|-------------------|
| `test_rag_injects_context_when_found` | Agent retrieves captions, injects into system prompt |
| `test_rag_fallback_when_not_found` | Agent uses current behavior when ChromaDB returns 0 results |
| `test_rag_unavailable_graceful` | ChromaDB error → fallback without crash |
| `test_textbook_references_in_response` | Response includes textbook_references field |
| `test_grade_filter_on_retrieval` | Only captions matching grade level are retrieved |
| `test_index_script_upserts_to_chromadb` | index_diagrams.py actually stores captions in ChromaDB |

## Files Changed

| File | Change |
|------|--------|
| `scripts/index_diagrams.py` | Wire PostgreSQL → ChromaDB indexing |
| `src/agents/diagram.py` | Add `grade` param, RAG retrieval, context injection |
| `src/schemas/diagram.py` | Add `TextbookReference`, `textbook_references` to response |
| `src/api/diagram.py` | Add `grade` to request schema, pass to agent |
| `tests/test_diagram_storage.py` | Add RAG + indexing tests |
| `scripts/ralph/prd.json` | Mark US-008 passes: true |
| `progress.txt` | Append completion entry |
