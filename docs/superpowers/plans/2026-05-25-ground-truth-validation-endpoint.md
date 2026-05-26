# Ground Truth Validation Endpoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans.

**Goal:** Add textbook ground-truth validation path to `/diagram/validate` via optional `textbook_diagram_id`.

**Architecture:** Single-task change: add field to request schema, add source to response schema, add branching logic in endpoint to load `TextbookDiagram.ground_truth_labels` when ID is provided.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest

---

### Task 1: Add textbook validation path to /diagram/validate

**Files:**
- Modify: `src/schemas/diagram.py`
- Modify: `src/api/diagram.py`
- Test: `tests/test_diagram_storage.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_diagram_storage.py`:

```python
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def test_validate_request_accepts_textbook_diagram_id():
    from src.schemas.diagram import DiagramValidateRequest

    req = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[],
        submitted_labels=[],
        topic="cells",
        difficulty="beginner",
        textbook_diagram_id=uuid.uuid4(),
    )
    assert req.textbook_diagram_id is not None


def test_validate_response_includes_source():
    from src.schemas.diagram import DiagramValidateResponse, DiagramLabelResult

    resp = DiagramValidateResponse(
        score=100.0,
        total_labels=2,
        correct_count=2,
        results=[DiagramLabelResult(label_id="1", correct_text="X", submitted_text="X", is_correct=True)],
        attempt_id=uuid.uuid4(),
        source="textbook",
    )
    assert resp.source == "textbook"


def test_validate_response_defaults_to_ai_generated():
    from src.schemas.diagram import DiagramValidateResponse, DiagramLabelResult

    resp = DiagramValidateResponse(
        score=100.0,
        total_labels=2,
        correct_count=2,
        results=[DiagramLabelResult(label_id="1", correct_text="X", submitted_text="X", is_correct=True)],
        attempt_id=uuid.uuid4(),
    )
    assert resp.source == "ai_generated"


@pytest.mark.asyncio
async def test_validate_with_textbook_labels():
    from src.api.diagram import validate_diagram
    from src.schemas.diagram import DiagramLabel, DiagramValidateRequest

    fake_labels = [{"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3}]
    textbook_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_diagram = MagicMock()
    mock_diagram.ground_truth_labels = {"labels": fake_labels, "proposed": True, "human_reviewed": False}
    mock_session.get = AsyncMock(return_value=mock_diagram)

    request = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[DiagramLabel(id="ignored", text="should not be used", x=0, y=0)],
        submitted_labels=[DiagramLabel(id="1", text="Nucleus", x=0.5, y=0.3)],
        topic="cells",
        difficulty="beginner",
        textbook_diagram_id=textbook_id,
    )

    result = await validate_diagram(request, session=mock_session)
    assert result.source == "textbook"
    assert result.score == 100.0
    assert result.correct_count == 1

    # Verify the textbook labels were used, not the request's correct_labels
    mock_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_validate_without_textbook_id():
    from src.api.diagram import validate_diagram
    from src.schemas.diagram import DiagramLabel, DiagramValidateRequest

    mock_session = AsyncMock()
    # Mock session.get to return None (shouldn't be called, but guard)
    mock_session.get = AsyncMock(return_value=None)

    request = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[DiagramLabel(id="1", text="Nucleus", x=0.5, y=0.3)],
        submitted_labels=[DiagramLabel(id="1", text="Nucleus", x=0.5, y=0.3)],
        topic="cells",
        difficulty="beginner",
    )

    result = await validate_diagram(request, session=mock_session)
    assert result.source == "ai_generated"
    assert result.score == 100.0


@pytest.mark.asyncio
async def test_validate_textbook_not_found():
    from src.api.diagram import validate_diagram
    from src.schemas.diagram import DiagramLabel, DiagramValidateRequest

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)

    request = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[DiagramLabel(id="1", text="N", x=0, y=0)],
        submitted_labels=[DiagramLabel(id="1", text="N", x=0, y=0)],
        topic="cells",
        difficulty="beginner",
        textbook_diagram_id=uuid.uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        await validate_diagram(request, session=mock_session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_validate_textbook_no_ground_truth():
    from src.api.diagram import validate_diagram
    from src.schemas.diagram import DiagramLabel, DiagramValidateRequest

    mock_session = AsyncMock()
    mock_diagram = MagicMock()
    mock_diagram.ground_truth_labels = None
    mock_session.get = AsyncMock(return_value=mock_diagram)

    request = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[DiagramLabel(id="1", text="N", x=0, y=0)],
        submitted_labels=[DiagramLabel(id="1", text="N", x=0, y=0)],
        topic="cells",
        difficulty="beginner",
        textbook_diagram_id=uuid.uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        await validate_diagram(request, session=mock_session)
    assert exc.value.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_diagram_storage.py -v -k "test_validate"`

Expected: FAIL — ImportError or schema errors (fields don't exist yet)

- [ ] **Step 3: Implement schema changes**

In `src/schemas/diagram.py`:

Update `DiagramValidateRequest`:
```python
class DiagramValidateRequest(SchemaModel):
    user_id: UUID
    correct_labels: list[DiagramLabel]
    submitted_labels: list[DiagramLabel]
    topic: str = Field(..., pattern="^(cells|organ systems|genetics|anatomy)$")
    difficulty: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    textbook_diagram_id: Optional[UUID] = None
```

Update `DiagramValidateResponse`:
```python
class DiagramValidateResponse(SchemaModel):
    score: float
    total_labels: int
    correct_count: int
    results: list[DiagramLabelResult]
    attempt_id: UUID
    source: str = "ai_generated"
```

- [ ] **Step 4: Implement endpoint changes**

In `src/api/diagram.py`, update `validate_diagram`:

```python
@router.post("/validate", response_model=DiagramValidateResponse)
async def validate_diagram(
    request: DiagramValidateRequest,
    session: AsyncSession = Depends(get_session),
):
    submitted = [l.model_dump() for l in request.submitted_labels]

    if request.textbook_diagram_id:
        diagram = await session.get(TextbookDiagram, request.textbook_diagram_id)
        if not diagram:
            raise HTTPException(status_code=404, detail="Textbook diagram not found")
        if not diagram.ground_truth_labels or not diagram.ground_truth_labels.get("labels"):
            raise HTTPException(
                status_code=400,
                detail="Textbook diagram has no ground truth labels",
            )
        correct = diagram.ground_truth_labels["labels"]
        source = "textbook"
    else:
        correct = [l.model_dump() for l in request.correct_labels]
        source = "ai_generated"

    results = validate_labels(correct, submitted)
    correct_count = sum(1 for r in results if r["is_correct"])
    total = len(results)
    score = round((correct_count / total * 100) if total > 0 else 0.0, 1)

    attempt = DiagramAttempt(
        user_id=request.user_id,
        topic=request.topic,
        difficulty=request.difficulty,
        score=score,
        labels={"submitted": submitted, "results": results},
        completed=True,
        completed_at=datetime.now(timezone.utc),
    )
    session.add(attempt)
    await session.commit()
    await session.refresh(attempt)

    return DiagramValidateResponse(
        score=score,
        total_labels=total,
        correct_count=correct_count,
        results=[DiagramLabelResult(**r) for r in results],
        attempt_id=attempt.id,
        source=source,
    )
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/pytest tests/test_diagram_storage.py -v -k "test_validate or test_textbook_reference or test_diagram_generate"`
Expected: All pass

Run: `.venv/bin/pytest tests/test_diagram_storage.py -v`
Expected: All 18 tests pass

- [ ] **Step 6: Ruff + mypy**

Run: `.venv/bin/ruff check src/schemas/diagram.py src/api/diagram.py tests/test_diagram_storage.py`
Expected: Clean (note: pre-existing E741 on `l` in api/diagram.py may show — these are pre-existing)

Run: `.venv/bin/mypy src/schemas/diagram.py src/api/diagram.py --explicit-package-bases`
Expected: 0 new errors

- [ ] **Step 7: Commit**

```bash
git add src/schemas/diagram.py src/api/diagram.py tests/test_diagram_storage.py
git commit -m "feat: ground truth validation path in /diagram/validate for US-009"
```

---

### Task 2: Update PRD and progress

**Files:**
- Modify: `scripts/ralph/prd.json`
- Modify: `progress.txt`

- [ ] **Step 1: Mark US-009 passes: true in PRD**

Edit `scripts/ralph/prd.json`: change `"passes": false` to `"passes": true` for US-009.

- [ ] **Step 2: Append to progress.txt**

```
---
## [2026-05-25] - US-009: Ground truth diagram validation endpoint
- Added `textbook_diagram_id: Optional[UUID] = None` to `DiagramValidateRequest`
- Added `source: str = "ai_generated"` to `DiagramValidateResponse` ("textbook" | "ai_generated")
- Modified `/diagram/validate` endpoint:
  - When `textbook_diagram_id` provided: loads TextbookDiagram, uses `ground_truth_labels.labels` as answer key, returns `source='textbook'`
  - When absent: uses `request.correct_labels`, returns `source='ai_generated'`
  - 404 if textbook_diagram_id not found in DB
  - 400 if diagram exists but ground_truth_labels is null or empty
- 6 new tests: schema field, response field, default source, textbook path, no-textbook path, 404 error, 400 error
- Quality: ruff clean (pre-existing E741 in api/diagram.py), mypy clean, 18/18 storage tests pass
- Files: `src/schemas/diagram.py`, `src/api/diagram.py`, `tests/test_diagram_storage.py`, `scripts/ralph/prd.json`, `progress.txt`
- **Learnings for future iterations:**
  - The `ground_truth_labels` JSON field stores `{labels: [...], proposed: true, human_reviewed: false, model_used: "..."}` — extract `.labels` for the answer key
  - Textbook validation reuses the same `validate_labels()` function — no new validation logic needed
  - The `source` field in the response lets frontend display "validated against textbook" vs "AI-generated"
  - `session.get(Model, id)` is the standard SQLAlchemy async pattern for single-record lookup by PK
  - The validate endpoint now has two distinct code paths sharing the same attempt-save logic
```

- [ ] **Step 3: Commit**

```bash
git add scripts/ralph/prd.json progress.txt
git commit -m "feat: US-009 - Ground truth diagram validation endpoint"
```

---

### Plan Self-Review

**1. Spec coverage:**
- [x] `textbook_diagram_id: Optional[UUID]` on request — Task 1
- [x] `source: str` on response — Task 1
- [x] When ID provided, load TextbookDiagram, use ground_truth_labels — Task 1
- [x] 404 when not found — Task 1
- [x] 400 when no labels — Task 1
- [x] When ID absent, existing behavior preserved — Task 1
- [x] 5+ tests covering all paths — Task 1
- [x] Ruff, mypy, pytest pass — Task 1

**2. Placeholder scan:** 0 placeholders.

**3. Type consistency:** `textbook_diagram_id` is `Optional[UUID]` everywhere. `source` is `str` defaulting to `"ai_generated"`. `ground_truth_labels["labels"]` is a `list[dict]` matching the shape of `validate_labels()`'s `correct` parameter.
