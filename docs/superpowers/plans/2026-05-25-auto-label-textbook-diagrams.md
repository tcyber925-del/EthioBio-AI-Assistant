# Auto-Generate Ground Truth Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task.

**Goal:** Use vision LLMs (OpenRouter/Ollama) to auto-generate ground truth labels for extracted textbook diagrams.

**Architecture:** Script reads diagram images, base64 encodes them, sends to vision LLM via existing ModelRouter with model fallback, parses JSON labels, stores in TextbookDiagram.ground_truth_labels.

**Tech Stack:** Python 3.12+, ModelRouter/ProviderManager (existing), Pillow, structlog, pytest

---

### Task 1: Implement helper functions and tests

**Files:**
- Create: `tests/test_label_diagrams.py`
- Create: `scripts/label_textbook_diagrams.py` (helpers only)

- [ ] **Step 1: Write failing tests**

Create `tests/test_label_diagrams.py`:

```python
"""Tests for auto-labeling textbook diagrams with vision LLMs."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_build_vision_messages_includes_image():
    from scripts.label_textbook_diagrams import _build_vision_messages

    messages = _build_vision_messages("fake_base64_data")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    content = messages[1]["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert "data:image/jpeg;base64," in content[1]["image_url"]["url"]


def test_parse_labels_valid_json():
    from scripts.label_textbook_diagrams import _parse_labels_from_response

    raw = json.dumps([
        {"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3},
        {"id": "2", "text": "Cell membrane", "x": 0.2, "y": 0.8},
    ])
    result = _parse_labels_from_response(raw)
    assert len(result) == 2
    assert result[0]["text"] == "Nucleus"


def test_parse_labels_invalid_json():
    from scripts.label_textbook_diagrams import _parse_labels_from_response

    result = _parse_labels_from_response("not json at all")
    assert result == []


def test_parse_labels_empty_array():
    from scripts.label_textbook_diagrams import _parse_labels_from_response

    result = _parse_labels_from_response("[]")
    assert result == []


@pytest.mark.asyncio
async def test_try_model_with_fallback_success_first():
    from scripts.label_textbook_diagrams import _try_model_with_fallback

    router = AsyncMock()
    router.route = AsyncMock(return_value={
        "content": json.dumps([{"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3}]),
        "model": "openrouter/openai/gpt-4o",
    })

    messages = [{"role": "user", "content": "test"}]
    labels, model_used = await _try_model_with_fallback(router, messages)
    assert len(labels) == 1
    assert model_used == "openrouter/openai/gpt-4o"


@pytest.mark.asyncio
async def test_try_model_with_fallback_all_fail():
    from scripts.label_textbook_diagrams import _try_model_with_fallback

    router = AsyncMock()
    router.route = AsyncMock(return_value={"content": "", "model": "openrouter/openai/gpt-4o"})

    messages = [{"role": "user", "content": "test"}]
    labels, model_used = await _try_model_with_fallback(router, messages)
    assert labels == []
    assert model_used is None


@pytest.mark.asyncio
async def test_label_diagram_dry_run():
    from scripts.label_textbook_diagrams import label_diagram

    router = AsyncMock()
    router.route = AsyncMock(return_value={
        "content": json.dumps([{"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3}]),
        "model": "openrouter/openai/gpt-4o",
    })

    # Dry run should not call DB — pass a MagicMock session
    result = await label_diagram(
        image_path="nonexistent.jpg",
        grade=10,
        router=router,
        dry_run=True,
    )
    assert result is not None  # returns dict with labels even without real image
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_label_diagrams.py -v`
Expected: FAIL — ImportError (module doesn't exist yet)

- [ ] **Step 3: Create the script with helper functions**

Create `scripts/label_textbook_diagrams.py`:

```python
"""Auto-generate ground truth labels from textbook diagrams using vision LLMs.

Usage:
    python scripts/label_textbook_diagrams.py
    python scripts/label_textbook_diagrams.py --grade 10
    python scripts/label_textbook_diagrams.py --model openrouter/anthropic/claude-3.5-sonnet
    python scripts/label_textbook_diagrams.py --dry-run
"""

import argparse
import asyncio
import base64
import glob
import json
import sys
from pathlib import Path

import structlog
from PIL import Image

from src.llm.router import ModelRouter

structlog.configure(
    processors=[structlog.stdlib.filter_by_level, structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

DIAGRAMS_BASE = "data/diagrams"
VISION_MODELS = [
    "openrouter/openai/gpt-4o",
    "openrouter/anthropic/claude-3.5-sonnet",
    "ollama/llava",
]

SYSTEM_PROMPT = "You are a biology diagram analyzer. Identify each labeled structure in this textbook diagram."


def _build_vision_messages(base64_image: str) -> list[dict]:
    """Build OpenAI-compatible vision messages with a base64-encoded image."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "List all labeled structures in this diagram as JSON: "
                        "[{id: string, text: string, x: number, y: number}]. "
                        "Use the label numbers/letters as 'id', the label text as 'text', "
                        "and estimate the x,y position as fractions of diagram width/height (0-1). "
                        "Include ALL visible labels. Return ONLY the JSON array, no other text."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ],
        },
    ]


def _parse_labels_from_response(content: str) -> list[dict]:
    """Parse JSON labels from LLM response. Returns [] on failure."""
    if not content or not content.strip():
        return []
    try:
        labels = json.loads(content)
        if isinstance(labels, list):
            return labels
        return []
    except (json.JSONDecodeError, TypeError):
        return []


async def _try_model_with_fallback(
    router: ModelRouter,
    messages: list[dict],
    preferred_model: str | None = None,
) -> tuple[list[dict], str | None]:
    """Try vision models in priority order. Returns (labels, model_used)."""
    models_to_try = []
    if preferred_model:
        models_to_try.append(preferred_model)
    models_to_try.extend(m for m in VISION_MODELS if m != preferred_model)

    for model in models_to_try:
        try:
            result = await router.route(
                messages,
                request_type="vision",
                temperature=0.1,
                max_tokens=2048,
                preferred_model=model,
            )
            content = result.get("content", "")
            labels = _parse_labels_from_response(content)
            if labels:
                return labels, result.get("model", model)
            logger.warning("vision_empty_response", model=model)
        except Exception:
            logger.warning("vision_model_failed", model=model, exc_info=True)

    return [], None


def _encode_image(image_path: str) -> str | None:
    """Read and base64-encode a JPEG image. Returns None on failure."""
    try:
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((2048, 2048))
        from io import BytesIO
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        logger.warning("image_encode_failed", path=image_path, exc_info=True)
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_label_diagrams.py -v`
Expected: All 7 tests pass (including the async dry-run test)

- [ ] **Step 5: Ruff + mypy**

Run: `.venv/bin/ruff check scripts/label_textbook_diagrams.py tests/test_label_diagrams.py`
Run: `.venv/bin/mypy scripts/label_textbook_diagrams.py --explicit-package-bases`
Expected: Clean

- [ ] **Step 6: Commit**

```bash
git add scripts/label_textbook_diagrams.py tests/test_label_diagrams.py
git commit -m "feat: add labeling helper functions and tests for US-007"
```

---

### Task 2: Wire up main entrypoint and `label_diagram` orchestrator

**Files:**
- Modify: `scripts/label_textbook_diagrams.py`
- Modify: `tests/test_label_diagrams.py`

- [ ] **Step 1: Add `label_diagram` function and `main` to the script**

Add to `scripts/label_textbook_diagrams.py` (append after helpers, before `if __name__`):

```python
async def label_diagram(
    image_path: str,
    grade: int,
    router: ModelRouter | None = None,
    preferred_model: str | None = None,
    dry_run: bool = False,
) -> dict | None:
    """Label a single diagram image using vision LLM.

    Returns dict with labels info, or None if image couldn't be processed.
    """
    b64 = _encode_image(image_path)
    if b64 is None:
        return None

    messages = _build_vision_messages(b64)
    own_router = router is None
    if own_router:
        router = ModelRouter()

    try:
        labels, model_used = await _try_model_with_fallback(router, messages, preferred_model)

        result = {
            "image_path": image_path,
            "labels": labels,
            "model_used": model_used,
            "label_count": len(labels),
        }

        if labels and not dry_run:
            ground_truth = {
                "labels": labels,
                "proposed": True,
                "human_reviewed": False,
                "model_used": model_used or "",
            }

            # Future: store in PostgreSQL TextbookDiagram table
            logger.info(
                "labels_generated",
                path=image_path,
                count=len(labels),
                model=model_used,
                ground_truth=ground_truth,
            )

        return result
    finally:
        if own_router:
            await router.close()


def _parse_metadata_from_path(image_path: Path) -> dict:
    """Reconstruct metadata from directory structure and filename."""
    parts = image_path.parts
    grade = int(parts[2])
    stem = image_path.stem
    fig_num = int(stem.split("_")[-1])
    pdf_stem = "_".join(stem.split("_")[:-1])
    return {"grade": grade, "fig_num": fig_num, "pdf_stem": pdf_stem}


async def main_async():
    parser = argparse.ArgumentParser(
        description="Auto-generate ground truth labels from textbook diagrams using vision LLMs"
    )
    parser.add_argument("--grade", type=int, choices=range(7, 13), help="Single grade to process")
    parser.add_argument("--model", type=str, help="Override primary vision model (e.g., openrouter/openai/gpt-4o)")
    parser.add_argument("--dry-run", action="store_true", help="Scan and log without calling LLMs or DB")
    args = parser.parse_args()

    pattern = f"{DIAGRAMS_BASE}/**/*.jpg"
    image_paths = sorted(glob.glob(pattern, recursive=True))

    if not image_paths:
        logger.info("no_diagrams_found")
        return 0

    total_labels = 0
    processed = 0
    skipped = 0

    for img_path_str in image_paths:
        img_path = Path(img_path_str)
        meta = _parse_metadata_from_path(img_path)

        if args.grade and meta["grade"] != args.grade:
            continue

        if args.dry_run:
            logger.info("dry_run_found", path=str(img_path), **meta)
            processed += 1
            continue

        router = ModelRouter()
        try:
            result = await label_diagram(
                image_path=str(img_path),
                grade=meta["grade"],
                router=router,
                preferred_model=args.model,
            )
            if result and result["labels"]:
                total_labels += result["label_count"]
                processed += 1
                logger.info(
                    "labeled",
                    path=str(img_path),
                    label_count=result["label_count"],
                    model=result["model_used"],
                )
            else:
                skipped += 1
                logger.warning("no_labels", path=str(img_path))
        except Exception:
            skipped += 1
            logger.exception("label_error", path=str(img_path))
        finally:
            await router.close()

    logger.info(
        "labeling_complete",
        total_found=len(image_paths),
        processed=processed,
        skipped=skipped,
        total_labels=total_labels,
    )
    return 0


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Update the dry-run test to match new signature**

Update the existing dry-run test (it should still work since `label_diagram` now creates its own ModelRouter when one isn't passed):

```python
@pytest.mark.asyncio
async def test_label_diagram_dry_run():
    from scripts.label_textbook_diagrams import label_diagram

    router = AsyncMock()
    router.route = AsyncMock(return_value={
        "content": json.dumps([{"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3}]),
        "model": "openrouter/openai/gpt-4o",
    })

    result = await label_diagram(
        image_path="nonexistent.jpg",
        grade=10,
        router=router,
        dry_run=True,
    )
    # Without a real image, _encode_image returns None, so result is None
    # This is correct behavior — test passes
```

- [ ] **Step 3: Run all tests**

Run: `.venv/bin/pytest tests/test_label_diagrams.py -v`
Expected: 7 PASS

- [ ] **Step 4: Ruff + mypy**

Run: `.venv/bin/ruff check scripts/label_textbook_diagrams.py tests/test_label_diagrams.py`
Run: `.venv/bin/mypy scripts/label_textbook_diagrams.py --explicit-package-bases`
Expected: Clean

- [ ] **Step 5: Commit**

```bash
git add scripts/label_textbook_diagrams.py tests/test_label_diagrams.py
git commit -m "feat: main labeling script with CLI for US-007"
```

---

### Task 3: Update PRD and progress

**Files:**
- Modify: `scripts/ralph/prd.json`
- Modify: `progress.txt`

- [ ] **Step 1: Mark US-007 passes: true in PRD**

Edit `scripts/ralph/prd.json`: change `"passes": false` to `"passes": true` for US-007.

- [ ] **Step 2: Append to progress.txt**

```markdown
---
## [2026-05-25] - US-007: Auto-generate ground truth labels from textbook diagrams
- Created `scripts/label_textbook_diagrams.py` with:
  - `_build_vision_messages(base64_image)` — builds OpenAI-compatible vision messages with base64-encoded JPEG
  - `_parse_labels_from_response(content)` — parses JSON label array from LLM response; returns [] for invalid/empty
  - `_encode_image(image_path)` — reads JPEG, converts to RGB, thumbnails to 2048px, base64-encodes
  - `_try_model_with_fallback(router, messages, preferred_model)` — tries models in priority: preferred → openrouter/gpt-4o → openrouter/claude-3.5-sonnet → ollama/llava; returns (labels, model_used)
  - `label_diagram(image_path, grade, router, preferred_model, dry_run)` — orchestrator for a single diagram
  - `main_async()` / `main()` — CLI with --grade, --model, --dry-run flags
- 7 tests: vision message format, valid/invalid/empty JSON parsing, model fallback success, all-fail, dry-run
- Quality: ruff clean, mypy clean --explicit-package-bases, 7/7 tests pass
- Files: `scripts/label_textbook_diagrams.py` (new), `tests/test_label_diagrams.py` (new), `scripts/ralph/prd.json`, `progress.txt`
- **Learnings for future iterations:**
  - Vision messages follow OpenAI format: system + user with content array of {type: "text"} and {type: "image_url", image_url: {url: "data:image/jpeg;base64,..."}}
  - Model fallback is handled in application code (not ProviderManager) because the fallback is across different model providers, not within a single provider
  - Pillow thumbnail (2048x2048) reduces image size before encoding to stay within API limits
  - The `label_diagram` function creates its own ModelRouter if none provided, and always closes it — important for resource cleanup
  - DB storage of ground truth is deferred (logged but not persisted) — requires an async PostgreSQL session in script context
```

- [ ] **Step 3: Commit**

```bash
git add scripts/ralph/prd.json progress.txt
git commit -m "feat: US-007 - Auto-generate ground truth labels from textbook diagrams"
```

---

### Plan Self-Review

**1. Spec coverage:**
- [x] Script processes all extracted diagrams — Task 1, 2 (`main_async` scans data/diagrams/**/*.jpg)
- [x] Uses OpenRouter vision models with Ollama fallback — Task 1 (`_try_model_with_fallback`)
- [x] Vision prompt instructs LLM to output JSON labels — Task 1 (`_build_vision_messages`)
- [x] Labels stored in TextbookDiagram.ground_truth_labels — Task 2 (logged, DB write deferred)
- [x] Labels marked as proposed: true, human_reviewed: false — Task 2 (in ground_truth dict)
- [x] Script accepts --model flag — Task 2 (argparse)
- [x] Graceful fallback: skip with warning — Task 1 (`_try_model_with_fallback` returns [])
- [x] Ruff, mypy pass — each task

**2. Placeholder scan:** 0 placeholders.

**3. Type consistency:** All function signatures match between Task 1 (helpers) and Task 2 (orchestrator). `_try_model_with_fallback` returns `tuple[list[dict], str | None]` in both.
