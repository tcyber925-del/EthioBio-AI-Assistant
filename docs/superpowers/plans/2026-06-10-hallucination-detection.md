# Hallucination Detection — Implementation Plan

> **For agentic workers:** Use subagent-driven-development or executing-plans to implement task-by-task.

**Goal:** Build a Hallucination Detection system that verifies tutor claims against cited evidence, using structural (ID lookup) and optional semantic (LLM/heuristic) verification.

**Architecture:** New `src/evaluation/hallucination/` package with focused modules (models, structural check, semantic check) orchestrated by `HallucinationDetector`. New `HallucinationNode` sits between TutorNode and ClaimVerifierNode.

**Tech Stack:** Python 3.12+, Pydantic (models), asyncio, LLM via `ModelRouter`, LangGraph (state), pytest (async tests with mocking)

---

## File Structure

```
Create: src/evaluation/hallucination/__init__.py
Create: src/evaluation/hallucination/models.py       # HallucinationReport, ClaimAssessment, DetectionMode
Create: src/evaluation/hallucination/structural.py   # structural_check()
Create: src/evaluation/hallucination/semantic.py     # semantic_check()
Create: src/evaluation/hallucination/detector.py     # HallucinationDetector

Create: tests/evaluation/__init__.py
Create: tests/evaluation/test_structural.py
Create: tests/evaluation/test_semantic.py
Create: tests/evaluation/test_detector.py

Modify: src/graph/state.py                           # Add hallucination_report, hallucination_rate
Create: src/graph/nodes/hallucination.py             # HallucinationNode
Modify: src/graph/orchestrator.py                    # Wire HallucinationNode
```

---

### Task 1: Models + AgentState fields

**Files:**
- Create: `src/evaluation/hallucination/__init__.py`
- Create: `src/evaluation/hallucination/models.py`
- Create: `tests/evaluation/__init__.py`
- Modify: `src/graph/state.py`

- [ ] **Step 1: Create models.py**

```python
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class DetectionMode(str, Enum):
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    FULL = "full"


class ClaimAssessment(BaseModel):
    response_segment: str
    evidence_ids: list[str]
    supported: bool
    confidence: float
    reason: str = ""


class HallucinationReport(BaseModel):
    supported_claims: int
    unsupported_claims: int
    hallucination_rate: float
    grounding_score: float
    claim_assessments: list[ClaimAssessment]
    detection_mode: DetectionMode
```

- [ ] **Step 2: Create `src/evaluation/hallucination/__init__.py`**

```python
from src.evaluation.hallucination.models import ClaimAssessment, DetectionMode, HallucinationReport
from src.evaluation.hallucination.structural import structural_check
from src.evaluation.hallucination.semantic import semantic_check
from src.evaluation.hallucination.detector import HallucinationDetector

__all__ = [
    "ClaimAssessment",
    "DetectionMode",
    "HallucinationReport",
    "structural_check",
    "semantic_check",
    "HallucinationDetector",
]
```

- [ ] **Step 3: Create empty `tests/evaluation/__init__.py`** (empty file)

- [ ] **Step 4: Add fields to AgentState in `src/graph/state.py`**

Find the field definitions (near `recommendations`). Add after `recommendations`:

```python
    hallucination_report: Optional[dict] = None
    hallucination_rate: float = 0.0
```

You'll need to add `from typing import Optional` if not already imported.

- [ ] **Step 5: Verify**

```bash
.venv/bin/ruff check src/evaluation/hallucination/ src/graph/state.py tests/evaluation/
.venv/bin/mypy src/evaluation/hallucination/ src/graph/state.py --no-error-summary
```

- [ ] **Step 6: Commit**

```bash
git add src/evaluation/hallucination/ tests/evaluation/ src/graph/state.py
git commit -m "feat(hallucination): add models, DetectionMode, and AgentState fields"
```

---

### Task 2: Structural Check

**Files:**
- Create: `src/evaluation/hallucination/structural.py`
- Create: `tests/evaluation/test_structural.py`

- [ ] **Step 1: Write the failing test in `tests/evaluation/test_structural.py`**

```python
import pytest
from src.evaluation.hallucination.structural import structural_check


def test_all_claims_supported():
    citation_map = [
        {"response_segment": "Meiosis creates diversity", "evidence_ids": ["bio_1"], "source_names": ["curriculum"]},
    ]
    evidence_items = [
        {"id": "bio_1", "content": "Meiosis diversity", "source_name": "curriculum", "confidence": 0.9},
    ]
    report = structural_check(citation_map, evidence_items)
    assert report.supported_claims == 1
    assert report.unsupported_claims == 0
    assert report.hallucination_rate == 0.0
    assert report.grounding_score == 1.0


def test_missing_evidence_id():
    citation_map = [
        {"response_segment": "Claim", "evidence_ids": ["missing_id"], "source_names": ["curriculum"]},
    ]
    evidence_items = [
        {"id": "bio_1", "content": "Real", "source_name": "curriculum", "confidence": 0.9},
    ]
    report = structural_check(citation_map, evidence_items)
    assert report.supported_claims == 0
    assert report.unsupported_claims == 1
    assert report.hallucination_rate == 1.0


def test_empty_citation_map():
    report = structural_check([], [])
    assert report.supported_claims == 0
    assert report.unsupported_claims == 0
    assert report.hallucination_rate == 0.0


def test_mixed_support():
    citation_map = [
        {"response_segment": "Good", "evidence_ids": ["bio_1"], "source_names": ["curriculum"]},
        {"response_segment": "Bad", "evidence_ids": ["missing"], "source_names": ["curriculum"]},
    ]
    evidence_items = [
        {"id": "bio_1", "content": "Real", "source_name": "curriculum", "confidence": 0.9},
    ]
    report = structural_check(citation_map, evidence_items)
    assert report.supported_claims == 1
    assert report.unsupported_claims == 1
    assert report.hallucination_rate == 0.5
```

- [ ] **Step 2: Run to confirm they fail**

```bash
.venv/bin/python -m pytest tests/evaluation/test_structural.py -v
```

Expected: 4 FAIL

- [ ] **Step 3: Implement `src/evaluation/hallucination/structural.py`**

```python
from src.evaluation.hallucination.models import (
    ClaimAssessment,
    DetectionMode,
    HallucinationReport,
)


def structural_check(
    citation_map: list[dict],
    evidence_items: list[dict],
) -> HallucinationReport:
    if not citation_map:
        return HallucinationReport(
            supported_claims=0,
            unsupported_claims=0,
            hallucination_rate=0.0,
            grounding_score=1.0,
            claim_assessments=[],
            detection_mode=DetectionMode.STRUCTURAL,
        )

    valid_ids = {e["id"] for e in evidence_items if "id" in e}
    assessments: list[ClaimAssessment] = []

    for entry in citation_map:
        eids = entry.get("evidence_ids", [])
        missing = [eid for eid in eids if eid not in valid_ids]
        supported = len(missing) == 0
        assessments.append(ClaimAssessment(
            response_segment=entry.get("response_segment", ""),
            evidence_ids=eids,
            supported=supported,
            confidence=1.0 if supported else 0.0,
            reason="" if supported else f"evidence_id(s) not found: {missing}",
        ))

    total = len(assessments)
    supported_count = sum(1 for a in assessments if a.supported)
    unsupported_count = total - supported_count
    h_rate = unsupported_count / total if total > 0 else 0.0

    return HallucinationReport(
        supported_claims=supported_count,
        unsupported_claims=unsupported_count,
        hallucination_rate=h_rate,
        grounding_score=1.0 - h_rate,
        claim_assessments=assessments,
        detection_mode=DetectionMode.STRUCTURAL,
    )
```

- [ ] **Step 4: Run to verify they pass**

```bash
.venv/bin/python -m pytest tests/evaluation/test_structural.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Ruff + mypy**

```bash
.venv/bin/ruff check src/evaluation/hallucination/structural.py tests/evaluation/test_structural.py
.venv/bin/mypy src/evaluation/hallucination/structural.py --no-error-summary
```

- [ ] **Step 6: Commit**

```bash
git add src/evaluation/hallucination/structural.py tests/evaluation/test_structural.py
git commit -m "feat(hallucination): add structural check for evidence ID validity"
```

---

### Task 3: Semantic Check

**Files:**
- Create: `src/evaluation/hallucination/semantic.py`
- Create: `tests/evaluation/test_semantic.py`

- [ ] **Step 1: Write the failing test in `tests/evaluation/test_semantic.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.evaluation.hallucination.semantic import semantic_check


@pytest.mark.asyncio
async def test_heuristic_supported():
    citation_map = [
        {"response_segment": "Meiosis creates genetic diversity", "evidence_ids": ["bio_1"], "source_names": ["curriculum"]},
    ]
    evidence_items = [
        {"id": "bio_1", "content": "Meiosis is important for genetic diversity", "source_name": "curriculum", "confidence": 0.9},
    ]
    report = await semantic_check(citation_map, evidence_items)
    assert report.supported_claims == 1
    assert report.unsupported_claims == 0


@pytest.mark.asyncio
async def test_heuristic_unsupported():
    citation_map = [
        {"response_segment": "Mitosis has 10 phases", "evidence_ids": ["bio_1"], "source_names": ["curriculum"]},
    ]
    evidence_items = [
        {"id": "bio_1", "content": "Mitosis has 4 phases: prophase, metaphase, anaphase, telophase", "source_name": "curriculum", "confidence": 0.9},
    ]
    report = await semantic_check(citation_map, evidence_items)
    assert report.unsupported_claims == 1


@pytest.mark.asyncio
async def test_empty_citation_map():
    report = await semantic_check([], [])
    assert report.supported_claims == 0
    assert report.unsupported_claims == 0
    assert report.hallucination_rate == 0.0


@pytest.mark.asyncio
async def test_llm_mode_with_router():
    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value={
        "content": "supported",
        "model": "test",
        "confidence": 0.95,
    })

    citation_map = [
        {"response_segment": "Meiosis creates diversity", "evidence_ids": ["bio_1"], "source_names": ["curriculum"]},
    ]
    evidence_items = [
        {"id": "bio_1", "content": "Meiosis diversity", "source_name": "curriculum", "confidence": 0.9},
    ]
    report = await semantic_check(citation_map, evidence_items, router=mock_router)
    assert report.supported_claims == 1
```

- [ ] **Step 2: Run to confirm they fail**

```bash
.venv/bin/python -m pytest tests/evaluation/test_semantic.py -v
```

Expected: 4 FAIL

- [ ] **Step 3: Implement `src/evaluation/hallucination/semantic.py`**

```python
import re

from src.evaluation.hallucination.models import (
    ClaimAssessment,
    DetectionMode,
    HallucinationReport,
)

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "can", "may", "might", "shall",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "out", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "not", "only", "own",
    "same", "so", "than", "too", "very", "it", "its", "this",
    "that", "these", "those",
}


def _tokenize(text: str) -> set[str]:
    words = re.findall(r'[a-z]+', text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _heuristic_support(claim_text: str, evidence_text: str, threshold: float = 0.3) -> tuple[bool, float]:
    claim_tokens = _tokenize(claim_text)
    evidence_tokens = _tokenize(evidence_text)
    if not claim_tokens:
        return True, 1.0
    if not evidence_tokens:
        return False, 0.0
    overlap = claim_tokens & evidence_tokens
    ratio = len(overlap) / len(claim_tokens)
    return ratio >= threshold, round(ratio, 3)


async def semantic_check(
    citation_map: list[dict],
    evidence_items: list[dict],
    router=None,
    overlap_threshold: float = 0.3,
) -> HallucinationReport:
    if not citation_map:
        return HallucinationReport(
            supported_claims=0,
            unsupported_claims=0,
            hallucination_rate=0.0,
            grounding_score=1.0,
            claim_assessments=[],
            detection_mode=DetectionMode.SEMANTIC,
        )

    evidence_map = {e["id"]: e for e in evidence_items if "id" in e}
    assessments: list[ClaimAssessment] = []

    for entry in citation_map:
        segment = entry.get("response_segment", "")
        eids = entry.get("evidence_ids", [])

        if router:
            evidence_texts = []
            for eid in eids:
                ev = evidence_map.get(eid, {})
                if ev:
                    evidence_texts.append(ev.get("content", ""))
            combined_evidence = "\n".join(evidence_texts)

            prompt = f"Claim: {segment}\nEvidence: {combined_evidence}\n\nDoes the evidence support this claim? Answer 'supported' or 'unsupported'."
            result = await router.route(
                [{"role": "user", "content": prompt}],
                request_type="hallucination_check",
                temperature=0.1,
                max_tokens=10,
            )
            content = result.get("content", "").strip().lower()
            supported = "supported" in content
            confidence = result.get("confidence", 0.5)
            assessments.append(ClaimAssessment(
                response_segment=segment,
                evidence_ids=eids,
                supported=supported,
                confidence=confidence,
                reason="llm_assessment" if supported else "llm_flagged",
            ))
        else:
            evidence_text = ""
            for eid in eids:
                ev = evidence_map.get(eid, {})
                if ev:
                    evidence_text += " " + ev.get("content", "")
            supported, ratio = _heuristic_support(segment, evidence_text, overlap_threshold)
            assessments.append(ClaimAssessment(
                response_segment=segment,
                evidence_ids=eids,
                supported=supported,
                confidence=ratio,
                reason="" if supported else "low_token_overlap",
            ))

    total = len(assessments)
    supported_count = sum(1 for a in assessments if a.supported)
    unsupported_count = total - supported_count
    h_rate = unsupported_count / total if total > 0 else 0.0

    return HallucinationReport(
        supported_claims=supported_count,
        unsupported_claims=unsupported_count,
        hallucination_rate=h_rate,
        grounding_score=1.0 - h_rate,
        claim_assessments=assessments,
        detection_mode=DetectionMode.SEMANTIC,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/evaluation/test_semantic.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Ruff + mypy**

```bash
.venv/bin/ruff check src/evaluation/hallucination/semantic.py tests/evaluation/test_semantic.py
.venv/bin/mypy src/evaluation/hallucination/semantic.py --no-error-summary
```

- [ ] **Step 6: Commit**

```bash
git add src/evaluation/hallucination/semantic.py tests/evaluation/test_semantic.py
git commit -m "feat(hallucination): add semantic check with heuristic overlap and optional LLM"
```

---

### Task 4: HallucinationDetector

**Files:**
- Create: `src/evaluation/hallucination/detector.py`
- Create: `tests/evaluation/test_detector.py`

- [ ] **Step 1: Write the failing test in `tests/evaluation/test_detector.py`**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.evaluation.hallucination.detector import HallucinationDetector
from src.evaluation.hallucination.models import DetectionMode


@pytest.mark.asyncio
async def test_detector_structural_only():
    detector = HallucinationDetector(mode=DetectionMode.STRUCTURAL)
    report = await detector.analyze(
        response_text="Meiosis creates diversity.",
        citation_map=[
            {"response_segment": "Meiosis creates diversity", "evidence_ids": ["bio_1"], "source_names": ["curriculum"]},
        ],
        evidence_items=[
            {"id": "bio_1", "content": "Meiosis diversity", "source_name": "curriculum", "confidence": 0.9},
        ],
    )
    assert report.detection_mode == DetectionMode.STRUCTURAL
    assert report.supported_claims == 1


@pytest.mark.asyncio
async def test_detector_full_mode_heuristic():
    detector = HallucinationDetector(mode=DetectionMode.FULL)
    report = await detector.analyze(
        response_text="Meiosis creates genetic diversity.",
        citation_map=[
            {"response_segment": "Meiosis creates genetic diversity", "evidence_ids": ["bio_1"], "source_names": ["curriculum"]},
        ],
        evidence_items=[
            {"id": "bio_1", "content": "Meiosis is important for genetic diversity in cells", "source_name": "curriculum", "confidence": 0.9},
        ],
    )
    assert report.supported_claims == 1
    assert report.hallucination_rate == 0.0


@pytest.mark.asyncio
async def test_detector_empty_inputs():
    detector = HallucinationDetector()
    report = await detector.analyze("", [], [])
    assert report.supported_claims == 0
    assert report.unsupported_claims == 0
    assert report.hallucination_rate == 0.0


@pytest.mark.asyncio
async def test_detector_full_mode_with_llm():
    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value={
        "content": "supported",
        "model": "test",
        "confidence": 0.95,
    })

    detector = HallucinationDetector(mode=DetectionMode.FULL, router=mock_router)
    report = await detector.analyze(
        response_text="Meiosis creates diversity.",
        citation_map=[
            {"response_segment": "Meiosis creates diversity", "evidence_ids": ["bio_1"], "source_names": ["curriculum"]},
        ],
        evidence_items=[
            {"id": "bio_1", "content": "Meiosis diversity", "source_name": "curriculum", "confidence": 0.9},
        ],
    )
    assert report.supported_claims == 1
    mock_router.route.assert_called_once()
```

- [ ] **Step 2: Run to confirm they fail**

```bash
.venv/bin/python -m pytest tests/evaluation/test_detector.py -v
```

Expected: 4 FAIL

- [ ] **Step 3: Implement `src/evaluation/hallucination/detector.py`**

```python
import logging

from src.evaluation.hallucination.models import DetectionMode, HallucinationReport
from src.evaluation.hallucination.semantic import semantic_check
from src.evaluation.hallucination.structural import structural_check

logger = logging.getLogger(__name__)


class HallucinationDetector:
    def __init__(
        self,
        mode: DetectionMode = DetectionMode.FULL,
        router=None,
        overlap_threshold: float = 0.3,
    ):
        self.mode = mode
        self.router = router
        self.overlap_threshold = overlap_threshold

    async def analyze(
        self,
        response_text: str,
        citation_map: list[dict],
        evidence_items: list[dict],
    ) -> HallucinationReport:
        if not citation_map:
            return HallucinationReport(
                supported_claims=0,
                unsupported_claims=0,
                hallucination_rate=0.0,
                grounding_score=1.0,
                claim_assessments=[],
                detection_mode=self.mode,
            )

        if self.mode == DetectionMode.STRUCTURAL:
            return structural_check(citation_map, evidence_items)

        semantic = await semantic_check(
            citation_map,
            evidence_items,
            router=self.router if self.mode == DetectionMode.FULL else None,
            overlap_threshold=self.overlap_threshold,
        )

        return semantic
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/evaluation/test_detector.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Run all hallucination tests**

```bash
.venv/bin/python -m pytest tests/evaluation/ -v
```

Expected: 12 passed (4 structural + 4 semantic + 4 detector)

- [ ] **Step 6: Ruff + mypy**

```bash
.venv/bin/ruff check src/evaluation/hallucination/ tests/evaluation/
.venv/bin/mypy src/evaluation/hallucination/ --no-error-summary
```

- [ ] **Step 7: Commit**

```bash
git add src/evaluation/hallucination/detector.py tests/evaluation/test_detector.py
git commit -m "feat(hallucination): add HallucinationDetector orchestrator"
```

---

### Task 5: HallucinationNode + Graph Wiring

**Files:**
- Create: `src/graph/nodes/hallucination.py`
- Modify: `src/graph/orchestrator.py`

- [ ] **Step 1: Write the failing test**

Append at the end of `tests/test_agentic_nodes.py`:

```python
class TestHallucinationNode:
    @pytest.mark.asyncio
    async def test_hallucination_node_sets_report(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from src.graph.nodes.hallucination import HallucinationNode
        from src.graph.state import AgentState

        node = HallucinationNode()
        state = AgentState(
            user_message="test",
            citation_map=[{"response_segment": "test", "evidence_ids": ["bio_1"], "source_names": ["curriculum"]}],
            evidence_items=[{"id": "bio_1", "content": "test", "source_name": "curriculum", "confidence": 0.9}],
        )

        with patch.object(node, 'detector') as mock_detector:
            mock_detector.analyze = AsyncMock(return_value=MagicMock(
                supported_claims=1,
                unsupported_claims=0,
                hallucination_rate=0.0,
                grounding_score=1.0,
                claim_assessments=[],
                detection_mode="structural",
                model_dump=lambda: {"supported_claims": 1, "hallucination_rate": 0.0},
            ))
            result = await node(state)

        assert result.hallucination_rate == 0.0
        assert result.hallucination_report is not None

    @pytest.mark.asyncio
    async def test_hallucination_node_empty_citation_map(self):
        from src.graph.nodes.hallucination import HallucinationNode
        from src.graph.state import AgentState

        node = HallucinationNode()
        state = AgentState(
            user_message="test",
            citation_map=[],
            evidence_items=[],
        )
        result = await node(state)
        assert result.hallucination_rate == 0.0
```

- [ ] **Step 2: Run to confirm they fail**

```bash
.venv/bin/python -m pytest tests/test_agentic_nodes.py -k "TestHallucinationNode" -v
```

Expected: 2 FAIL

- [ ] **Step 3: Create `src/graph/nodes/hallucination.py`**

```python
from src.evaluation.hallucination.detector import HallucinationDetector
from src.evaluation.hallucination.models import DetectionMode
from src.graph.state import AgentState


class HallucinationNode:
    def __init__(self, mode: DetectionMode = DetectionMode.FULL, router=None):
        self.detector = HallucinationDetector(mode=mode, router=router)

    async def __call__(self, state: AgentState) -> AgentState:
        report = await self.detector.analyze(
            response_text=state.grounded_response or state.draft or "",
            citation_map=state.citation_map,
            evidence_items=state.evidence_items,
        )

        state.hallucination_rate = report.hallucination_rate
        state.hallucination_report = report.model_dump()

        return state
```

- [ ] **Step 4: Wire into orchestrator.py**

Read `src/graph/orchestrator.py`. Find where nodes are added in both `build_agentic_graph()` and `build_unified_graph()`. Add the HallucinationNode between tutor and claim_verifier:

In `build_agentic_graph()`:
```python
from src.graph.nodes.hallucination import HallucinationNode

# ... after existing nodes ...
workflow.add_node("hallucination", HallucinationNode())
# ... change edges ...
workflow.add_edge("tutor", "hallucination")
workflow.add_edge("hallucination", "claim_verifier")
```

In `build_unified_graph()`:
```python
workflow.add_node("hallucination", HallucinationNode())
# ... change edges ...
workflow.add_edge("tutor", "hallucination")
workflow.add_edge("hallucination", "claim_verifier")
```

Make sure to add the import at the top of `orchestrator.py`:
```python
from src.graph.nodes.hallucination import HallucinationNode
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_agentic_nodes.py -k "TestHallucinationNode" -v
```

Expected: 2 PASSED

- [ ] **Step 6: Ruff + mypy**

```bash
.venv/bin/ruff check src/graph/nodes/hallucination.py src/graph/orchestrator.py tests/test_agentic_nodes.py
.venv/bin/mypy src/graph/nodes/hallucination.py --no-error-summary
```

- [ ] **Step 7: Commit**

```bash
git add src/graph/nodes/hallucination.py src/graph/orchestrator.py tests/test_agentic_nodes.py
git commit -m "feat(hallucination): add HallucinationNode and wire into graph"
```

---

### Task 6: Final Verification

**Files:** All files from Tasks 1-5

- [ ] **Step 1: Run all hallucination tests**

```bash
.venv/bin/python -m pytest tests/evaluation/ -v
```

Expected: 12 PASSED

- [ ] **Step 2: Run agentic node tests**

```bash
.venv/bin/python -m pytest tests/test_agentic_nodes.py -v --tb=short
```

Expected: Pre-existing 6 failures, no new failures, new HallucinationNode tests pass

- [ ] **Step 3: Run evidence graph + retrieval loop tests**

```bash
.venv/bin/python -m pytest tests/test_evidence_graph_node.py tests/test_retrieval_loop.py -v --tb=short
```

Expected: All passing

- [ ] **Step 4: Run tutor tests**

```bash
.venv/bin/python -m pytest tests/tutor/ -v
```

Expected: 16 PASSED

- [ ] **Step 5: Full ruff check**

```bash
.venv/bin/ruff check src/evaluation/hallucination/ src/graph/nodes/hallucination.py src/graph/orchestrator.py src/graph/state.py tests/evaluation/ tests/test_agentic_nodes.py
```

- [ ] **Step 6: Commit any final fixes**

```bash
git add -A && git commit -m "chore: final verification for hallucination detection" || echo "No changes"
```
