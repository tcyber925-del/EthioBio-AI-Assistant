# Fix Page Number Offset in Citations

## Problem
All cited page numbers are ~6-10 pages ahead of the actual textbook page. This is because PDF page indices (1-indexed) include front-matter pages (cover, copyright, TOC) that the printed textbook doesn't count.

## Root Cause
`scripts/ingest_curriculum.py` stores `page_number = page_num + 1` (the raw PDF page index), but the textbook's printed page numbering starts after N front-matter pages. Each grade has different front-matter count:

| Grade | Front-matter pages | Offset |
|-------|-------------------|--------|
| 9     | 7                 | +7     |
| 10    | 6                 | +6     |
| 11    | 10                | +10    |
| 12    | 5                 | +5     |

## Fix

### File: `src/graph/nodes/retrieval.py`

1. Add `PAGE_OFFSET` dict and `_correct_page()` helper after `N_RESULTS = 8`:

```python
PAGE_OFFSET = {9: 7, 10: 6, 11: 10, 12: 5}

def _correct_page(page_number: int, grade_level: int) -> int:
    offset = PAGE_OFFSET.get(grade_level, 0)
    return max(1, page_number - offset)
```

2. In `RetrievalNode.__call__()`, correct page numbers in the metadata before storing. Replace:

```python
        state.retrieved_chunks = [
            {"content": r.content, "metadata": r.metadata, "score": r.score, "source_id": r.source_id}
            for r in quality_results
        ]
        state.context = self.adapter.format_context(quality_results)
```

With:

```python
        corrected_results = []
        for r in quality_results:
            meta = dict(r.metadata)
            grade = meta.get("grade_level", 0)
            if "page_number" in meta:
                meta["page_number"] = _correct_page(meta["page_number"], grade)
            corrected_results.append(
                RetrievalResult(
                    content=r.content, metadata=meta,
                    score=r.score, source_id=r.source_id,
                )
            )

        state.retrieved_chunks = [
            {"content": r.content, "metadata": r.metadata, "score": r.score, "source_id": r.source_id}
            for r in corrected_results
        ]
        state.context = self.adapter.format_context(corrected_results)
```

3. Add `from src.retrieval.adapter import RetrievalFilter, VectorStoreAdapter, RetrievalResult` import (add `RetrievalResult`).

### Deployment

```bash
docker cp "src/graph/nodes/retrieval.py" ethiobio-app:/app/src/graph/nodes/retrieval.py
docker cp "src/graph/nodes/retrieval.py" ethiobio-bot:/app/src/graph/nodes/retrieval.py
docker compose restart telegram-bot
```

### Verification

Test with Grade 10 question "Define mitosis and meiosis" via Telegram. Verify cited page numbers match the actual textbook page (should now show ~6-10 less than before).

### Why this approach (not re-ingestion)

Fixing at display time in `retrieval.py` requires zero re-ingestion. The page number is corrected in the metadata dict that flows to both `format_context()` (adapter.py) and the inline citation blocks (tutor.py, orchestrator.py) — all three read from the same corrected metadata, so all citations are fixed automatically.
