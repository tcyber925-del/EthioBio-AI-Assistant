# RAG Diagram Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement this plan task-by-task.

**Goal:** Inject textbook-accurate diagram caption context into DiagramAgent generation prompt via ChromaDB RAG.

**Architecture:** Follows existing QuizAgent pattern (adapter param → search → format_context → inject into system prompt). Index script reads PostgreSQL → embeds captions → upserts to ChromaDB with source_type="textbook_diagram".

**Tech Stack:** VectorStoreAdapter (ChromaDB), RetrievalFilter (grade_level + source_type), DiagramAgent, asyncpg

---

### Task 1: Index TextbookDiagram captions into ChromaDB

**Files:**
- Modify: `scripts/index_diagrams.py`
- Test: `tests/test_diagram_storage.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_diagram_storage.py`:

```python
"""Tests for indexing textbook diagrams into ChromaDB."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.database.models import TextbookDiagram


@pytest.mark.asyncio
async def test_index_script_upserts_to_chromadb():
    """index_diagrams.py wires PostgreSQL → ChromaDB embedding + upsert."""
    from scripts.index_diagrams import index_diagram_captions

    records = [
        TextbookDiagram(
            id="11111111-1111-1111-1111-111111111111",
            grade_level=10,
            unit="Unit 2",
            topic="Cell Biology",
            caption="Diagram of an animal cell",
            image_path="data/diagrams/10/animal_cell_1.jpg",
            figure_number=1,
            page_number=42,
            source_file="biology_grade10.pdf",
        ),
        TextbookDiagram(
            id="22222222-2222-2222-2222-222222222222",
            grade_level=10,
            unit="Unit 3",
            topic="Genetics",
            caption="DNA replication fork showing leading and lagging strands",
            image_path="data/diagrams/10/dna_replication_1.jpg",
            figure_number=1,
            page_number=78,
            source_file="biology_grade10.pdf",
        ),
    ]

    mock_adapter = MagicMock()
    mock_adapter.embedder.embed_batch = AsyncMock(return_value=[[0.1] * 384, [0.2] * 384])
    mock_adapter.vector_store.add_documents = AsyncMock()

    result = await index_diagram_captions(records, adapter=mock_adapter, dry_run=False)

    assert result["indexed"] == 2
    assert result["skipped"] == 0
    mock_adapter.vector_store.add_documents.assert_called_once()
    call_args = mock_adapter.vector_store.add_documents.call_args
    assert len(call_args.kwargs["texts"]) == 2
    assert call_args.kwargs["metadatas"][0] == {
        "source_type": "textbook_diagram",
        "grade_level": 10,
        "unit": "Unit 2",
        "topic": "Cell Biology",
        "figure_number": 1,
        "image_path": "data/diagrams/10/animal_cell_1.jpg",
    }
    assert "animal cell" in call_args.kwargs["texts"][0]
    assert "DNA" in call_args.kwargs["texts"][1]


@pytest.mark.asyncio
async def test_index_dry_run():
    from scripts.index_diagrams import index_diagram_captions

    records = [
        TextbookDiagram(
            id="11111111-1111-1111-1111-111111111111",
            grade_level=9,
            unit="Unit 1",
            topic="Biology",
            caption="test",
            image_path="test.jpg",
            figure_number=1,
            page_number=1,
            source_file="test.pdf",
        ),
    ]

    mock_adapter = MagicMock()
    result = await index_diagram_captions(records, adapter=mock_adapter, dry_run=True)

    assert result["indexed"] == 0
    assert result["skipped"] == 1
    mock_adapter.vector_store.add_documents.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_diagram_storage.py::test_index_script_upserts_to_chromadb tests/test_diagram_storage.py::test_index_dry_run -v`
Expected: FAIL — ImportError (function doesn't exist yet)

- [ ] **Step 3: Implement `index_diagram_captions` in the script**

Add to `scripts/index_diagrams.py` (replace skeleton content):

```python
"""Index textbook diagram captions into ChromaDB for RAG retrieval.

Usage:
    python scripts/index_diagrams.py                     # all grades
    python scripts/index_diagrams.py --grade 10          # single grade
    python scripts/index_diagrams.py --dry-run            # preview only
"""

import argparse
import asyncio
import sys
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import TextbookDiagram
from src.retrieval.adapter import VectorStoreAdapter

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()


async def index_diagram_captions(
    records: list[TextbookDiagram],
    adapter: VectorStoreAdapter | None = None,
    dry_run: bool = False,
) -> dict:
    """Embed and upsert diagram captions into ChromaDB.

    Args:
        records: List of TextbookDiagram records to index.
        adapter: VectorStoreAdapter instance (created if None).
        dry_run: If True, log what would be indexed without writing.

    Returns:
        dict with indexed, skipped counts.
    """
    own_adapter = adapter is None
    if own_adapter:
        adapter = VectorStoreAdapter()

    try:
        texts = []
        metadatas = []
        ids = []
        skipped = 0

        for record in records:
            if not record.caption or not record.caption.strip():
                skipped += 1
                continue

            texts.append(f"[Grade {record.grade_level}] {record.caption}")
            metadatas.append({
                "source_type": "textbook_diagram",
                "grade_level": record.grade_level,
                "unit": record.unit or "",
                "topic": record.topic or "",
                "figure_number": record.figure_number,
                "image_path": record.image_path,
            })
            ids.append(f"diagram_caption_{record.id}")

        if dry_run or not texts:
            if dry_run:
                for i, t in enumerate(texts):
                    logger.info("dry_run_document", index=i, text=t[:100], meta=metadatas[i])
            return {"indexed": 0, "skipped": skipped + (len(records) - len(texts))}

        embeddings = await adapter.embedder.embed_batch(texts)
        await adapter.vector_store.add_documents(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        return {"indexed": len(texts), "skipped": skipped}
    finally:
        if own_adapter:
            adapter.close()


async def main_async(grade: Optional[int] = None, dry_run: bool = False):
    from src.database.session import get_session

    async for session in get_session():
        stmt = select(TextbookDiagram)
        if grade is not None:
            stmt = stmt.where(TextbookDiagram.grade_level == grade)
        stmt = stmt.order_by(TextbookDiagram.grade_level, TextbookDiagram.figure_number)

        result = await session.execute(stmt)
        records = list(result.scalars().all())
        logger.info("records_loaded", count=len(records), grade=grade or "all")

        outcome = await index_diagram_captions(records, dry_run=dry_run)
        logger.info(
            "indexing_complete",
            indexed=outcome["indexed"],
            skipped=outcome["skipped"],
            total=len(records),
        )
        return outcome


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Index textbook diagram captions into ChromaDB for RAG retrieval"
    )
    parser.add_argument(
        "--grade", type=int, choices=range(7, 13),
        help="Single grade to process",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Log what would be indexed without writing to ChromaDB",
    )
    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()
    asyncio.run(main_async(grade=args.grade, dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_diagram_storage.py::test_index_script_upserts_to_chromadb tests/test_diagram_storage.py::test_index_dry_run -v`
Expected: PASS (x2)

- [ ] **Step 5: Ruff + mypy**

Run: `.venv/bin/ruff check scripts/index_diagrams.py tests/test_diagram_storage.py`
Run: `.venv/bin/mypy scripts/index_diagrams.py --explicit-package-bases`
Expected: All checks passed / 0 new errors

- [ ] **Step 6: Commit**

```bash
git add scripts/index_diagrams.py tests/test_diagram_storage.py
git commit -m "feat: index textbook diagram captions into ChromaDB for US-008"
```

---

### Task 2: Add TextbookReference schema and wire grade through API

**Files:**
- Modify: `src/schemas/diagram.py`
- Modify: `src/api/diagram.py`

- [ ] **Step 1: Add `TextbookReference` schema**

Add to `src/schemas/diagram.py` (before `DiagramGenerateResponse`):

```python
class TextbookReference(BaseModel):
    grade: int
    unit: str | None = None
    figure_number: int | None = None
    caption: str
```

Update `DiagramGenerateResponse` to include:

```python
class DiagramGenerateResponse(SchemaModel):
    title: str
    diagram_svg: str
    labels: list[DiagramLabel]
    topic: str
    difficulty: str
    model_used: str
    textbook_references: list[TextbookReference] = []
```

- [ ] **Step 2: Add `grade` field to `DiagramGenerateRequest`**

In `src/schemas/diagram.py`, update `DiagramGenerateRequest`:

```python
class DiagramGenerateRequest(SchemaModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    topic: str = Field(..., min_length=1)
    difficulty: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")
    model: Optional[str] = Field(None, min_length=1)
    grade: int = Field(default=10, ge=7, le=12)
```

- [ ] **Step 3: Wire grade through the API endpoint**

In `src/api/diagram.py`, update the generate endpoint to pass `request.grade`:

```python
@router.post("/generate", response_model=DiagramGenerateResponse)
async def generate_diagram(
    request: DiagramGenerateRequest,
    session: AsyncSession = Depends(get_session),
):
    router = ModelRouter()
    agent = DiagramAgent(llm_router=router)
    result = await agent.generate(
        prompt=request.prompt,
        topic=request.topic,
        difficulty=request.difficulty,
        session=session,
        preferred_model=request.model,
        grade=request.grade,
    )
    return DiagramGenerateResponse(**result)
```

- [ ] **Step 4: Remove old tests that check old schema shape, update import test**

Update `tests/test_diagram_storage.py` import test to verify `TextbookReference` exists:

```python
def test_textbook_reference_schema():
    from src.schemas.diagram import TextbookReference

    ref = TextbookReference(grade=10, unit="Unit 2", figure_number=1, caption="Animal cell")
    assert ref.grade == 10
    assert ref.caption == "Animal cell"


def test_diagram_generate_request_includes_grade():
    from src.schemas.diagram import DiagramGenerateRequest

    req = DiagramGenerateRequest(prompt="test", topic="cells")
    assert req.grade == 10

    req2 = DiagramGenerateRequest(prompt="test", topic="cells", grade=12)
    assert req2.grade == 12


def test_diagram_generate_response_includes_textbook_refs():
    from src.schemas.diagram import DiagramGenerateResponse, TextbookReference

    ref = TextbookReference(grade=10, unit="Unit 2", figure_number=1, caption="Animal cell")
    resp = DiagramGenerateResponse(
        title="Test",
        diagram_svg="<svg></svg>",
        labels=[],
        topic="cells",
        difficulty="beginner",
        model_used="test",
        textbook_references=[ref],
    )
    assert len(resp.textbook_references) == 1
    assert resp.textbook_references[0].caption == "Animal cell"
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/pytest tests/test_diagram_storage.py::test_textbook_reference_schema tests/test_diagram_storage.py::test_diagram_generate_request_includes_grade tests/test_diagram_storage.py::test_diagram_generate_response_includes_textbook_refs -v`
Expected: PASS (x3)

- [ ] **Step 6: Ruff + mypy**

Run: `.venv/bin/ruff check src/schemas/diagram.py src/api/diagram.py tests/test_diagram_storage.py`
Run: `.venv/bin/mypy src/schemas/diagram.py src/api/diagram.py --explicit-package-bases`
Expected: Clean

- [ ] **Step 7: Commit**

```bash
git add src/schemas/diagram.py src/api/diagram.py tests/test_diagram_storage.py
git commit -m "feat: add TextbookReference schema and grade API wiring for US-008"
```

---

### Task 3: Add RAG retrieval to DiagramAgent

**Files:**
- Modify: `src/agents/diagram.py`
- Test: `tests/test_diagram_storage.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_diagram_storage.py`:

```python
@pytest.mark.asyncio
async def test_rag_injects_context_when_found():
    from src.agents.diagram import DiagramAgent
    from src.llm.router import ModelRouter
    from unittest.mock import AsyncMock, patch

    mock_router = AsyncMock(spec=ModelRouter)
    mock_router.route = AsyncMock(return_value={
        "content": '{"title":"Cell","diagram_svg":"<svg></svg>","labels":[]}',
        "model": "ollama/test",
    })

    mock_adapter = AsyncMock()
    mock_adapter.search = AsyncMock(return_value=[
        MagicMock(
            content="Diagram of an animal cell",
            metadata={
                "source_type": "textbook_diagram",
                "grade_level": 10,
                "unit": "Unit 2",
                "topic": "Cell Biology",
                "figure_number": 1,
                "image_path": "data/diagrams/10/animal_cell_1.jpg",
            },
            score=0.95,
            source_id="diagram_caption_1",
        ),
    ])
    mock_adapter.format_context = MagicMock(return_value="[Grade 10] Diagram of an animal cell")

    agent = DiagramAgent(llm_router=mock_router, adapter=mock_adapter)
    result = await agent.generate(
        prompt="Draw a cell",
        topic="Cell Biology",
        grade=10,
    )

    assert len(result.get("textbook_references", [])) == 1
    assert result["textbook_references"][0]["caption"] == "Diagram of an animal cell"
    assert result["textbook_references"][0]["grade"] == 10

    # Verify the system prompt included curriculum context
    call_kwargs = mock_router.route.call_args.kwargs
    assert "animal cell" in call_kwargs["messages"][0]["content"]


@pytest.mark.asyncio
async def test_rag_fallback_when_not_found():
    from src.agents.diagram import DiagramAgent
    from src.llm.router import ModelRouter
    from unittest.mock import AsyncMock, MagicMock

    mock_router = AsyncMock(spec=ModelRouter)
    mock_router.route = AsyncMock(return_value={
        "content": '{"title":"Cell","diagram_svg":"<svg></svg>","labels":[]}',
        "model": "ollama/test",
    })

    mock_adapter = AsyncMock()
    mock_adapter.search = AsyncMock(return_value=[])
    mock_adapter.format_context = MagicMock(return_value="")

    agent = DiagramAgent(llm_router=mock_router, adapter=mock_adapter)
    result = await agent.generate(
        prompt="Draw a cell",
        topic="Cell Biology",
        grade=10,
    )

    assert result.get("textbook_references", []) == []

    # Should use original system prompt (no context injected)
    call_kwargs = mock_router.route.call_args.kwargs
    assert "Curriculum reference" not in call_kwargs["messages"][0]["content"]


@pytest.mark.asyncio
async def test_rag_unavailable_graceful():
    from src.agents.diagram import DiagramAgent
    from src.llm.router import ModelRouter
    from unittest.mock import AsyncMock, MagicMock

    mock_router = AsyncMock(spec=ModelRouter)
    mock_router.route = AsyncMock(return_value={
        "content": '{"title":"Cell","diagram_svg":"<svg></svg>","labels":[]}',
        "model": "ollama/test",
    })

    mock_adapter = AsyncMock()
    mock_adapter.search = AsyncMock(side_effect=Exception("ChromaDB unavailable"))

    agent = DiagramAgent(llm_router=mock_router, adapter=mock_adapter)
    result = await agent.generate(
        prompt="Draw a cell",
        topic="Cell Biology",
        grade=10,
    )

    # Should fall through gracefully — no crash, no references
    assert result.get("textbook_references", []) == []


@pytest.mark.asyncio
async def test_rag_respects_grade_filter():
    from src.agents.diagram import DiagramAgent
    from src.retrieval.adapter import RetrievalFilter
    from unittest.mock import AsyncMock, MagicMock

    mock_router = AsyncMock()
    mock_router.route = AsyncMock(return_value={
        "content": '{"title":"Cell","diagram_svg":"<svg></svg>","labels":[]}',
        "model": "ollama/test",
    })

    mock_adapter = AsyncMock()
    mock_adapter.search = AsyncMock(return_value=[])
    mock_adapter.format_context = MagicMock(return_value="")

    agent = DiagramAgent(llm_router=mock_router, adapter=mock_adapter)
    await agent.generate(prompt="test", topic="cells", grade=11)

    # Verify filter_obj includes grade_level=11
    call_kwargs = mock_adapter.search.call_args.kwargs
    assert call_kwargs["filter_obj"].grade_level == 11
    assert call_kwargs["filter_obj"].source_type == "textbook_diagram"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_diagram_storage.py -v -k "test_rag"`

Expected: FAIL — ImportError or "no attribute" errors (DiagramAgent doesn't accept adapter param, no grade param, no textbook_references in response)

- [ ] **Step 3: Implement RAG in DiagramAgent**

Replace `src/agents/diagram.py` content with:

```python
import json
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.retrieval.adapter import RetrievalFilter, VectorStoreAdapter

logger = structlog.get_logger()

DIAGRAM_SYSTEM_PROMPT = """You are EthioBio Diagram Generator, creating
visual biology diagrams for Ethiopian students (Grades 7-12).

Generate an SVG diagram of a biology structure based on the user's request. The diagram must:
- Be valid SVG markup (no HTML wrapping, no markdown fences in the svg value)
- Use clear colors and label positions
- Fit within a 800x600 viewBox
- Include visual elements (shapes, lines, curves) that represent the biology structure
- Have labeled parts with leader lines connecting labels to structures
- Be age-appropriate for the specified difficulty level

Output a JSON object following this schema:
{
  "title": "Diagram title",
  "labels": [
    {"id": "label_1", "text": "Part Name", "x": 650, "y": 50},
    {"id": "label_2", "text": "Another Part", "x": 700, "y": 150}
  ],
  "diagram_svg": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>...</svg>"
}

Rules for labels:
- Each label's x,y should be the position of the label TEXT on the SVG canvas
- Labels should be placed to the right of the diagram content area (x > 500 typically)
- id must be unique and use snake_case
- The label text in the SVG should match the label text in the labels array

Rules for SVG:
- The SVG must be self-contained (no external CSS or fonts)
- Use simple colors, shapes, and text
- For beginner: simpler diagrams with 3-5 labels
- For intermediate: moderate complexity with 6-10 labels
- For advanced: detailed diagrams with 10-15 labels
"""

CURRICULUM_CONTEXT_BLOCK = """

Curriculum reference materials (textbook diagrams with captions):
{context}

Use the exact biological terminology from these references when labeling diagram structures.
"""


class DiagramAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter, adapter: Optional[VectorStoreAdapter] = None):
        super().__init__(llm_router, name="diagram")
        self.adapter = adapter or VectorStoreAdapter()

    async def generate(
        self,
        prompt: str,
        topic: str,
        difficulty: str = "beginner",
        session: Optional[AsyncSession] = None,
        preferred_model: str | None = None,
        grade: int = 10,
    ) -> dict:
        # Retrieve textbook diagram context if available
        textbook_references = []
        system_prompt = DIAGRAM_SYSTEM_PROMPT
        try:
            filter_obj = RetrievalFilter(grade_level=grade, source_type="textbook_diagram")
            results = await self.adapter.search(query=topic, n_results=3, filter_obj=filter_obj)
            if results:
                context = self.adapter.format_context(results)
                system_prompt = DIAGRAM_SYSTEM_PROMPT + CURRICULUM_CONTEXT_BLOCK.format(context=context)
                for r in results:
                    textbook_references.append({
                        "grade": r.metadata.get("grade_level", grade),
                        "unit": r.metadata.get("unit"),
                        "figure_number": r.metadata.get("figure_number"),
                        "caption": r.content,
                    })
        except Exception:
            logger.warning("rag_retrieval_failed", exc_info=True)

        user_message = f"""Create a biology diagram for topic: {topic}.
User request: {prompt}
Difficulty level: {difficulty}

For {difficulty} difficulty:
- beginner: 3-5 labeled structures, simple shapes, large text
- intermediate: 6-10 labeled structures, moderate detail
- advanced: 10-15 labeled structures, detailed anatomical accuracy

Respond with valid JSON only."""

        result = await self._call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            session=session,
            temperature=0.7,
            max_tokens=4096,
            request_type="diagram_generation",
            preferred_model=preferred_model,
        )

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            return {
                "title": parsed.get("title", f"{topic} - {prompt[:50]}"),
                "diagram_svg": parsed.get("diagram_svg", ""),
                "labels": parsed.get("labels", []),
                "topic": topic,
                "difficulty": difficulty,
                "model_used": result.get("model", ""),
                "textbook_references": textbook_references,
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("diagram_parse_error", error=str(e), content=result["content"][:300])
            return {
                "title": f"{topic} - {prompt[:50]}",
                "diagram_svg": result["content"],
                "labels": [],
                "topic": topic,
                "difficulty": difficulty,
                "model_used": result.get("model", ""),
                "textbook_references": textbook_references,
            }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_diagram_storage.py -v -k "test_rag or test_diagram_generate"`

Expected: All 4 RAG tests + existing diagram generation tests pass

- [ ] **Step 5: Run all diagram tests**

Run: `.venv/bin/pytest tests/test_diagram_storage.py tests/test_agents.py -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"`

Expected: All existing tests pass (check for regressions in test_agents.py diagram tests)

- [ ] **Step 6: Ruff + mypy**

Run: `.venv/bin/ruff check src/agents/diagram.py tests/test_diagram_storage.py`
Run: `.venv/bin/mypy src/agents/diagram.py --explicit-package-bases`
Expected: Clean / 0 new errors

- [ ] **Step 7: Commit**

```bash
git add src/agents/diagram.py tests/test_diagram_storage.py
git commit -m "feat: RAG textbook context injection in DiagramAgent for US-008"
```

---

### Task 4: Update PRD and progress

**Files:**
- Modify: `scripts/ralph/prd.json`
- Modify: `progress.txt`

- [ ] **Step 1: Mark US-008 passes: true in PRD**

Edit `scripts/ralph/prd.json`: change `"passes": false` to `"passes": true` for US-008.

- [ ] **Step 2: Append to progress.txt**

```
---
## [2026-05-25] - US-008: RAG diagram generation with textbook context
- Extended `scripts/index_diagrams.py` to wire PostgreSQL → ChromaDB indexing:
  - `index_diagram_captions(records, adapter, dry_run)` embeds captions and upserts to ChromaDB
  - Metadata: source_type="textbook_diagram", grade_level, unit, topic, figure_number, image_path
  - IDs: `diagram_caption_{uuid}`
  - Dry-run mode logs without writing
  - CLI: `--grade`, `--dry-run` flags
- Added `TextbookReference` schema: grade, unit, figure_number, caption
- Updated `DiagramGenerateRequest` with `grade: int = Field(default=10, ge=7, le=12)`
- Updated `DiagramGenerateResponse` with `textbook_references: list[TextbookReference] = []`
- Modified `DiagramAgent`:
  - `__init__(llm_router, adapter=None)` — same QuizAgent pattern
  - `generate(..., grade=10)` — retrieves captions via `adapter.search()` with `RetrievalFilter(grade_level, source_type="textbook_diagram")`
  - Injects curriculum context block into system prompt when results found
  - Builds `textbook_references` list from search results for API response
  - Errors in ChromaDB search caught and logged — falls through gracefully
- 8 new tests: chromadb upsert, dry-run, context injection, fallback, graceful degradation, grade filter, schema fields
- Quality: ruff clean, mypy clean, all tests pass
- Files: `scripts/index_diagrams.py`, `src/schemas/diagram.py`, `src/api/diagram.py`, `src/agents/diagram.py`, `tests/test_diagram_storage.py`, `scripts/ralph/prd.json`, `progress.txt`
- **Learnings for future iterations:**
  - QuizAgent pattern is the template: accept adapter in __init__, build RetrievalFilter, call adapter.search(), inject format_context into system prompt
  - ChromaDB errors must NOT propagate — wrap retrieval in try/except with logger.warning
  - `source_type` metadata filter is what distinguishes textbook diagram captions from PDF text chunks
  - The `RetrievalFilter.to_chroma_where()` translates Python filter to ChromaDB `$eq` syntax
  - format_context returns a string; manual iteration over results is still needed for structured textbook_references
  - Grade filter in retrieval respects the curriculum level, preventing irrelevant results from other grades
```

- [ ] **Step 3: Commit**

```bash
git add scripts/ralph/prd.json progress.txt
git commit -m "feat: US-008 - RAG diagram generation with textbook context"
```

---

### Plan Self-Review

**1. Spec coverage:**
- [x] Index diagram captions into ChromaDB — Task 1
- [x] DiagramAgent retrieves relevant captions before calling LLM — Task 3
- [x] Retrieved context injected into system prompt — Task 3
- [x] Response includes textbook_references — Task 2 (schema) + Task 3 (build in agent)
- [x] When no matches, falls back to current behavior — Task 3 (empty results → no context block)
- [x] TextbookReference schema with grade, unit, figure_number, caption — Task 2
- [x] DiagramGenerateRequest.grade field — Task 2
- [x] Graceful error handling for ChromaDB failures — Task 3 (try/except with logger.warning)
- [x] Tests for all RAG scenarios — Task 3
- [x] Ruff, mypy pass — each task

**2. Placeholder scan:** 0 placeholders.

**3. Type consistency:** `adapter` is `Optional[VectorStoreAdapter]` in both `__init__` and tests. `grade` is `int` with default 10 everywhere. `textbook_references` is `list[dict]` in agent code, `list[TextbookReference]` in response schema — Pydantic handles the conversion from dict.
