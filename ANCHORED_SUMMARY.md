# Anchored Summary — Final State

All work is complete.

## Completed

### 1. Docker Rebuild
Containers rebuilt successfully. The "No Docker image rebuild" constraint from prior summaries is obsolete.
- `api_base_url` = `http://app:8000` (Docker internal)
- `dashboard_url` = `http://localhost:3000`

### 2. ChromaDB 0.5.5 Migration
After rebuild, persisted SQLite DB had breaking changes from ChromaDB 0.5.5:
- `seq_id` type mismatch (old: bytes → new: integer) — patched SQLite
- `_type` key missing from collection metadata JSON — added via patch
- HNSW index format changed — all `.hnsw` files deleted to force rebuild
- Dimension mismatch (old DB: 768-dim, local embedder: 384-dim) — cleared collection and re-ingested

### 3. Full Re-ingestion (all grades, consistent 384-dim)
- Cleared entire collection
- Grades 9, 11, 12 — PyMuPDF (default extractor) — good text
- Grade 10 — EasyOCR — readable text (minor OCR artifacts, substantively correct)
- **Total: 1225 chunks** (G9: 209, G10: 180, G11: 380, G12: 456) — all 384-dim (`all-MiniLM-L6-v2`)
- BM25 index rebuilt after ingestion

### 4. Chat Endpoint Verified
Grade 10 question answered correctly using EasyOCR-extracted data with citations. Server restarted to pick up new collection dimension.

### 5. Tests
875/876 pass (1 pre-existing failure unrelated to these changes).

## Key Technical Details
- **Embedder**: `all-MiniLM-L6-v2` (384-dim) from `src/rag/embedder.py`
- **Runtime**: `VectorStoreAdapter` auto-adapts to store dimension (line 80: forces Ollama if mismatch, uses local if match)
- **Collection at**: `./data/vectors_new` (Docker volume)
