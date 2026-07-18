# Export Module — Agent Instructions

## Purpose
Generates downloadable DOCX and PDF files for quizzes and lesson plans.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /export/quiz/{quiz_id}?format=docx\|pdf` | Export quiz as DOCX or PDF |
| `GET /export/lesson-plan/{lesson_id}?format=docx\|pdf` | Export lesson plan as DOCX or PDF |

Both endpoints return the file as a download (`Content-Disposition: attachment`).

## Patterns

- **DOCX**: Use `python-docx` `Document` with `BytesIO` buffer for in-memory generation. The returned bytes are a ZIP-compressed OOXML file — do not assert text content directly in tests.
- **PDF**: Use `fpdf2`. Subclass `FPDF` for custom headers/footers. Use `cell()` with `new_x="LMARGIN"` / `new_y="NEXT"` for single-line text instead of `multi_cell()` which can fail in edge cases.
- **To add a new exportable type**: Add exporter function to both `docx_exporter.py` and `pdf_exporter.py`, then add a new endpoint in `src/api/export.py`.
