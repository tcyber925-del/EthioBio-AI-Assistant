# PRD: Grade 10 Re-ingestion with Docling/RapidOCR

## Introduction

Grade 10 biology PDF is an image-based (scanned) document. PyMuPDF extracts garbled text. EasyOCR was used before but its dependencies (torchvision, libGL) break on fresh container builds due to version mismatches and slow downloads. Docling with RapidOCR is already baked into the Docker image, has all models cached, and works immediately.

Replace Grade 10's current 180 EasyOCR chunks with clean RapidOCR-extracted chunks using the existing `--use-docling` flag — no code changes needed.

## Goals

- Re-ingest Grade 10 with Docling/RapidOCR using the existing pipeline
- No new dependencies or code modifications
- Verify text quality is comparable to EasyOCR
- Total implementation time under 2 hours (mostly waiting for ingestion)

## User Stories

### US-001: Delete stale Grade 10 vectors
**Description:** As a developer, I need to remove the current 180 Grade 10 EasyOCR chunks from ChromaDB so the new Docling ingestion can replace them cleanly.

**Acceptance Criteria:**
- [ ] `coll.delete(where={'grade_level': 10})` removes all Grade 10 vectors
- [ ] Collection count drops from 1225 to 1045
- [ ] Run via inline python command

### US-002: Re-ingest Grade 10 with Docling
**Description:** As a developer, I want to run `ingest_curriculum.py --use-docling --grade 10` so Grade 10 text is extracted via RapidOCR and stored as 384-dim vectors.

**Acceptance Criteria:**
- [ ] Ingestion script completes without errors
- [ ] Grade 10 chunks stored in ChromaDB (expect ~180 chunks)
- [ ] Total collection count returns to ~1225
- [ ] BM25 index rebuilt automatically

### US-003: Verify text quality
**Description:** As a developer, I need to sample extracted chunks to confirm text is readable and substantively correct.

**Acceptance Criteria:**
- [ ] Sample 3-5 random Grade 10 chunks from ChromaDB
- [ ] Each chunk has >100 chars of readable English text
- [ ] No binary/control characters in extracted text

### US-004: Verify chat endpoint
**Description:** As a developer, I want to ask a Grade 10 biology question via the API and confirm the response uses the new OCR data.

**Acceptance Criteria:**
- [ ] `POST /chat` with `grade_level=10` returns an answer
- [ ] Answer cites Grade 10 curriculum sources
- [ ] Answer is substantively correct (not gibberish)

## Functional Requirements

- FR-1: Delete Grade 10 vectors from ChromaDB via `coll.delete(where={'grade_level': 10})`
- FR-2: Run `python /app/scripts/ingest_curriculum.py --use-docling --grade 10`
- FR-3: Verify via `coll.get(where={'grade_level': 10})` that chunks exist with readable text
- FR-4: Test chat endpoint with Grade 10 question
- FR-5: Restart `ethiobio-app` container to clear any cached VectorStoreAdapter state

## Non-Goals

- No changes to ingestion script or any source code
- No Dockerfile modifications
- No installation of new packages
- No changes to EasyOCR or other OCR engines
- No migration of existing Grades 9, 11, 12 data

## Technical Considerations

- **Current state:** ChromaDB has 1225 vectors (209+180+380+456) at 384-dim (all-MiniLM-L6-v2)
- **Docling pipeline:** `--use-docling` → `_extract_with_docling()` → pypdfium2 text extraction → >50% garbled → falls back to `_extract_with_ocr()` → pypdfium2 + RapidOCR
- **Speed:** RapidOCR ~15 pages/min. Grade 10 has 182 pages → ~12 minutes
- **No PyTorch needed:** RapidOCR uses ONNX Runtime, not torch/torchvision
- **Models pre-cached:** All RapidOCR ONNX models are baked into the Docker image

## Success Metrics

- Grade 10 text quality is readable (no binary garbage)
- Chat endpoint returns coherent Grade 10 answers with curriculum citations
- No regressions in Grades 9, 11, 12 responses

## Execution Plan

1. Delete Grade 10 vectors (180 chunks) from ChromaDB
2. Run ingestion with `--use-docling --grade 10`
3. Sample chunks to verify quality
4. Restart `ethiobio-app` container
5. Test chat endpoint with Grade 10 question
6. Start `telegram-bot` container

## Open Questions

- None — this is a straightforward re-ingestion with existing tooling.
