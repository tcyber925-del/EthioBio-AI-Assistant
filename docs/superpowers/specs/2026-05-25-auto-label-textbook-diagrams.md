# Auto-Generate Ground Truth Labels from Textbook Diagrams — Design Doc

## Feature

Use vision-capable LLMs (via OpenRouter/Ollama) to analyze extracted textbook diagrams and generate structured labels as ground truth for validation.

## Architecture

```
scripts/label_textbook_diagrams.py
  └─→ for each data/diagrams/**/*.jpg:
        ├─ Read image → base64 encode
        ├─ ModelRouter.route(preferred_model, vision_messages)
        │    ├─ Try openrouter/openai/gpt-4o (primary)
        │    ├─ Try openrouter/anthropic/claude-3.5-sonnet (fallback 1)
        │    ├─ Try ollama/llava (fallback 2)
        │    └─ Skip diagram with warning if all fail
        ├─ Parse JSON response → list[DiagramLabel]
        ├─ Update TextbookDiagram.ground_truth_labels in PostgreSQL
        └─ Log result (success/skip/error)
```

## Components

### `scripts/label_textbook_diagrams.py`

```
main():
  parser: --grade, --model (override primary vision model), --dry-run
  scan data/diagrams/**/*.jpg
  for each image:
    label_diagram(image_path, grade, preferred_model)

label_diagram(image_path, grade, preferred_model=None):
  1. Read image → base64 encode
  2. Build vision messages with diagram analysis prompt
  3. Try models in priority order:
     a. preferred_model or "openrouter/openai/gpt-4o"
     b. "openrouter/anthropic/claude-3.5-sonnet"
     c. "ollama/llava"
  4. Parse response JSON into labels
  5. Update TextbookDiagram.ground_truth_labels in DB
  6. Log result
```

### Vision Prompt

System: "You are a biology diagram analyzer. Identify each labeled structure in this textbook diagram."

User message with image: "List all labeled structures in this diagram as JSON: [{id: string, text: string, x: number, y: number}]. Use the label numbers/letters as 'id', the label text as 'text', and estimate the x,y position as fractions of diagram width/height (0-1). Include ALL visible labels."

### Data Format (in TextbookDiagram.ground_truth_labels)

```json
{
  "labels": [
    {"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3},
    {"id": "2", "text": "Cell membrane", "x": 0.2, "y": 0.8}
  ],
  "proposed": true,
  "human_reviewed": false,
  "model_used": "openrouter/openai/gpt-4o"
}
```

### Image Encoding

- Read JPEG file as bytes
- Base64 encode
- Build data URI: `data:image/jpeg;base64,{encoded}`
- Image size limit: warn if > 20MB (OpenRouter limit)

## Fallback Strategy

All models tried via existing `ModelRouter.route()` with `preferred_model`. No changes to ProviderManager needed. If `response.get("content")` is empty or unparseable, move to next fallback.

## Error Handling

- Corrupt image: log warning + skip (don't crash)
- LLM returns non-JSON: log raw response + skip
- LLM returns empty labels: log + skip (not an error — diagram may have no labels)
- All models fail: log warning with model names tried
- DB unavailable: log error + continue (don't lose progress)

## Testing

- Unit: `tests/test_label_diagrams.py`
  - `_build_vision_messages()` — verifies message format with base64 image
  - `_parse_labels_from_response()` — valid JSON, invalid JSON, empty, partial
  - `_try_model_with_fallback()` — mock ModelRouter, verify fallback order
  - `--dry-run` flag doesn't touch DB
- Ruff + mypy

## Dependencies

All existing: `Pillow` (image reading), `base64` (stdlib), `ModelRouter`/`ProviderManager` (existing), `TextbookDiagram` (existing US-006).
