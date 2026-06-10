# Tutor Synthesis Agent — Design Spec

**PRD-008** | 2026-06-10

## 1. Architecture

```
SynthesisNode → TutorSynthesisAgent → TutorNode → ClaimVerifierNode → SafetyNode
                    │                                        ↑
                    │                                   (uses citation_map
                    │                                    for verification)
                    ▼
              TutorResponse
              ├─ content: str
              ├─ teaching_strategy: TeachingStrategy
              ├─ citation_map: list[CitationEntry]
              ├─ misconceptions_addressed: list[str]
              └─ recommendations: list[str]
```

The `TutorSynthesisAgent` is a new agent that replaces the inline prompt-building in the current `TutorNode`. The `TutorNode` becomes a thin orchestrator:

1. Calls `TutorSynthesisAgent.generate()` with evidence + learner context
2. Agent selects strategy, personalizes output, grounds claims
3. Returns structured `TutorResponse` with `citation_map`
4. Node maps response fields to `AgentState`

## 2. Models (`src/agents/tutor/models.py`)

```python
from enum import Enum
from pydantic import BaseModel

class TeachingStrategy(str, Enum):
    SOCRATIC = "socratic"
    DIRECT_EXPLANATION = "direct_explanation"
    GUIDED_DISCOVERY = "guided_discovery"
    REMEDIATION = "remediation"
    ASSESSMENT_PREP = "assessment_prep"

class CitationEntry(BaseModel):
    response_segment: str        # short excerpt from tutor output
    evidence_ids: list[str]      # IDs from EvidenceGraph records
    source_names: list[str]      # e.g. ["curriculum", "recommendation"]

class TutorResponse(BaseModel):
    content: str
    confidence: float
    teaching_strategy: TeachingStrategy
    citation_map: list[CitationEntry]
    misconceptions_addressed: list[str]
    recommendations: list[str]
```

## 3. AgentState Additions

```python
evidence_items: list[dict] = []         # populated by EvidenceGraphNode — full evidence record dicts with id, content, source_name, score
teaching_strategy: str = ""             # serialized TeachingStrategy value
citation_map: list[dict] = []          # serialized list of CitationEntry
grounded_response: str = ""            # final response text
recommendations: list[str] = []
```

**Note:** `EvidenceGraphNode` currently sets only `state.evidence_ids`. It must be extended to also set `state.evidence_items` with the full selected evidence record dicts (`{id, content, metadata, source_name, score}`) to provide enough context for grounding.

## 4. Teaching Strategy Selector (`src/agents/tutor/strategy.py`)

Rule-based selector — no LLM call, deterministic:

| Condition | Strategy |
|-----------|----------|
| `socratic_mode=true` or `hint_level>0` | `SOCRATIC` |
| `intent == "quiz"` or assessment-prep keywords (exam, test, quiz, prepare) | `ASSESSMENT_PREP` |
| `misconception_detected` or weak areas in learner snapshot | `REMEDIATION` |
| Conceptual keywords (why, how, explain, compare, what is the difference) | `GUIDED_DISCOVERY` |
| Fallback (factual: what, when, where, define, list) | `DIRECT_EXPLANATION` |

```python
def select_teaching_strategy(
    user_message: str,
    socratic_mode: bool,
    hint_level: int,
    intent: str,
    misconception_detected: bool,
    learner_profile_block: str,
) -> TeachingStrategy
```

## 5. Personalization (`src/agents/tutor/personalization.py`)

Reuses existing pipeline data: `learner_profile_block`, `grade_level`, `language`.

```python
def build_personalization_block(
    learner_profile_block: str,
    grade_level: int | None,
    language: str,
    misconceptions: list[str],
) -> str
```

Produces a structured block for the system prompt. Returns `""` when `learner_profile_block` is empty (graceful degradation for non-agentic path).

## 6. Grounding & Citation Map (`src/agents/tutor/grounding.py`)

Two-phase approach:

**Phase 1 — Prompt instruction:** System prompt instructs LLM to emit inline citations `[id:<evidence_id>]` for each major claim, using the evidence IDs from `evidence_items`.

**Phase 2 — Post-hoc extraction:** Parse response for `[id:...]` markers and build citation_map.

```python
def extract_citations(
    response_text: str,
    evidence_items: list[dict],
) -> tuple[str, list[CitationEntry]]:
    """Extract inline citations, build citation_map, return cleaned text + entries."""
```

**Hallucination prevention:** If `evidence_items` is non-empty but response contains zero citations, the agent reduces confidence and appends a grounding disclaimer.

**Graceful degradation:** When `evidence_items` is empty (non-agentic path), citation extraction is skipped — response passes through as-is.

## 7. TutorSynthesisAgent (`src/agents/tutor/tutor.py`)

```python
class TutorSynthesisAgent:
    def __init__(self, router: ModelRouter): ...

    async def generate(
        self,
        user_message: str,
        evidence_items: list[dict],
        evidence_synthesis: str,
        grade_level: int | None,
        language: str,
        socratic_mode: bool,
        hint_level: int,
        reveal_answer: bool,
        learner_profile_block: str,
        messages: list[dict],
        intent: str,
        misconception_detected: bool,
        student_misconceptions: list[str],
    ) -> TutorResponse:
        # 1. Select strategy via strategy.py
        # 2. Build personalization block via personalization.py
        # 3. Select and populate strategy-specific prompt
        # 4. Inject evidence synthesis + personalization
        # 5. Call LLM via router
        # 6. Extract citation_map via grounding.py
        # 7. Return TutorResponse
```

## 8. Refactored TutorNode (`src/graph/nodes/tutor.py`)

| Before | After |
|--------|-------|
| Builds prompt inline | Delegates to `TutorSynthesisAgent.generate()` |
| Calls router directly | Maps `TutorResponse` fields to `AgentState` |
| Only sets `draft`, `model_used`, `confidence` | Also sets `citation_map`, `teaching_strategy`, `grounded_response`, `recommendations` |
| No post-processing | Post-processes citation extraction |

Two execution paths:
- **Agentic path** (when `evidence_items` is populated): delegates to `TutorSynthesisAgent`
- **Legacy path** (when `evidence_items` is empty): uses existing inline prompt builder — backward compatible

## 9. File Layout

```
src/agents/tutor/
├── __init__.py
├── models.py
├── strategy.py
├── personalization.py
├── grounding.py
├── prompts.py
└── tutor.py          # TutorSynthesisAgent

tests/tutor/
├── test_strategy.py
├── test_personalization.py
├── test_grounding.py
└── test_tutor.py
```

## 10. Dependency Flow

```
EvidenceGraphNode → AgentState.evidence_items
                      ↓
TutorSynthesisAgent.generate()
  ├── strategy.select()          → TeachingStrategy
  ├── personalization.build()    → prompt block
  ├── prompts.get()              → system prompt
  ├── router.call()              → LLM response
  └── grounding.extract()        → citation_map
      ↓
TutorNode → AgentState.{draft, citation_map, teaching_strategy, ...}
```

## 11. Key Design Decisions

- **Rule-based strategy selector** (no LLM) — fast, deterministic, sufficient for the 5 strategies
- **Inline citation `[id:...]` format** — LLMs can produce structured output without needing JSON mode; parsing is simple regex
- **Gradual activation** — agentic path only activates when `evidence_items` is populated; legacy path unchanged
- **Misconception detection kept as heuristic** — existing `_detect_misconception()` supplement, not replaced
- **`TutorSynthesisAgent` is a new package** following the pattern of `QueryRewriterAgent`/`SearchFanoutAgent`

## 12. Error Handling

| Scenario | Behavior |
|----------|----------|
| No `evidence_items` | Fall back to legacy path |
| LLM returns empty/malformed | Return error response, set confidence=0 |
| Citation extraction finds no markers | Append grounding disclaimer, reduce confidence |
| Learner profile unavailable | Skip personalization block |
| Strategy selector gets no match | Default to `DIRECT_EXPLANATION` |

## 13. Success Criteria

- All existing TutorNode tests pass unchanged
- New tests: 4 strategy cases, 2 personalization cases, 3 grounding cases, 4 agent integration tests
- Ruff + mypy clean on new files
- `citation_map` populated for agentic path, empty for legacy path
