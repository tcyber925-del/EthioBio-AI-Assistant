# Pipeline Page-Number + Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pipeline-ingested PDFs chunk per page with **printed textbook page numbers** (grade-aware), plus `source_file`/`unit`/`section`/`subtopic`/`heading` metadata. Then re-index the existing prod G10 textbook (KO `9c993dfe-8f9a-404c-9229-451548aa70f9`, 345 vectors) with the fixed path.

**Architecture:** Port pure helpers from `scripts/ingest_curriculum.py` into `src/ingestion/textbook.py`; make `_extract_pdf_text_sync` return per-page dicts; chunk per page in `_run_content_extraction_and_chunking`; enrich metadata in `_run_embedding_and_indexing`; one-shot `scripts/reindex_grade10.py` writes to pgvector with the existing KO id.

**Tech Stack:** Python 3.12+, pypdf (already used), sqlalchemy async, OpenRouter embedder (prod path), pytest-asyncio, ruff, mypy.

---

### Task 1: Port legacy helpers to `src/ingestion/textbook.py`

**Files:**
- Create: `src/ingestion/textbook.py`
- Create: `src/ingestion/__init__.py` (if missing)

- [ ] **Step 1: Write failing tests** `tests/test_textbook_extraction.py`

```python
import pytest

from src.ingestion.textbook import (
    extract_page_number,
    extract_section_subtopic,
    extract_unit,
    extract_heading,
)


class TestExtractPageNumber:
    def test_footer_standalone_number(self):
        text = "Some body text.\n\n42"
        assert extract_page_number(text, pdf_page=45, grade=10) == 42

    def test_footer_grade_biology_number_after(self):
        text = "body\nGrade 10 Biology 47"
        assert extract_page_number(text, pdf_page=50, grade=10) == 47

    def test_footer_grade_biology_number_before(self):
        text = "body\n47 | Grade 10 Biology"
        assert extract_page_number(text, pdf_page=50, grade=10) == 47

    def test_header_standalone_number_grade12(self):
        text = "12\nSome body text."
        assert extract_page_number(text, pdf_page=17, grade=12) == 12

    def test_front_matter_fallback(self):
        # No printed number -> pdf index minus grade 10 front matter (3)
        text = "Some body text without a page number."
        assert extract_page_number(text, pdf_page=50, grade=10) == 47

    def test_unknown_grade_uses_pdf_index(self):
        text = "Some body text."
        assert extract_page_number(text, pdf_page=9, grade=0) == 9

    def test_out_of_range_ignored(self):
        text = "body\n9999"
        assert extract_page_number(text, pdf_page=20, grade=10) == 17


class TestUnitHeadingSection:
    def test_extract_unit_arabic(self):
        assert extract_unit("Unit 3: Biochemical Molecules\n...") == "Unit 3: Biochemical Molecules"

    def test_extract_unit_roman(self):
        assert extract_unit("Unit I: Sub-fields of Biology\n...") == "Unit 1: Sub-fields of Biology"

    def test_extract_heading_uppercase(self):
        assert extract_heading("THE CELL\nbody text") == "THE CELL"

    def test_extract_section_subtopic(self):
        sec, sub = extract_section_subtopic("3.1 Carbohydrates\n\n3.1.1 Monosaccharides\nbody")
        assert sec == "3.1 Carbohydrates"
        assert sub == "3.1.1 Monosaccharides"
```

- [ ] **Step 2: Implement the module**

Port verbatim (adjust names/imports):
- `_FRONT_MATTER_PAGES = {9: 7, 10: 3, 11: 10, 12: 5}` → module constant `FRONT_MATTER_PAGES`
- `extract_page_number(page_text, pdf_page_num, grade)` — from `ingest_curriculum.py:383-435`
- `extract_unit(text)` + `_roman_to_int` — from `:282-334`
- `extract_section_subtopic(text)` + `_SECTION_RE`/`_SUBTOPIC_RE` — from `:357-374`
- `extract_heading(text)` — from `:635-642`
- `extract_pdf_pages(path) -> list[dict]` — pypdf per-page, 1-based `pdf_page`:
  ```python
  def extract_pdf_pages(path: str) -> list[dict]:
      from pypdf import PdfReader
      reader = PdfReader(str(path))
      pages = []
      for i, page in enumerate(reader.pages, start=1):
          text = page.extract_text()
          if text and text.strip():
              pages.append({"text": text.strip(), "pdf_page": i})
      return pages
  ```

- [ ] **Step 3: Run tests** — `pytest tests/test_textbook_extraction.py -v` → all PASS

- [ ] **Step 4: Commit**
```bash
git add src/ingestion/ tests/test_textbook_extraction.py
git commit -m "feat(ingestion): port textbook page-number and unit/heading helpers"
```

---

### Task 2: Pipeline chunk-per-page with page numbers

**Files:**
- Modify: `src/core/pipeline/service.py`

- [ ] **Step 1: Write failing tests** (extend `tests/test_knowledge_platform.py`)

In `TestKnowledgePipeline`-style tests, add a PDF page-aware test. Use a real
tiny 2-page PDF (generate via pypdf writer in-test):

```python
class TestPipelinePageNumbers:
    async def test_pdf_chunks_carry_page_number_and_source_file(self, pipeline, registry):
        from io import BytesIO
        from pypdf import PdfWriter

        buf = BytesIO()
        w = PdfWriter()
        w.add_blank_page(width=612, height=792)
        w.add_blank_page(width=612, height=792)
        w.write(buf)
        pdf_bytes = buf.getvalue()
        p = Path(mkdtemp()) / "doc.pdf"
        p.write_bytes(pdf_bytes)
        # patch _extract_pdf_pages to return deterministic pages
        with patch(
            "src.core.pipeline.service.extract_pdf_pages",
            return_value=[
                {"text": "Unit 3: Biochemical Molecules\n\nGlucose is a simple sugar.\n\n7", "pdf_page": 1},
                {"text": "DNA structure is double helix.\n\n8", "pdf_page": 2},
            ],
        ):
            ko = NewKnowledgeObject(
                workspace_id="00000000-0000-0000-0000-000000000001",
                owner_id="00000000-0000-0000-0000-000000000002",
                title="doc.pdf",
                content_type="application/pdf",
                content_hash="x",
                metadata={"grade_level": 10},
            )
            ko, _ = await registry.register(ko)
            result = await pipeline.run(ko.id, p)
        assert result.success
        metas = pipeline._vector_store.add_documents.call_args.kwargs["metadatas"]
        assert all(m["page_number"] > 0 for m in metas)
        assert all(m["source_file"] == "doc.pdf" for m in metas)
        assert any("Unit 3" in m["unit"] for m in metas)
```

- [ ] **Step 2: Run to verify failing** — `pytest tests/test_knowledge_platform.py -k PageNumbers -v`
  Expected: FAIL (no `extract_pdf_pages` in service; `page_number` is 0/None)

- [ ] **Step 3: Implement**

In `src/core/pipeline/service.py`:

1. Replace `_extract_pdf_text_sync` with a wrapper delegating to
   `src.ingestion.textbook.extract_pdf_pages`; delete the local flattening version.
2. Rework `_run_content_extraction_and_chunking`:
   ```python
   async def _run_content_extraction_and_chunking(self, ko_id, file_path):
       ko_meta = await self._load_ko_metadata(ko_id)
       grade = ko_meta.get("grade_level") or 0
       source_file = ko_meta.get("source_file") or file_path.name
       if file_path.suffix.lower() == ".pdf":
           pages = await self._extract_pdf_pages(file_path)
           chunks = []
           for page in pages:
               page_chunks = _chunk_text(page["text"], ko_id)
               for c in page_chunks:
                   c["page_number"] = extract_page_number(page["text"], page["pdf_page"], grade)
                   c["pdf_page"] = page["pdf_page"]
                   c["source_file"] = source_file
                   chunks.append(c)
       else:
           chunks = _chunk_text(text, ko_id)
           for c in chunks:
               c["source_file"] = source_file
       await self._registry.update_metadata(ko_id, {"chunk_count": len(chunks)})
       return chunks
   ```
3. Add `_load_ko_metadata(ko_id)` — extract the KO lookup currently inside
   `_run_embedding_and_indexing` into a private helper; call it from both.
4. `_extract_text` for PDF → `_extract_pdf_pages` returning pages list; for
   docx/txt keep current behavior (single text) — chunking branch handles both.
   (`_extract_text` stays for the non-PDF path only.)
5. In `_run_embedding_and_indexing` metadata build (lines ~190-204): use
   `c.get("source_file")` and derive unit/section/subtopic/heading when empty:
   ```python
   "source_file": c.get("source_file") or ko_meta.get("source_file", ""),
   "page_number": c.get("page_number") or 0,
   ```
   and before the dict build, fill:
   ```python
   for c in chunks:
       if not c.get("unit"):
           c["unit"] = extract_unit(c["text"])
       if not c.get("heading"):
           c["heading"] = extract_heading(c["text"])
       if not c.get("section") or not c.get("subtopic"):
           sec, sub = extract_section_subtopic(c["text"])
           c["section"] = c.get("section") or sec
           c["subtopic"] = c.get("subtopic") or sub
   ```
   (Import helpers from `src.ingestion.textbook`; keep `topic` from ko_meta.)

- [ ] **Step 4: Run new tests** — `pytest tests/test_knowledge_platform.py -k PageNumbers -v` → PASS.
  Then full `pytest tests/ -k "not slow"` → green.

- [ ] **Step 5: Commit**
```bash
git add src/core/pipeline/service.py tests/test_knowledge_platform.py
git commit -m "feat(pipeline): chunk per page with printed page numbers and source_file metadata"
```

---

### Task 3: Re-index script `scripts/reindex_grade10.py`

**Files:**
- Create: `scripts/reindex_grade10.py`

- [ ] **Step 1: Write the script**

```python
"""
Re-index Grade 10 textbook with page-number metadata into pgvector.

Run with prod DB override (DATABASE_URL=... OPENROUTER_API_KEY=...):
  python scripts/reindex_grade10.py
"""
import asyncio
import sys

from pathlib import Path

sys.path.insert(0, "/app")  # container root; harmless locally

from src.config import settings
from src.ingestion.textbook import extract_pdf_pages, extract_page_number, \
    extract_unit, extract_heading, extract_section_subtopic
from src.rag.embedder import Embedder
from src.rag.pgvector_store import PGVectorStore

KO_ID = "9c993dfe-8f9a-404c-9229-451548aa70f9"
GRADE = 10
SOURCE_FILE = "Biology Grade 10 ST (MT)(BOOK).pdf"
PDF_PATH = Path("data/textbooks/Grade10/Biology Grade 10 ST (MT)(BOOK).pdf")

async def main():
    store = PGVectorStore(collection_name=settings.collection_name)
    deleted = await store.delete_by_grade(GRADE)
    print(f"Deleted {deleted} grade-10 embeddings")

    pages = extract_pdf_pages(str(PDF_PATH))
    print(f"Extracted {len(pages)} pages")
    if not pages:
        raise SystemExit("No pages extracted — check the PDF path")

    chunks = []
    for page in pages:
        for c in _chunk(page["text"]):
            c["page_number"] = extract_page_number(page["text"], page["pdf_page"], GRADE)
            c["pdf_page"] = page["pdf_page"]
            chunks.append(c)

    filtered = [c for c in chunks if len(c["text"]) >= 80]
    print(f"{len(chunks)} raw chunks, {len(filtered)} after quality filter")

    metadatas, texts = [], []
    for i, c in enumerate(filtered):
        if not c.get("unit"): c["unit"] = extract_unit(c["text"])
        if not c.get("heading"): c["heading"] = extract_heading(c["text"])
        sec, sub = extract_section_subtopic(c["text"])
        c["section"] = c.get("section") or sec
        c["subtopic"] = c.get("subtopic") or sub
        metadatas.append({
            "knowledge_object_id": KO_ID,
            "chunk_index": i,
            "heading": c["heading"] or c["text"][:80],
            "topic": c["topic"] or "",
            "grade_level": GRADE,
            "unit": c.get("unit", ""),
            "section": c.get("section", ""),
            "subtopic": c.get("subtopic", ""),
            "source_type": "student_textbook",
            "source_file": SOURCE_FILE,
            "page_number": c["page_number"],
        })
        texts.append(c["text"])

    embedder = Embedder()
    embeddings = await embedder.embed_batch(texts)
    ids = [f"g10_{SOURCE_FILE}_{i}" for i in range(len(texts))]
    await store.add_documents(texts, embeddings, metadatas, ids)

    covered = sum(1 for m in metadatas if m["page_number"] > 0)
    print(f"Stored {len(texts)} chunks; page_number>0 on {covered}/{len(metadatas)}")
    sample = [(m["page_number"], m["source_file"], t[:40]) for m, t in zip(metadatas[:3], texts)]
    for s in sample:
        print("  sample:", s)

def _chunk(text: str, max_chars: int = 1500) -> list[dict]:
    # mirror src.core.pipeline.service._chunk_text
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for para in paragraphs:
        if len(para) <= max_chars:
            chunks.append({"text": para})
        else:
            sentences = para.replace("\n", " ").split(". ")
            buf = ""
            for sent in sentences:
                candidate = f"{buf}. {sent}".strip() if buf else sent
                if len(candidate) > max_chars and buf:
                    chunks.append({"text": buf + "."})
                    buf = sent
                else:
                    buf = candidate
            if buf:
                chunks.append({"text": buf})
    return chunks

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Dry-run locally against prod DB**

```bash
DATABASE_URL="postgresql+asyncpg://ethiobio:...@dpg-...-a.frankfurt-postgres.render.com:5432/ethiobio?ssl=require" \
OPENROUTER_API_KEY="$(sed 's/.*=//' .env | tr -d '"' | tr -d ' ' | sed -n '/^sk-or/p')" \
python scripts/reindex_grade10.py
```
Expected: "Stored N chunks; page_number>0 on N/N" with N ≈ 345± (chunking parity may shift count slightly — acceptable; verify search still returns the KO).

**Watch-outs:** Render PG needs the dev machine's current public IP in the allowlist (see handoff — re-add via `PATCH /v1/postgres/dpg-d9obe27lk1mc7388cfb0-a` if connection drops). The `.env` OPENROUTER key has a leading space — strip it.

- [ ] **Step 3: Verify prod search returns page numbers**

```bash
curl "https://ethiobio-api.onrender.com/api/v1/knowledge/search?q=mitosis&workspace_id=a543a7e7-9385-473e-b840-20db474ce8df"
```
Expected: 200, results present. Then check `page_number` via a direct pgvector query on the rows (page_number > 0).

- [ ] **Step 4: Commit the script**
```bash
git add scripts/reindex_grade10.py
git commit -m "feat(scripts): re-index grade 10 with page-number metadata (reindex_grade10.py)"
```

---

### Task 4: Full verification

- [ ] **Step 1:** `pytest tests/ -v -k "not slow"` → all pass
- [ ] **Step 2:** `ruff check . && mypy src/` → clean
- [ ] **Step 3:** `git push` → CI green (lint+typecheck, tests -m "not slow")
- [ ] **Step 4:** Render deploy hook fires (GHCR build + deploy); verify `/health`, `/readiness`, and a prod search returns results with page numbers.

---

## Self-Review

**Spec coverage:**
- Port helpers → Task 1 ✓
- Per-page chunking + page numbers + source_file → Task 2 ✓
- Metadata enrichment (unit/section/subtopic/heading) → Task 2 ✓
- Re-index G10 → Task 3 ✓
- pgvector write path unchanged → Task 2 uses existing `add_documents` ✓
- Tests for pure helpers + pipeline → Tasks 1-2 ✓

**Placeholders:** G10 KO id `9c993dfe-8f9a-404c-9229-451548aa70f9` and workspace `a543a7e7-9385-473e-b840-20db474ce8df` taken from the handoff; prod DB creds in DATABASE_URL placeholder (re-extract from session summary before running Task 3).

**Type consistency:** `extract_page_number(page_text: str, pdf_page_num: int, grade: int) -> int` matches legacy signature; `_chunk` in the script mirrors `_chunk_text` (no `heading` in first append — added later in script). `extract_pdf_pages` returns `list[dict]` matching legacy OCR page shape (`{"text", "pdf_page"}`).
