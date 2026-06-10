# Hallucination Detection — Design Spec

**PRD-009 (Sub-project 1)** | 2026-06-10

## 1. Architecture

```
TutorResponse (from PRD-008)
├─ content: str
├─ citation_map: list[CitationEntry]
└─ evidence_items: list[dict]
         │
         ▼
  HallucinationDetector
  ├─ structural_check()  — fast, deterministic
  └─ semantic_check()    — optional, LLM or heuristic
         │
         ▼
  HallucinationReport
  ├─ supported_claims: int
  ├─ unsupported_claims: int
  ├─ hallucination_rate: float
  ├─ grounding_score: float
  ├─ claim_assessments: list[ClaimAssessment]
  └─ detection_mode: DetectionMode
         │
         ▼
  State → hallucination_report, hallucination_rate
```

Two detection modes:

| Mode | What | When |
|------|------|------|
| **Structural** | Checks citation_map entries against evidence_items — are cited IDs valid? | Always — fast, no LLM |
| **Semantic** | For each `citation_map` entry, checks if `response_segment` is supported by cited evidence content | Optional — LLM or heuristic overlap |

## 2. Models (`src/evaluation/hallucination/models.py`)

```python
from enum import Enum
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
    hallucination_rate: float          # 0.0 - 1.0 (unsupported/total)
    grounding_score: float             # 1.0 - hallucination_rate
    claim_assessments: list[ClaimAssessment]
    detection_mode: DetectionMode
```

## 3. Structural Check (`src/evaluation/hallucination/structural.py`)

Pure function — no LLM, 100% deterministic:

```python
def structural_check(
    citation_map: list[dict],
    evidence_items: list[dict],
) -> HallucinationReport:
```

For each `CitationEntry`:
- Check every `evidence_ids[i]` exists in `evidence_items`
- If all IDs are found → `supported=True`
- If any ID is missing → `supported=False`, `reason="evidence_id not found"`
- Calculate `hallucination_rate` as unsupported/total

Fast O(n+m) — n = citation entries, m = evidence items.

## 4. Semantic Check (`src/evaluation/hallucination/semantic.py`)

Optional — verifies claim content matches evidence content:

```python
async def semantic_check(
    citation_map: list[dict],
    evidence_items: list[dict],
    router=None,
) -> HallucinationReport:
```

Two sub-modes:

**With router (LLM):** For each claim+evidence pair, asks the LLM: "Does the following evidence support this claim?" Returns binary + confidence. Best accuracy.

**Without router (heuristic):** Token overlap between `response_segment` and evidence `content`. Preprocess both by lowercasing and removing stopwords. If overlap ratio > threshold (default 0.3), claim is supported.

## 5. HallucinationDetector (`src/evaluation/hallucination/detector.py`)

Orchestrator that combines both checks:

```python
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
        # Always runs structural check
        report = structural_check(citation_map, evidence_items)

        # Optional semantic check
        if self.mode in (DetectionMode.SEMANTIC, DetectionMode.FULL):
            semantic = await semantic_check(
                citation_map, evidence_items, self.router
            )
            # Merge: use semantic results for claim_assessments
            # but keep hallucination_rate from structural as fallback

        return report
```

## 6. LangGraph Integration

New node: `HallucinationNode` positioned between `TutorNode` and `ClaimVerifierNode`.

```
synthesis → tutor → hallucination → claim_verifier → safety
```

The `HallucinationNode`:
1. Reads `citation_map` and `evidence_items` from state
2. Calls `HallucinationDetector.analyze()`
3. Sets `state.hallucination_report` and `state.hallucination_rate`
4. Passes state through to `ClaimVerifierNode`

## 7. AgentState Additions

```python
hallucination_report: Optional[dict] = None
hallucination_rate: float = 0.0
```

## 8. File Layout

```
src/evaluation/hallucination/
├── __init__.py
├── models.py
├── structural.py
├── semantic.py
└── detector.py

tests/evaluation/
├── __init__.py
├── test_structural.py
├── test_semantic.py
└── test_detector.py
```

## 9. Error Handling

| Scenario | Behavior |
|----------|----------|
| Empty `citation_map` | Return report with 0 claims, hallucination_rate=0 |
| Empty `evidence_items` | All claims marked unsupported, hallucination_rate=1.0 |
| LLM call fails in semantic check | Fall back to heuristic overlap |
| `response_text` empty | Return report with 0 claims |
| `router=None` with SEMANTIC/FULL mode | Use heuristic overlap automatically |

## 10. Success Criteria

- All structural cases covered (valid IDs, missing IDs, empty, mixed)
- Semantic cases covered (supported claim, unsupported claim, empty)
- Detector integration tests (merging structural + semantic)
- Ruff + mypy clean
- `HallucinationNode` wired in graph without breaking existing flow
- Pre-existing tests unchanged
