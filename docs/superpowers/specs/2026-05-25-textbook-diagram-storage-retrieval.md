# Textbook Diagram Storage and Retrieval — Design Doc

## Feature

Store extracted textbook diagrams in PostgreSQL and ChromaDB, serve them via a GET API endpoint.

## Architecture

```
US-005 output (data/diagrams/{grade}/*.jpg)
  │
  └─→ New pipeline step: index_diagrams.py
        ├─ Stores each figure in PostgreSQL (TextbookDiagram model)
        └─ Embeds captions → ChromaDB (existing collection, source_type="textbook_diagram")

GET /diagram/textbook?grade=10&topic=Cell+Biology
  └─→ Query PostgreSQL by grade_level + optional topic filter
       Returns matching diagrams with image URLs (StaticFiles mount)
```

## Data Flow

### Storage (new script `scripts/index_diagrams.py`):
1. Scans `data/diagrams/{grade}/*.jpg` and their metadata (from the extraction step)
2. For each figure, inserts `TextbookDiagram` row into PostgreSQL
3. Embeds caption via `VectorStoreAdapter.generate_embedding()` → stores in ChromaDB with `source_type: "textbook_diagram"` metadata
4. Handles idempotency: skips if image_path already exists in DB

### Retrieval:
1. `GET /diagram/textbook?grade=10&topic=Cell+Biology`
2. Query: `SELECT * FROM textbook_diagrams WHERE grade_level = :grade AND topic ILIKE :topic_pattern`
3. Response: `list[TextbookDiagramResponse]` with `image_url`, `caption`, `grade_level`, `unit`, `topic`, `figure_number`, `page_number`

## Components

### `src/schemas/diagram.py` — add schema
```python
class TextbookDiagramResponse(SchemaModel):
    id: UUID
    image_url: str
    caption: str
    grade_level: int
    unit: str
    topic: str
    figure_number: int
    page_number: int
    source_file: str
```

### `src/database/models.py` — add model
```python
class TextbookDiagram(Base):
    __tablename__ = "textbook_diagrams"
    id, grade_level, unit, topic, caption, image_path, figure_number,
    page_number, source_file, ground_truth_labels (JSON, nullable),
    created_at, updated_at
```

### `src/api/diagram.py` — add GET endpoint
```python
@router.get("/textbook", response_model=list[TextbookDiagramResponse])
async def get_textbook_diagrams(grade: int, topic: Optional[str] = None):
    # Query PostgreSQL, construct image_url from static mount
```

### `src/main.py` — mount static files
```python
app.mount("/diagrams/static", StaticFiles(directory="data/diagrams"), name="diagrams")
```

### `scripts/index_diagrams.py` — indexing pipeline
- Reads metadata from existing `data/diagrams/` structure
- Inserts into PostgreSQL
- Embeds captions → ChromaDB

## ChromaDB Indexing

- Target: existing `ethiobio_curriculum` collection (no new collection)
- Metadata added: `source_type: "textbook_diagram"`, `grade_level`, `topic`, `unit`, `diagram_id` (UUID)
- Content: figure caption text
- Uses existing `VectorStoreAdapter.generate_embedding()` for embeddings
- Not required for the GET endpoint to work — it's a separate data path for US-008

## Image URLs

Constructed as: `/diagrams/static/{grade}/{filename}`
Derived from `image_path` field (relative to data/diagrams/).

## Error Handling

- Grade 7-8: query returns empty list (no diagrams exist → 200 with [])
- Missing topic param: return all diagrams for that grade
- No matching diagrams: 200 with empty list
- StaticFiles mount handles 404 for missing images

## Testing

- Unit: `tests/test_diagram_storage.py`
  - `TextbookDiagram` model columns
  - Schema serialization
  - GET endpoint response shape
  - Empty results (grade 7-8), single result, multiple results
- Lint: `ruff check`
- Type: `mypy` (with `--explicit-package-bases`)
