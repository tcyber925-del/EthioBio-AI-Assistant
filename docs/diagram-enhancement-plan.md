# Diagram Enhancement Plan

## Problem

The current diagram generation endpoint (`POST /diagram/generate`) produces SVG
diagrams that are **not aligned with the Ethiopian Biology curriculum**. The
textbook figure extraction and indexing pipeline has never been run, so:

- The RAG context injection in `DiagramAgent.generate()` is dead code — ChromaDB
  has zero `textbook_diagram` entries.
- Generated diagrams come entirely from the LLM's pre-training data (Wikipedia,
  Western sources), not the Grade 9-12 Ethiopian textbook.
- The `textbook_references` field in responses is always empty.
- The textbook diagram validation path (`POST /diagram/validate` with
  `textbook_diagram_id`) cannot function — `TextbookDiagram` table is empty,
  `ground_truth_labels` never populated.

## Architecture Decision

**SVG-from-LLM is the primary generation path** — SVGs are editable, scalable,
and support precise labeling for educational use. Cloudflare Workers AI image
generation is used **only for augmentation**: VisionCritic evaluation,
sketch-to-diagram processing, and illustrative reference images.

## Label Language

**English only.** The Ethiopian Grades 9-12 biology curriculum is taught and
examined in English. All diagrams use English terminology matching the textbook.
No Amharic label feature is planned.

## Phases

### Phase 0 — Textbook Extraction & Indexing Pipeline

Run the existing extraction and indexing scripts to populate the vector store
with textbook diagram captions. This is a prerequisite for all alignment-dependent
features.

| Step | Command | Output | Est. Time |
|------|---------|--------|-----------|
| Install deps | `pip install docling pypdfium2 Pillow` | Extraction tools | 30 min |
| Extract all grades | `python scripts/ingest_diagrams.py` | JPGs in `data/diagrams/Grade{9,10,11,12}/` | ~4 hours |
| Verify extraction | Check count per grade | ~150-300 figures total | 5 min |
| Index captions | `python scripts/index_diagrams.py` | ChromaDB populated | 5 min |

**Files**: `scripts/ingest_diagrams.py`, `scripts/index_diagrams.py`,
`src/ingestion/diagram_extractor.py`

**Grade 7-8**: No textbook PDFs exist. These grades receive generic (non-aligned)
diagrams — document this limitation.

---

### Phase 1 — Critical Bug Fixes

| # | Task | File:Line | Change |
|---|------|-----------|--------|
| 1.1 | SVG XSS sanitization | `page.tsx:305` + `agents/diagram.py:126` | `DOMPurify` on frontend, XML validation on backend |
| 1.2 | Wire real user ID | `page.tsx:54` | Replace `PLACEHOLDER_USER_ID` with auth context |
| 1.3 | Fix static image 404 | `next.config.js` | Add `/diagrams/static/:path*` proxy rule |
| 1.4 | Remove topic regex | `schemas/diagram.py:25,53,69` | Free string instead of `^(cells\|...)$` |
| 1.5 | Add `httpx` | `pyproject.toml` | Dependency for Cloudflare API |

---

### Phase 2 — Topic Expansion

- Remove regex validation from `topic` in all diagram schemas
- Expand frontend topic suggestions from 4 to ~14 (cells, organ systems, genetics,
  anatomy, botany, angiosperms, photosynthesis, ecology, microbiology, evolution,
  human biology, zoology, biochemistry, biotechnology)

---

### Phase 3 — Multi-Panel Support

**Schema** (`src/schemas/diagram.py`):
```python
class DiagramPanel:
    id: str
    caption: str
    svg: str
    labels: list[DiagramLabel]

class DiagramGenerateResponse:
    panels: list[DiagramPanel]  # NEW
    diagram_svg: str = panels[0].svg if panels else ""  # backward compat
```

**Agent** (`src/agents/diagram.py`):
- `detect_panel_count(prompt)`: Heuristic using "and", "vs", "external...internal"
- `generate_panel(sub_prompt, index)`: Single SVG generation per panel
- `generate()` orchestrates 1 or N sequential calls

**Frontend** (`page.tsx`): Tabbed panel navigation, independent label inputs per panel.

---

### Phase 4 — Vision-Enhanced Critic Loop

**New files**:
- `src/utils/svg_render.py`: `render_svg_to_png(svg, width, height) -> bytes`
  via `cairosvg`
- `src/agents/diagram_critic.py`: `DiagramCritic` with heuristic checks (XML
  validity, label bounds) + optional vision check via Cloudflare SDXL

**Refine loop**: After initial generation, score 0-10. If < 7, pass issues back
to LLM for up to 3 iterations.

---

### Phase 5 — Cloudflare Workers AI Integration

**New file**: `src/services/cloudflare_images.py`
- `generate(prompt, model, steps)` → FLUX.1 Schnell for illustrative images
- `image_to_image(prompt, input_image)` → SD 1.5 img2img for sketch uploads

**Config** (`src/config.py`): `cloudflare_account_id`, `cloudflare_api_token`,
`cloudflare_image_model`

**Pricing**: 10,000 neurons/day free (~174 images). SDXL is $0/step (Beta).
No GPU infrastructure needed.

---

### Phase 6 — Lightweight SVG Editor (parallelizable)

Frontend-only: draggable label positions, inline text editing, color picker,
SVG download button.

---

### Phase 7 — Telegram Bot Integration (parallelizable)

**New command**: `/diagram` — topic picker → grade picker → text prompt →
SVG→PNG via `cairosvg` → `reply_photo()` with label list.

**Files**: `src/telegram/bot.py`, `src/telegram/keyboards.py`,
`src/telegram/messages/en.json`, `src/telegram/messages/am.json`

---

### Phase 8 — Icon Library Integration (parallelizable)

- `POST /diagram/compose`: Compose diagrams from pre-built biology icons
- Frontend palette with Bioicons (CC0/CC-BY: ~3,000 biology SVGs)

---

### Phase 9 — Gamification & XP

- Add `xp_awarded` to `DiagramAttempt` model
- In `POST /diagram/validate`: `award_xp()` + `update_streak()` + `check_achievements()`
- Return XP fields in validation response

---

### Phase 10 — Multi-Format Export

- SVG: Direct download
- PNG: `cairosvg` render
- PDF: `fpdf2` embed
- PPTX: `python-pptx` insert as vector

---

### Phase 11 — Sketch-to-Diagram

`POST /diagram/from-sketch`: Accept image upload → Cloudflare SDXL img2img →
vision LLM interprets → DiagramAgent generates SVG. Frontend: camera/file upload.

---

### Phase 12 — Visual Ground Truth Auto-Labeling

`POST /diagram/label-textbook`: Vision LLM generates labels from textbook
diagram images → stores in `TextbookDiagram.ground_truth_labels`.

---

### Phase 13 — SVG-to-Image Validation

Render student labels onto SVG → PNG → vision LLM evaluates → cross-reference
with text `validate_labels()` → flag mismatches for teacher review.

---

### Phase 14 — Style Transfer from Textbook Images

Optional `reference_image` on generate → vision LLM extracts style (colors, font,
density) → injects into SVG prompt → diagrams match textbook visual language.

## Timeline

```
Phase  0: 2 days  (pipeline execution)
Phase  1: 2 days  (security fixes)
Phase  2: 1 day   (topic expansion)
Phase  3: 4 days  (multi-panel)
Phase  4: 5 days  (critic loop)
Phase  5: 4 days  (Cloudflare)
Phase  6: 4 days  (SVG editor) — parallel
Phase  7: 3 days  (Telegram bot) — parallel
Phase  8: 4 days  (icon library) — parallel
Phase  9: 3 days  (gamification)
Phase 10: 3 days  (export)
Phase 11: 4 days  (sketch)
Phase 12: 4 days  (ground truth)
Phase 13: 2 days  (validation)
Phase 14: 3 days  (style transfer)

Total: ~30 calendar days with parallel phases
```

## Dependencies

| Dependency | Phases | Cost |
|-----------|--------|------|
| `docling`, `pypdfium2`, `Pillow` | 0 | Open source |
| `cairosvg` | 4, 7, 10 | Open source |
| `httpx` | 5, 11-14 | Open source |
| `python-pptx` | 10 | Open source |
| `DOMPurify` (npm) | 1 | Open source |
| Cloudflare Workers AI | 4, 5, 11, 13, 14 | 10K neurons/day free |
| Bioicons SVGs | 8 | CC0/CC-BY |
