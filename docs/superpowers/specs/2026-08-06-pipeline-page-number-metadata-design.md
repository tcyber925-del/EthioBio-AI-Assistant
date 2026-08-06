# Pipeline Chunk Metadata: Restore Printed Page Numbers + source_file

Date: 2026-08-06
Status: Approved

## Problem

Chunks ingested through the production pipeline (`src/core/pipeline/service.py`)
carry no real page information. `_extract_pdf_text_sync` (service.py:257) flattens
all PDF pages into one `"\n\n"`-joined string, and `_chunk_text` (service.py:35)
hardcodes `page_number: None`, which `_run_embedding_and_indexing` (service.py:190)
persists as `page_number: 0`. The legacy ingest scripts
(`scripts/ingest_curriculum.py` → `embed_grade10.py`) chunked per OCR page and
stored the **printed textbook page number** (parsed from footer/header, grade-aware
front-matter offsets). This behavior was lost during the migration to the pipeline
+ pgvector; prod G10 rows now have `page_number=0`, `source_file=""`,
`section=""`, `subtopic=""`.

Consumers already read `page_number` from chunk metadata
(`src/graph/orchestrator.py:222`, `src/graph/nodes/tutor.py:178`,
`src/retrieval/adapter.py:270`, `src/rag/retriever.py:97`) — they just get 0/empty.

## Goals

- Pipeline-ingested chunks get **printed textbook page numbers** (e.g. the book's
  page 47, not PDF page 50) when grade is known (9-12); PDF page index as fallback.
- `source_file` populated with the uploaded filename.
- `unit`/`section`/`subtopic`/`heading` populated from chunk text where derivable
  (port of legacy helpers).
- Re-index the existing prod G10 textbook (345 vectors, KO `9c993dfe-8f9a-404c-9229-451548aa70f9`)
  with the fixed path so prod search returns real page numbers again.
- pgvector write path unchanged (`PGVectorStore.add_documents` already persists
  `page_number`, `source_file`, `unit`, `section`, `subtopic`, `heading` from metadata).

## Non-Goals

- No changes to the retrieval/ranking path (separate reranker feature).
- No changes to ChromaDB legacy adapter path (`src/retrieval/adapter.py`).
- No OCR pipeline in `src/` — PDFs with no text layer keep using the best
  available extraction (pypdf); G10 has a text layer (verified: prod embedded it).
- No schema/migration changes — metadata is a JSONB column.

## Design

### 1. Page extraction returns pages (`src/core/pipeline/service.py`)

Replace the flattening `_extract_pdf_text_sync` with a page-aware variant used
by `_extract_pdf_text` / `_run_content_extraction_and_chunking`:

- New module `src/ingestion/textbook.py` (port of legacy helpers, pure functions):
  - `extract_pdf_pages(path) -> list[{"text": str, "pdf_page": int}]` — pypdf
    per-page text with 1-based page index.
  - `extract_page_number(page_text, pdf_page, grade) -> int` — port of
    `scripts/ingest_curriculum.py:_extract_page_number` (footer/header patterns 1-6,
    `_FRONT_MATTER_PAGES = {9: 7, 10: 3, 11: 10, 12: 5}` fallback).
  - `extract_unit(text)`, `extract_heading(text)`, `extract_section_subtopic(text)`
    — ports of `_extract_unit`, `_extract_heading`, `_extract_heading_info`.
- `PipelineOrchestrator._run_content_extraction_and_chunking`:
  1. Load KO metadata (grade_level) — small refactor: fetch `ko_meta` here via
     `self._session_factory` (already done in `_run_embedding_and_indexing`; move
     that lookup earlier and pass it down).
  2. For PDFs: `pages = extract_pdf_pages(...)`; chunk **per page** (keep chunks
     within a page, no cross-page merging); each chunk dict carries
     `pdf_page` and `page_number = extract_page_number(page_text, pdf_page, grade)`
     when grade in 9-12 else `page_number = pdf_page`.
  3. For non-PDFs: current `_chunk_text` behavior, `page_number` left unset →
     defaults 0 in metadata (unchanged).
- `_chunk_text` signature: keep for non-PDF path; add per-page chunking that sets
  `page_number` from the enclosing page, `source_file` from `file_path.name`.

### 2. Metadata enrichment (`_run_embedding_and_indexing`)

In the metadata dict build (service.py:190-204):

- `source_file`: `file_path.name` (new param passed through from `run()`), falling
  back to `ko_meta.get("source_file", "")`.
- `unit`/`section`/`subtopic`/`heading`: if empty in chunk, derive from chunk text
  via the ported helpers (unit → `extract_unit`, heading → `extract_heading`,
  section/subtopic → `extract_section_subtopic`). `topic` derived from unit via
  `_derive_topic_from_unit` port when unit is known and topic empty.
- `page_number`: chunk's resolved value (printed or pdf index); never `None` →
  pgvector default `0` only when truly absent.

### 3. Re-index script `scripts/reindex_grade10.py`

One-shot maintenance script, prod-connectable (DATABASE_URL override pattern from
the prior handoff):

- Uses local PDF `data/textbooks/Grade10/Biology Grade 10 ST (MT)(BOOK).pdf` (27MB).
- `PGVectorStore.delete_by_grade(10)` → extract pages → chunk per page → embed via
  `Embedder()` (OpenRouter, 2048-dim, matches existing rows) → build metadata with
  `knowledge_object_id=9c993dfe-...` + `source_file` + page numbers → `add_documents`.
- Bypasses the pipeline lifecycle (no duplicate-content validation — we are
  refreshing, not uploading a new KO).
- Prints summary: chunk count, page-number coverage (chunks with `page_number>0`),
  and a sample of (page_number, source_file) pairs.

### 4. Tests

- New `tests/test_textbook_extraction.py` (pure functions):
  - `extract_page_number` — footer pattern (grades 9/10/11), header pattern
    (grade 12), "Grade X Biology N" variants, front-matter fallback, out-of-range
    guard, non-9-12 grade fallback to pdf index.
  - `extract_unit` / `extract_heading` / `extract_section_subtopic` — happy paths.
- New/updated pipeline tests in `tests/test_knowledge_platform.py`:
  - pipeline run with a fake PDF → chunks carry `page_number` + `source_file`;
  - metadata dict passed to `add_documents` includes page_number > 0;
  - non-PDF upload keeps old behavior (page_number absent → 0).

## Error Handling

- PDF extraction failures → pipeline `FAILED` (existing behavior, unchanged).
- Page-number parsing never raises: all regexes guarded, fallback always returns
  `max(1, pdf_page - front_matter)`.
- Re-index script: on embed failure, aborts before `add_documents` (no partial
  vector set); prints the failing batch index.

## Testing

```bash
pytest tests/ -v -k "not slow"   # unit tests
ruff check . && mypy src/        # lint + typecheck
```

## References

- `scripts/ingest_curriculum.py:282-435` — helpers being ported
- `scripts/embed_grade10.py`, `scripts/reingest_all.py` — legacy page-aware flow
- Handoff `/tmp/opencode/handoff-ethiobio-retrieval-deploy.md` — prod state, KO id
