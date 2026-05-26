# Textbook Figure Extraction Pipeline — Design Doc

## Feature

Extract figures from Ethiopian biology PDF textbooks (grades 9–12) using Docling layout analysis.

## Architecture

```
scripts/ingest_diagrams.py
  └─→ src/ingestion/diagram_extractor.extract_figures_from_pdf(filepath, grade)
        ├─ Docling DocumentConverter → layout items (FigureItem, PictureItem)
        ├─ pypdfium2 → render full page at 200 DPI → Pillow Image
        ├─ crop image to figure bounding box → save JPEG (quality 85)
        ├─ traverse Docling document tree → find preceding heading → unit/topic
        └─ return list[dict] with metadata
```

## Data Flow

1. `ingest_diagrams.py` iterates `data/textbooks/Grade{9,10,11,12}/*.pdf` (grades 7–8: log + skip)
2. Calls `extract_figures_from_pdf()` for each PDF
3. For each detected figure:
   - Render the parent PDF page at 200 DPI with pypdfium2
   - Crop to figure's bounding rect (from Docling layout)
   - Save to `data/diagrams/{grade}/{pdf_stem}_{fig_num}.jpg`
   - Record metadata: `{grade, pdf_stem, fig_num, page_num, caption, unit, topic, bbox, image_path}`
4. Progress logged per PDF with figure count

## Unit/Topic Mapping

Use Docling's hierarchical document tree. For each figure:
- Find the nearest preceding `HeadingItem` in document order
- If heading matches "Unit \d+" → set `unit` field
- The heading text itself → `topic` field
- Fallback: `unit="unknown"`, `topic="unknown"`

## Key Abstractions

### `src/ingestion/diagram_extractor.py`

```python
def extract_figures_from_pdf(filepath: str, grade: int) -> list[dict]:
    """Detect and extract figures from a PDF using Docling layout analysis.
    Returns list of dicts with: image_path, grade, pdf_stem, fig_num, page_num,
    caption, unit, topic."""
```

Internal helpers:
- `_detect_figures(docling_doc)` — filter FigureItem/PictureItem from Docling layout
- `_render_page(filepath, page_num, dpi=200)` — pypdfium2 → numpy → Pillow
- `_crop_figure(page_image, bbox)` — Pillow crop, pad 10px
- `_extract_caption(text_items, figure_bbox)` — text items spatially below figure
- `_map_unit_topic(docling_doc, figure)` — traverse heading hierarchy

### `scripts/ingest_diagrams.py`

```python
def main():
    for grade in [9, 10, 11, 12]:
        for pdf in glob(f"data/textbooks/Grade{grade}/*.pdf"):
            figures = extract_figures_from_pdf(pdf, grade)
            log(f"Grade {grade}, {pdf.name}: {len(figures)} figures")
    # Grades 7-8: log "No PDF found for Grade {grade}" and skip
```

## Dependencies Added

- `Pillow>=10.0.0` (image cropping + JPEG save)

All other deps exist: `pypdfium2` (page rendering), `docling>=2.12.0` (layout analysis).

## Error Handling

- Corrupt PDFs: log error + skip to next PDF, don't crash
- Zero figures: log "No figures detected in {filepath}" — not an error
- Missing page render: log warning, skip figure
- Output dir created automatically (`data/diagrams/{grade}/`)

## Testing

- Unit: `pytest tests/test_diagram_extractor.py`
  - Mock Docling output + pypdfium2 page render
  - Verify figure count, image saved, metadata correctness
  - Test caption extraction, unit/topic mapping
  - Test grades 7-8 stub (log + skip)
- Lint: `ruff check src/ingestion/diagram_extractor.py scripts/ingest_diagrams.py`
- Type: `mypy src/ingestion/diagram_extractor.py`
