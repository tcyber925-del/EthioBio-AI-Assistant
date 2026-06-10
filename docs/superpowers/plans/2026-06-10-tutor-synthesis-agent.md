# PRD-008 Tutor Synthesis Agent — Implementation Plan

> **For agentic workers:** Use subagent-driven-development or executing-plans to implement step-by-step.

**Goal:** Implement grounding enforcement (citation_map), teaching strategy selection, personalization, and misconception remediation for the TutorNode.

**Architecture:** New `src/agents/tutor/` package with Focused modules (models, strategy, personalization, grounding, prompts) orchestrated by `TutorSynthesisAgent`. Existing `TutorNode` delegates to agent when `evidence_items` is populated; keeps legacy path for backward compatibility.

**Tech Stack:** Python 3.12+, Pydantic (models), asyncio, LLM via `ModelRouter`, LangGraph (state), pytest (async tests with mocking)

---

## File Structure

```
Create: src/agents/tutor/__init__.py
Create: src/agents/tutor/models.py           # TutorResponse, CitationEntry, TeachingStrategy
Create: src/agents/tutor/strategy.py         # select_teaching_strategy()
Create: src/agents/tutor/personalization.py  # build_personalization_block()
Create: src/agents/tutor/grounding.py        # extract_citations()
Create: src/agents/tutor/prompts.py          # strategy-specific system prompts
Create: src/agents/tutor/tutor.py            # TutorSynthesisAgent

Modify: src/graph/state.py                   # Add 5 fields: evidence_items, teaching_strategy, citation_map, grounded_response, recommendations
Modify: src/graph/nodes/evidence_graph.py    # Populate evidence_items alongside evidence_ids
Modify: src/graph/nodes/tutor.py             # Refactor to delegate to TutorSynthesisAgent

Create: tests/tutor/__init__.py
Create: tests/tutor/test_strategy.py
Create: tests/tutor/test_personalization.py
Create: tests/tutor/test_grounding.py
Create: tests/tutor/test_tutor.py

Modify: tests/test_evidence_graph_node.py    # Add evidence_items assertion
```

---

### Task 1: Models + AgentState fields

**Files:**
- Create: `src/agents/tutor/__init__.py`
- Create: `src/agents/tutor/models.py`
- Create: `tests/tutor/__init__.py`
- Modify: `src/graph/state.py`

- [ ] **Step 1: Create models.py**

```python
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TeachingStrategy(str, Enum):
    SOCRATIC = "socratic"
    DIRECT_EXPLANATION = "direct_explanation"
    GUIDED_DISCOVERY = "guided_discovery"
    REMEDIATION = "remediation"
    ASSESSMENT_PREP = "assessment_prep"


class CitationEntry(BaseModel):
    response_segment: str
    evidence_ids: list[str]
    source_names: list[str]
    source_name: Optional[str] = None


class TutorResponse(BaseModel):
    content: str
    confidence: float
    teaching_strategy: TeachingStrategy
    citation_map: list[CitationEntry]
    misconceptions_addressed: list[str]
    recommendations: list[str]
```

- [ ] **Step 2: Create `src/agents/tutor/__init__.py`** with re-exports:

```python
from src.agents.tutor.models import CitationEntry, TeachingStrategy, TutorResponse
from src.agents.tutor.strategy import select_teaching_strategy
from src.agents.tutor.personalization import build_personalization_block
from src.agents.tutor.grounding import extract_citations
from src.agents.tutor.tutor import TutorSynthesisAgent

__all__ = [
    "CitationEntry",
    "TeachingStrategy",
    "TutorResponse",
    "select_teaching_strategy",
    "build_personalization_block",
    "extract_citations",
    "TutorSynthesisAgent",
]
```

- [ ] **Step 3: Create empty `tests/tutor/__init__.py`** (empty file)

- [ ] **Step 4: Add fields to AgentState in `src/graph/state.py`**

Find the field definitions block (around line 90-110). Add after `evidence_ids`:

```python
    evidence_items: list[dict] = field(default_factory=list)
    teaching_strategy: str = ""
    citation_map: list[dict] = field(default_factory=list)
    grounded_response: str = ""
    recommendations: list[str] = field(default_factory=list)
```

- [ ] **Step 5: Run ruff to verify imports are clean**

```bash
.venv/bin/ruff check src/agents/tutor/models.py src/agents/tutor/__init__.py src/graph/state.py tests/tutor/__init__.py
```

- [ ] **Step 6: Run mypy on new files**

```bash
.venv/bin/mypy src/agents/tutor/models.py src/agents/tutor/__init__.py src/graph/state.py --no-error-summary
```

Expected: No new errors in our files (pre-existing errors in other files are OK).

- [ ] **Step 7: Commit**

```bash
git add src/agents/tutor/ tests/tutor/ src/graph/state.py
git commit -m "feat(tutor): add models, TeachingStrategy enum, and AgentState fields"
```

---

### Task 2: Teaching Strategy Selector

**Files:**
- Create: `src/agents/tutor/strategy.py`
- Create: `tests/tutor/test_strategy.py`

- [ ] **Step 1: Write the failing test**

Create `tests/tutor/test_strategy.py`:

```python
import pytest

from src.agents.tutor.strategy import select_teaching_strategy
from src.agents.tutor.models import TeachingStrategy


def test_socratic_mode_returns_socratic():
    result = select_teaching_strategy(
        user_message="What is mitosis?",
        socratic_mode=True,
        hint_level=0,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.SOCRATIC


def test_hint_level_triggers_socratic():
    result = select_teaching_strategy(
        user_message="What is mitosis?",
        socratic_mode=False,
        hint_level=2,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.SOCRATIC


def test_quiz_intent_returns_assessment_prep():
    result = select_teaching_strategy(
        user_message="Quiz me on genetics",
        socratic_mode=False,
        hint_level=0,
        intent="quiz",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.ASSESSMENT_PREP


def test_misconception_returns_remediation():
    result = select_teaching_strategy(
        user_message="Why do I struggle with genetics?",
        socratic_mode=False,
        hint_level=0,
        intent="tutor",
        misconception_detected=True,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.REMEDIATION


def test_conceptual_question_returns_guided_discovery():
    result = select_teaching_strategy(
        user_message="Why is meiosis important?",
        socratic_mode=False,
        hint_level=0,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.GUIDED_DISCOVERY


def test_factual_question_returns_direct_explanation():
    result = select_teaching_strategy(
        user_message="What is osmosis?",
        socratic_mode=False,
        hint_level=0,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.DIRECT_EXPLANATION


def test_weak_area_in_profile_returns_remediation():
    result = select_teaching_strategy(
        user_message="Tell me about genetics",
        socratic_mode=False,
        hint_level=0,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="weak_areas: genetics, cell division",
    )
    assert result == TeachingStrategy.REMEDIATION
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/tutor/test_strategy.py -v
```

Expected: 7 tests FAIL with `ModuleNotFoundError` or `function not defined`

- [ ] **Step 3: Implement `src/agents/tutor/strategy.py`**

```python
import re
from src.agents.tutor.models import TeachingStrategy

CONCEPTUAL_KEYWORDS = [
    "why", "how", "explain", "compare", "contrast",
    "what is the difference", "what's the difference",
    "what is the relationship", "what's the relationship",
]

ASSESSMENT_KEYWORDS = [
    "exam", "test", "quiz", "prepare", "practice",
    "question", "assessment", "review",
]

def select_teaching_strategy(
    user_message: str,
    socratic_mode: bool,
    hint_level: int,
    intent: str,
    misconception_detected: bool,
    learner_profile_block: str,
) -> TeachingStrategy:
    if socratic_mode or hint_level > 0:
        return TeachingStrategy.SOCRATIC

    if intent == "quiz":
        return TeachingStrategy.ASSESSMENT_PREP

    msg_lower = user_message.lower()
    if re.search(r'\b(?:exam|test|quiz|prepare|practice|assessment)\b', msg_lower):
        return TeachingStrategy.ASSESSMENT_PREP

    if misconception_detected or "weak_areas" in learner_profile_block.lower():
        return TeachingStrategy.REMEDIATION

    for kw in CONCEPTUAL_KEYWORDS:
        if kw in msg_lower:
            return TeachingStrategy.GUIDED_DISCOVERY

    return TeachingStrategy.DIRECT_EXPLANATION
```

- [ ] **Step 4: Run tests again to verify they pass**

```bash
.venv/bin/python -m pytest tests/tutor/test_strategy.py -v
```

Expected: 7 PASSED

- [ ] **Step 5: Ruff + mypy**

```bash
.venv/bin/ruff check src/agents/tutor/strategy.py tests/tutor/test_strategy.py
.venv/bin/mypy src/agents/tutor/strategy.py --no-error-summary
```

- [ ] **Step 6: Commit**

```bash
git add src/agents/tutor/strategy.py tests/tutor/test_strategy.py
git commit -m "feat(tutor): add teaching strategy selector with 5 strategies"
```

---

### Task 3: Personalization Module

**Files:**
- Create: `src/agents/tutor/personalization.py`
- Create: `tests/tutor/test_personalization.py`

- [ ] **Step 1: Write the failing test**

Create `tests/tutor/test_personalization.py`:

```python
import pytest
from src.agents.tutor.personalization import build_personalization_block


def test_with_full_profile():
    block = build_personalization_block(
        learner_profile_block="weak_areas: genetics",
        grade_level=10,
        language="am",
        misconceptions=["confuses dominant and recessive"],
    )
    assert "Grade Level: 10" in block
    assert "Language: am" in block
    assert "weak_areas: genetics" in block
    assert "confuses dominant and recessive" in block


def test_empty_profile_returns_empty():
    block = build_personalization_block(
        learner_profile_block="",
        grade_level=None,
        language="en",
        misconceptions=[],
    )
    assert block == ""


def test_no_misconceptions():
    block = build_personalization_block(
        learner_profile_block="grade_level: 8",
        grade_level=8,
        language="en",
        misconceptions=[],
    )
    assert "Grade Level: 8" in block
    assert "Misconceptions" not in block
```

- [ ] **Step 2: Run to verify they fail**

```bash
.venv/bin/python -m pytest tests/tutor/test_personalization.py -v
```

Expected: 3 FAIL

- [ ] **Step 3: Implement `src/agents/tutor/personalization.py`**

```python
def build_personalization_block(
    learner_profile_block: str,
    grade_level: int | None,
    language: str,
    misconceptions: list[str],
) -> str:
    if not learner_profile_block:
        return ""

    lines = ["## Learner Profile"]
    if grade_level:
        lines.append(f"- Grade Level: {grade_level}")
    lines.append(f"- Language: {language}")

    lines.append("")
    lines.append("### Learner Data")
    lines.append(learner_profile_block)

    if misconceptions:
        lines.append("")
        lines.append("### Known Misconceptions")
        for m in misconceptions:
            lines.append(f"- {m}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/tutor/test_personalization.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Ruff + mypy**

```bash
.venv/bin/ruff check src/agents/tutor/personalization.py tests/tutor/test_personalization.py
.venv/bin/mypy src/agents/tutor/personalization.py --no-error-summary
```

- [ ] **Step 6: Commit**

```bash
git add src/agents/tutor/personalization.py tests/tutor/test_personalization.py
git commit -m "feat(tutor): add personalization block builder"
```

---

### Task 4: Grounding + Citation Map

**Files:**
- Create: `src/agents/tutor/grounding.py`
- Create: `tests/tutor/test_grounding.py`

- [ ] **Step 1: Write the failing test**

Create `tests/tutor/test_grounding.py`:

```python
import pytest
from src.agents.tutor.grounding import extract_citations


def test_extracts_single_citation():
    text = "Meiosis produces diverse cells. [id:bio_ch4_22]"
    cleaned, entries = extract_citations(text, [
        {"id": "bio_ch4_22", "content": "Meiosis creates diversity", "source_name": "curriculum"}
    ])
    assert cleaned == "Meiosis produces diverse cells."
    assert len(entries) == 1
    assert entries[0].evidence_ids == ["bio_ch4_22"]
    assert "curriculum" in entries[0].source_names


def test_extracts_multiple_citations():
    text = "Mitosis has 4 phases. [id:bio_ch3_10] Meiosis has 8. [id:bio_ch4_22]"
    cleaned, entries = extract_citations(text, [
        {"id": "bio_ch3_10", "content": "Mitosis phases", "source_name": "curriculum"},
        {"id": "bio_ch4_22", "content": "Meiosis stages", "source_name": "curriculum"},
    ])
    assert len(entries) == 2


def test_no_citations_returns_empty():
    text = "Just some text without citations."
    cleaned, entries = extract_citations(text, [])
    assert cleaned == text
    assert entries == []


def test_unknown_evidence_id():
    text = "Some claim. [id:unknown_id]"
    cleaned, entries = extract_citations(text, [
        {"id": "known_id", "content": "Known", "source_name": "curriculum"}
    ])
    assert len(entries) == 1
    assert entries[0].evidence_ids == ["unknown_id"]
    assert entries[0].source_names == ["unknown"]
```

- [ ] **Step 2: Run to verify they fail**

```bash
.venv/bin/python -m pytest tests/tutor/test_grounding.py -v
```

Expected: 4 FAIL

- [ ] **Step 3: Implement `src/agents/tutor/grounding.py`**

```python
import re
from src.agents.tutor.models import CitationEntry

CITATION_PATTERN = re.compile(r'\[id:([^\]]+)\]')

def extract_citations(
    response_text: str,
    evidence_items: list[dict],
) -> tuple[str, list[CitationEntry]]:
    evidence_map: dict[str, dict] = {}
    for item in evidence_items:
        eid = item.get("id", "")
        if eid:
            evidence_map[eid] = item

    matches = list(CITATION_PATTERN.finditer(response_text))
    if not matches:
        return response_text, []

    cleaned = CITATION_PATTERN.sub("", response_text).strip()
    cleaned = re.sub(r'  +', " ", cleaned)

    entries: list[CitationEntry] = []
    for m in matches:
        eid = m.group(1)
        evidence = evidence_map.get(eid, {})
        entries.append(CitationEntry(
            response_segment="",
            evidence_ids=[eid],
            source_names=[evidence.get("source_name", "unknown")] if evidence else ["unknown"],
        ))

    return cleaned, entries
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/tutor/test_grounding.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Ruff + mypy**

```bash
.venv/bin/ruff check src/agents/tutor/grounding.py tests/tutor/test_grounding.py
.venv/bin/mypy src/agents/tutor/grounding.py --no-error-summary
```

- [ ] **Step 6: Commit**

```bash
git add src/agents/tutor/grounding.py tests/tutor/test_grounding.py
git commit -m "feat(tutor): add citation map extraction from LLM output"
```

---

### Task 5: Strategy-Specific Prompts

**Files:**
- Create: `src/agents/tutor/prompts.py`

- [ ] **Step 1: Implement `src/agents/tutor/prompts.py`**

Contains 5 strategy-specific system prompt constants, plus a `get_system_prompt()` selector. Reuses the existing SOCRATIC prompt from the current TutorNode for `SOCRATIC`, and defines new ones for the other 4 strategies.

```python
from src.agents.tutor.models import TeachingStrategy

DIRECT_EXPLANATION_PROMPT = """You are EthioBio Tutor, an AI biology tutor for Ethiopian middle and high school students (Grades 7-12).

INSTRUCTIONS:
1. Answer the student's question using ONLY the evidence provided below.
2. For EVERY major claim, add an inline citation [id:<evidence_id>] using the evidence IDs provided.
3. Adapt explanations to the student's grade level.
4. If the evidence does not contain enough information to fully answer, say so clearly.
5. Keep explanations clear, simple, and focused.
6. When available, cite sources at the end of each key point."""

GUIDED_DISCOVERY_PROMPT = """You are EthioBio Tutor in Guided Discovery mode.

INSTRUCTIONS:
1. Guide the student to discover the answer through structured questions and hints.
2. For EVERY claim you make, add inline citation [id:<evidence_id>] using the evidence IDs provided.
3. Break down complex concepts into smaller steps.
4. Praise correct reasoning, gently redirect incorrect assumptions.
5. Use evidence to support your guidance."""

REMEDIATION_PROMPT = """You are EthioBio Tutor in Remediation mode.

INSTRUCTIONS:
1. First, identify the student's misconception clearly.
2. Explain why the misconception is incorrect, citing evidence [id:<evidence_id>].
3. Provide the correct mental model using evidence.
4. Add inline citations [id:<evidence_id>] for all claims.
5. Offer targeted practice suggestions to reinforce correct understanding."""

ASSESSMENT_PREP_PROMPT = """You are EthioBio Tutor in Assessment Prep mode.

INSTRUCTIONS:
1. Provide exam-style explanations using only the evidence provided.
2. Add inline citations [id:<evidence_id>] for every key fact.
3. Highlight what students typically confuse.
4. Suggest what to focus on based on the curriculum evidence.
5. Keep responses structured and focused on key concepts."""

PROMPT_MAP = {
    TeachingStrategy.DIRECT_EXPLANATION: DIRECT_EXPLANATION_PROMPT,
    TeachingStrategy.GUIDED_DISCOVERY: GUIDED_DISCOVERY_PROMPT,
    TeachingStrategy.REMEDIATION: REMEDIATION_PROMPT,
    TeachingStrategy.ASSESSMENT_PREP: ASSESSMENT_PREP_PROMPT,
}

SOCARIC_BASE_PROMPT = """You are EthioBio Tutor in Socratic Mode, an AI biology tutor for Ethiopian middle and high school students (Grades 7-12).
The curriculum is in English. Follow language instructions provided in the user message.

STRUCTURED RESPONSE FORMAT:
When a student asks a biology question, your response MUST contain at least one guiding question. Follow this structure:
1. ACKNOWLEDGE — Briefly affirm the question (1 sentence).
2. GUIDE — Ask 1-2 probing questions that help the student reason toward the answer themselves.
3. PROMPT — End by inviting the student to share their thinking.

Rules:
1. DO NOT give direct answers. Ask guiding questions that help the student discover the answer themselves.
2. Adapt questions to the student's grade level.
3. When provided with curriculum context, use it to formulate better guiding questions.
4. Keep responses brief and focused on the next guiding question.
5. Praise correct reasoning and gently redirect incorrect assumptions.
6. If the student is stuck after several exchanges, you may provide a hint to keep them moving.
7. Always encourage the student to think step by step.
8. If the student's response contains a conceptual error, gently correct them by explaining why their reasoning is incorrect, then continue with a guiding question. Be supportive — never condescending."""

def get_system_prompt(strategy: TeachingStrategy) -> str:
    if strategy == TeachingStrategy.SOCRATIC:
        return SOCARIC_BASE_PROMPT
    return PROMPT_MAP.get(strategy, DIRECT_EXPLANATION_PROMPT)
```

- [ ] **Step 2: Ruff**

```bash
.venv/bin/ruff check src/agents/tutor/prompts.py
```

- [ ] **Step 3: Commit**

```bash
git add src/agents/tutor/prompts.py
git commit -m "feat(tutor): add strategy-specific system prompts"
```

---

### Task 6: TutorSynthesisAgent

**Files:**
- Create: `src/agents/tutor/tutor.py`
- Create: `tests/tutor/test_tutor.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/tutor/test_tutor.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.tutor.tutor import TutorSynthesisAgent
from src.agents.tutor.models import TeachingStrategy


@pytest.mark.asyncio
async def test_agent_selects_strategy_and_extracts_citations():
    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value={
        "content": "Meiosis produces diverse cells. [id:bio_ch4_22]",
        "model": "test-model",
        "confidence": 0.9,
    })

    agent = TutorSynthesisAgent(mock_router)
    response = await agent.generate(
        user_message="What is meiosis?",
        evidence_items=[{"id": "bio_ch4_22", "content": "Meiosis diversity", "source_name": "curriculum"}],
        evidence_synthesis="Synthesis text",
        grade_level=10,
        language="en",
        socratic_mode=False,
        hint_level=0,
        reveal_answer=False,
        learner_profile_block="",
        messages=[],
        intent="tutor",
        misconception_detected=False,
        student_misconceptions=[],
    )

    assert response.content == "Meiosis produces diverse cells."
    assert response.teaching_strategy == TeachingStrategy.DIRECT_EXPLANATION
    assert len(response.citation_map) == 1
    assert response.citation_map[0].evidence_ids == ["bio_ch4_22"]
    assert response.confidence == 0.9


@pytest.mark.asyncio
async def test_agent_uses_socratic_when_in_socratic_mode():
    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value={
        "content": "What do you think? [id:bio_ch4_22]",
        "model": "test-model",
        "confidence": 0.8,
    })

    agent = TutorSynthesisAgent(mock_router)
    response = await agent.generate(
        user_message="What is meiosis?",
        evidence_items=[],
        evidence_synthesis="",
        grade_level=None,
        language="en",
        socratic_mode=True,
        hint_level=0,
        reveal_answer=False,
        learner_profile_block="",
        messages=[],
        intent="tutor",
        misconception_detected=False,
        student_misconceptions=[],
    )

    assert response.teaching_strategy == TeachingStrategy.SOCRATIC
```

- [ ] **Step 2: Run to verify they fail**

```bash
.venv/bin/python -m pytest tests/tutor/test_tutor.py -v
```

Expected: 2 FAIL

- [ ] **Step 3: Implement `src/agents/tutor/tutor.py`**

```python
import logging

from src.agents.tutor.grounding import extract_citations
from src.agents.tutor.models import TeachingStrategy, TutorResponse
from src.agents.tutor.personalization import build_personalization_block
from src.agents.tutor.prompts import get_system_prompt
from src.agents.tutor.strategy import select_teaching_strategy
from src.llm.router import ModelRouter

logger = logging.getLogger(__name__)

HINT_PROMPTS = {
    1: "\n\nThe student has requested a HINT (Level 1). Give a BROAD, general hint that points them in the right direction without giving away the answer.",
    2: "\n\nThe student has requested a HINT (Level 2). Give a MORE SPECIFIC hint that narrows down the possibilities significantly.",
    3: "\n\nThe student has requested a HINT (Level 3). Give a VERY SPECIFIC hint that leads almost directly to the answer.",
}

REVEAL_PROMPT = "\n\nThe student has requested the final answer. Provide the complete correct answer with a full explanation. Cite curriculum sources when available."


class TutorSynthesisAgent:
    def __init__(self, router: ModelRouter):
        self.router = router

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
        strategy = select_teaching_strategy(
            user_message=user_message,
            socratic_mode=socratic_mode,
            hint_level=hint_level,
            intent=intent,
            misconception_detected=misconception_detected,
            learner_profile_block=learner_profile_block,
        )

        system = get_system_prompt(strategy)

        personalization = build_personalization_block(
            learner_profile_block=learner_profile_block,
            grade_level=grade_level,
            language=language,
            misconceptions=student_misconceptions,
        )
        if personalization:
            system += "\n\n" + personalization

        if evidence_synthesis:
            system += f"\n\n## Evidence Synthesis\n{evidence_synthesis}\n\nUse the above evidence to ground your answer. Cite evidence IDs using [id:<evidence_id>]."
        elif evidence_items:
            items_text = "\n".join(
                f"- [{e.get('id', '?')}] {e.get('content', '')[:200]}"
                for e in evidence_items
            )
            system += f"\n\n## Evidence Items\n{items_text}\n\nUse the above evidence to ground your answer. Cite evidence IDs using [id:<evidence_id>]."

        if reveal_answer:
            system += REVEAL_PROMPT
        elif hint_level > 0 and hint_level in HINT_PROMPTS:
            system += HINT_PROMPTS[hint_level]

        grade_context = f" (Grade {grade_level})" if grade_level else ""
        if language == "am":
            lang_context = "Respond entirely in Amharic (አማርኛ). Use Amharic biology terminology."
        elif language == "both":
            lang_context = "Answer in English with Amharic explanation. Provide key terms in both languages."
        else:
            lang_context = "Answer in English."

        user_prompt = f"[Grade{grade_context}] {lang_context}\n\nStudent question: {user_message}"
        llm_messages = [
            {"role": "system", "content": system},
            *messages,
            {"role": "user", "content": user_prompt},
        ]

        result = await self.router.route(
            llm_messages, request_type="tutor", temperature=0.7, max_tokens=2048,
        )

        content = result["content"]
        cleaned_content, citation_map = extract_citations(content, evidence_items)

        if evidence_items and not citation_map:
            logger.warning("tutor_response_missing_citations")
            disclaimer = "\n\n*Note: Some claims could not be directly cited to the available evidence.*"
            cleaned_content += disclaimer

        return TutorResponse(
            content=cleaned_content,
            confidence=result.get("confidence", 0.0),
            teaching_strategy=strategy,
            citation_map=citation_map,
            misconceptions_addressed=student_misconceptions if misconception_detected else [],
            recommendations=[],
        )
```

- [ ] **Step 4: Update `__init__.py` re-export** (already done in Task 1, verify TutorSynthesisAgent is in __all__)

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/tutor/test_tutor.py -v
```

Expected: 2 PASSED. Then run all tutor tests:

```bash
.venv/bin/python -m pytest tests/tutor/ -v
```

Expected: 16 total (7 strategy + 3 personalization + 4 grounding + 2 agent)

- [ ] **Step 6: Ruff + mypy**

```bash
.venv/bin/ruff check src/agents/tutor/tutor.py tests/tutor/test_tutor.py src/agents/tutor/__init__.py
.venv/bin/mypy src/agents/tutor/tutor.py --no-error-summary
```

- [ ] **Step 7: Commit**

```bash
git add src/agents/tutor/tutor.py src/agents/tutor/__init__.py tests/tutor/test_tutor.py
git commit -m "feat(tutor): add TutorSynthesisAgent with grounding and strategy"
```

---

### Task 7: EvidenceGraphNode — Populate evidence_items

**Files:**
- Modify: `src/graph/nodes/evidence_graph.py`
- Modify: `tests/test_evidence_graph_node.py`

The `EvidenceGraphNode` currently sets `state.evidence_ids` (list of string IDs). It must also set `state.evidence_items` (full evidence record dicts) to provide enough context for the TutorSynthesisAgent.

- [ ] **Step 1: Read the evidence_graph node to find where `state.evidence_ids` is set**

Look at the `__call__` method around the `persist`, `select`, and `coverage` section. Identify where `state.evidence_ids` is assigned.

- [ ] **Step 2: Write failing test**

In `tests/test_evidence_graph_node.py`, find/test for `test_node_updates_evidence_ids`. Add a new assertion:

```python
async def test_node_sets_evidence_items(self):
    """Evidence graph node should populate evidence_items with full dicts."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from src.graph.nodes.evidence_graph import EvidenceGraphNode
    from src.graph.state import AgentState

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_factory = MagicMock()
    mock_factory.return_value = mock_session

    # Simulate EvidenceRecord objects from select_evidence
    mock_record_1 = MagicMock()
    mock_record_1.id = "evid-1"
    mock_record_1.content = "Meiosis creates diversity"
    mock_record_1.source_name = "curriculum"
    mock_record_1.confidence = 0.9
    mock_record_1.archived = False

    mock_selector = AsyncMock()
    mock_selector.select_evidence.return_value = [mock_record_1]

    node = EvidenceGraphNode(db_session_factory=mock_factory)
    with patch.object(node, 'selector', mock_selector):
        with patch.object(node, 'summarizer', AsyncMock()):
            state = AgentState(
                user_message="test",
                retrieval_source_results={
                    "curriculum": [{"content": "test", "metadata": {}, "score": 0.9, "source": "curriculum"}],
                },
            )
            result = await node(state)

    assert len(result.evidence_items) >= 1
    assert result.evidence_items[0]["id"] == "evid-1"
    assert "content" in result.evidence_items[0]
    assert "source_name" in result.evidence_items[0]
```

- [ ] **Step 3: Run the evidence graph tests**

```bash
.venv/bin/python -m pytest tests/test_evidence_graph_node.py -v
```

Expected: 11 collected, 1 new FAIL

- [ ] **Step 4: Modify `src/graph/nodes/evidence_graph.py`**

Find where `state.evidence_ids = selected_ids` is set. Add `state.evidence_items` right after:

```python
        state.evidence_ids = selected_ids
        state.evidence_items = [
            {
                "id": e.id,
                "content": e.content,
                "source_name": e.source_name,
                "confidence": e.confidence,
            }
            for e in evidence_list
        ]
```

Note: the exact variable name (`evidence_list` vs `selected`) depends on the actual code. Read the file first to get the correct variable.

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_evidence_graph_node.py -v
```

Expected: 11 (or 12) PASSED

- [ ] **Step 6: Ruff + mypy**

```bash
.venv/bin/ruff check src/graph/nodes/evidence_graph.py tests/test_evidence_graph_node.py
.venv/bin/mypy src/graph/nodes/evidence_graph.py --no-error-summary
```

- [ ] **Step 7: Commit**

```bash
git add src/graph/nodes/evidence_graph.py tests/test_evidence_graph_node.py
git commit -m "feat(evidence): populate evidence_items with full record dicts"
```

---

### Task 8: Refactor TutorNode

**Files:**
- Modify: `src/graph/nodes/tutor.py`
- Create/Modify: `tests/test_agentic_nodes.py` (add TutorNode integration tests)

- [ ] **Step 1: Write failing tests for the refactored TutorNode**

Append inside `tests/test_agentic_nodes.py` (add a new test class at the end):

```python
class TestTutorNodePRD008:
    """Tests for the refactored TutorNode with TutorSynthesisAgent."""

    @pytest.mark.asyncio
    async def test_agentic_path_delegates_to_tutor_synthesis_agent(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from src.graph.nodes.tutor import TutorNode
        from src.graph.state import AgentState
        from src.llm.router import ModelRouter
        from src.agents.tutor.models import TutorResponse, TeachingStrategy, CitationEntry

        mock_router = MagicMock(spec=ModelRouter)
        node = TutorNode(mock_router)

        state = AgentState(
            user_message="What is meiosis?",
            evidence_items=[{"id": "bio_1", "content": "Meiosis", "source_name": "curriculum"}],
            evidence_synthesis="Synthesis",
            grade_level=10,
            language="en",
            socratic_mode=False,
            hint_level=0,
            reveal_answer=False,
            learner_profile_block="",
            messages=[],
            intent="tutor",
            misconception_detected=False,
        )

        expected_response = TutorResponse(
            content="Meiosis produces diversity.",
            confidence=0.9,
            teaching_strategy=TeachingStrategy.DIRECT_EXPLANATION,
            citation_map=[CitationEntry(response_segment="", evidence_ids=["bio_1"], source_names=["curriculum"])],
            misconceptions_addressed=[],
            recommendations=[],
        )

        with patch.object(node, 'agent') as mock_agent:
            mock_agent.generate = AsyncMock(return_value=expected_response)
            result = await node(state)

        assert result.draft == "Meiosis produces diversity."
        assert result.teaching_strategy == "direct_explanation"
        assert len(result.citation_map) == 1
        assert result.citation_map[0]["evidence_ids"] == ["bio_1"]
        assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_legacy_path_when_no_evidence_items(self):
        from unittest.mock import patch
        from src.graph.nodes.tutor import TutorNode
        from src.graph.state import AgentState
        from src.llm.router import ModelRouter

        mock_router = MagicMock(spec=ModelRouter)
        node = TutorNode(mock_router)

        mock_router.route = AsyncMock(return_value={
            "content": "Legacy response",
            "model": "test",
            "confidence": 0.8,
        })

        state = AgentState(
            user_message="What is mitosis?",
            evidence_items=[],
            context="Some curriculum context",
            grade_level=8,
            language="en",
            socratic_mode=False,
            messages=[],
        )

        result = await node(state)
        assert result.draft == "Legacy response"
        assert result.teaching_strategy == ""  # not populated in legacy path
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/test_agentic_nodes.py -k "TestTutorNodePRD008" -v
```

Expected: 2 FAIL

- [ ] **Step 3: Refactor TutorNode**

Read the current `src/graph/nodes/tutor.py`. Modify:

1. Add import of `TutorSynthesisAgent` from `src.agents.tutor.tutor`
2. In `__init__`, create `self.agent = TutorSynthesisAgent(router)` 
3. In `__call__`, add a branch: if `state.evidence_items` is non-empty, use the agentic path:

```python
async def __call__(self, state: AgentState) -> AgentState:
    if state.evidence_items:
        return await self._agentic_call(state)
    return await self._legacy_call(state)
```

4. Move existing logic to `_legacy_call(self, state)` (exactly as-is)
5. Add `_agentic_call(self, state)`:

```python
async def _agentic_call(self, state: AgentState) -> AgentState:
    student_misconceptions = []
    if state.misconception_correction:
        student_misconceptions = [state.misconception_correction]

    response = await self.agent.generate(
        user_message=state.user_message,
        evidence_items=state.evidence_items,
        evidence_synthesis=state.evidence_synthesis,
        grade_level=state.grade_level,
        language=state.language,
        socratic_mode=state.socratic_mode,
        hint_level=state.hint_level,
        reveal_answer=state.reveal_answer,
        learner_profile_block=state.learner_profile_block or "",
        messages=state.messages,
        intent=state.intent,
        misconception_detected=state.misconception_detected,
        student_misconceptions=student_misconceptions,
    )

    state.draft = response.content
    state.grounded_response = response.content
    state.confidence = response.confidence
    state.teaching_strategy = response.teaching_strategy.value
    state.citation_map = [e.model_dump() for e in response.citation_map]
    state.recommendations = response.recommendations
    state.misconception_correction = ", ".join(response.misconceptions_addressed) if response.misconceptions_addressed else state.misconception_correction

    return state
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_agentic_nodes.py -k "TestTutorNodePRD008" -v
```

Expected: 2 PASSED

```bash
.venv/bin/python -m pytest tests/test_agentic_nodes.py -v --tb=short
```

Expected: pre-existing 6 failures remain, no new failures introduced.

- [ ] **Step 5: Ruff + mypy**

```bash
.venv/bin/ruff check src/graph/nodes/tutor.py tests/test_agentic_nodes.py
.venv/bin/mypy src/graph/nodes/tutor.py --no-error-summary
```

- [ ] **Step 6: Commit**

```bash
git add src/graph/nodes/tutor.py tests/test_agentic_nodes.py
git commit -m "feat(tutor): refactor TutorNode to delegate to TutorSynthesisAgent"
```

---

### Task 9: Final verification

**Files:** All files from Tasks 1-8

- [ ] **Step 1: Run all tutor-related tests**

```bash
.venv/bin/python -m pytest tests/tutor/ -v
```

Expected: 16 PASSED

- [ ] **Step 2: Run evidence graph tests**

```bash
.venv/bin/python -m pytest tests/test_evidence_graph_node.py -v
```

Expected: 11+ PASSED

- [ ] **Step 3: Run agentic node tests (excluding pre-existing failures)**

```bash
.venv/bin/python -m pytest tests/test_agentic_nodes.py -v --tb=short
```

Expected: Pre-existing 6 failures, no new failures.

- [ ] **Step 4: Run retrieval loop tests**

```bash
.venv/bin/python -m pytest tests/test_retrieval_loop.py -v
```

Expected: 21 PASSED

- [ ] **Step 5: Full ruff check**

```bash
.venv/bin/ruff check src/agents/tutor/ src/graph/nodes/tutor.py src/graph/nodes/evidence_graph.py src/graph/state.py tests/tutor/ tests/test_agentic_nodes.py tests/test_evidence_graph_node.py
```

- [ ] **Step 6: Final commit (if any fixes needed)**

```bash
git add -A && git commit -m "chore: final verification and fixes" || echo "No changes needed"
```

- [ ] **Step 7: Update anchored summary**

Log the completion status for the anchored summary.
