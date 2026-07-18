"""Safety node — runs self-check on generated content."""

import asyncio
import json
import re

from src.graph.state import AgentState
from src.llm.router import ModelRouter

SAFETY_PROMPT_EN = """You are EthioBio Safety Agent. Review the following biology content for:
1. Factual accuracy (check names, processes, numbers)
2. Grade-appropriateness
3. Safety (no harmful content)
4. Curriculum alignment
5. Clarity
6. Language quality (proper {language})

Respond with ONLY a JSON object:
{{"safe": true/false, "issues": ["issue1"], "score": 0.0-1.0, "suggestions": ["suggestion"]}}"""

SAFETY_PROMPT_AM = """እርስዎ የEthioBio ደህንነት ተቆጣጣሪ ነዎት። የሚከተለውን የባዮሎጂ ይዘት ይገምግሙ፡
1. ትክክለኛነት (ስሞች፣ ሂደቶች፣ ቁጥሮች)
2. የክፍል ደረጃ ተገቢነት
3. ደህንነት (ምንም ጎጂ ይዘት የለም)
4. ከሥርዓተ ትምህርት ጋር መጣጣም
5. ግልጽነት
6. የቋንቋ ጥራት (ትክክለኛ {language})

በJSON ብቻ ይመልሱ፦
{{"safe": true/false, "issues": ["issue1"], "score": 0.0-1.0, "suggestions": ["suggestion"]}}"""

MAX_RETRIES = 2
RETRY_DELAY = 0.5

# Citation pattern: (Grade X, Unit Y: Title, Section N.N: Name, p. Z)
CITATION_RE = re.compile(
    r"\(Grade\s+(\d+).*?Unit\s+(\d+).*?(?:Section\s+([\d.]+))?.*?p\.?\s*(\d+)\)",
    re.IGNORECASE,
)

# Quote extraction pattern: "quoted text" (min 10 chars)
QUOTE_RE = re.compile(r'"([^"]{10,})"')


def _normalize(text: str) -> str:
    """Normalize whitespace and case for quote matching."""
    return " ".join(text.lower().replace("\n", " ").split())


def _collect_source_text(state: AgentState) -> str:
    """Concatenate all available source text for quote verification."""
    parts = []
    if state.context:
        parts.append(state.context)
    if state.retrieved_chunks:
        for chunk in state.retrieved_chunks:
            content = chunk.get("content", "")
            if content:
                parts.append(content)
    if state.evidence_synthesis:
        parts.append(state.evidence_synthesis)
    return "\n".join(parts)


def _verify_citations(text: str, grade_level: int | None = None) -> list[str]:
    """Verify that citations in the response are plausible. Returns list of issues found."""
    issues = []
    citations = CITATION_RE.findall(text)
    for cited_grade, cited_unit, cited_section, cited_page in citations:
        cited_grade_num = int(cited_grade)
        if cited_grade_num < 7 or cited_grade_num > 12:
            issues.append(f"Hallucinated citation: Grade {cited_grade_num} is outside 7-12 range")
        if grade_level and cited_grade_num != grade_level:
            issues.append(
                f"Citation grade mismatch: response cites Grade {cited_grade_num}"
                f" but student is Grade {grade_level}"
            )
        unit_num = int(cited_unit)
        if unit_num < 1 or unit_num > 20:
            issues.append(f"Suspicious unit number in citation: Unit {cited_unit}")
        if cited_section:
            parts = cited_section.split(".")
            if len(parts) >= 2:
                section_unit = parts[0]
                if section_unit != cited_unit:
                    issues.append(f"Section {cited_section} does not belong to Unit {cited_unit}")
    return issues


def _verify_verbatim_quotes(response: str, state: AgentState) -> list[str]:
    """Extract quoted text from response and verify verbatim match in source chunks.

    Normalizes whitespace and case before comparing.
    Returns list of issues for quotes not found in any source text.
    """
    source_text = _collect_source_text(state)
    if not source_text:
        return []

    normalized_sources = _normalize(source_text)
    quotes = QUOTE_RE.findall(response)
    issues = []
    for q in quotes:
        if _normalize(q) not in normalized_sources:
            truncated = q[:100] + "..." if len(q) > 100 else q
            issues.append(f'Quote not found in curriculum: "{truncated}"')
    return issues


class SafetyNode:
    def __init__(self, router: ModelRouter):
        self.router = router

    async def __call__(self, state: AgentState) -> AgentState:
        grade_context = f" (Grade {state.grade_level})" if state.grade_level else ""
        lang_names = {"en": "English", "am": "አማርኛ", "both": "English/አማርኛ"}
        lang_name = lang_names.get(state.language, "English")

        prompt_template = SAFETY_PROMPT_EN if state.language == "en" else SAFETY_PROMPT_AM
        safety_prompt = prompt_template.format(language=lang_name)

        messages = [
            {"role": "system", "content": safety_prompt},
            {
                "role": "user",
                "content": f"Review this biology content{grade_context}:\n\n{state.draft}",
            },
        ]

        for attempt in range(MAX_RETRIES + 1):
            try:
                result = await self.router.route(
                    messages, request_type="safety_check", temperature=0.1, max_tokens=500
                )

                content = result["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                parsed = json.loads(content)
                state.safe = parsed.get("safe", True)
                state.safety_issues = parsed.get("issues", [])
                state.safety_score = parsed.get("score", 1.0)
                break
            except (json.JSONDecodeError, KeyError):
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    state.safe = False
                    state.safety_issues = ["Safety check failed after retries"]
                    state.safety_score = 0.0

        # Citation verification — catch hallucinated textbook references
        citation_issues = _verify_citations(state.draft, state.grade_level)
        if citation_issues:
            state.safety_issues.extend(citation_issues)
            state.safety_score = max(0.0, state.safety_score - 0.15 * len(citation_issues))
            if state.safety_score < 0.6:
                state.safe = False

        # Verbatim quote verification — catch fabricated quotes
        quote_issues = _verify_verbatim_quotes(state.draft, state)
        if quote_issues:
            state.safety_issues.extend(quote_issues)
            state.safety_score = max(0.0, state.safety_score - 0.2 * len(quote_issues))
            if state.safety_score < 0.6:
                state.safe = False

        if not state.safe or state.safety_score < 0.6:
            state.safety_revision_count += 1
            state.requires_teacher_review = True
            state.status = "needs_review"
        else:
            state.status = "approved"

        return state


def should_revise(state: AgentState) -> str:
    if not state.safe and state.safety_score < 0.4:
        return "reject"
    if not state.safe or state.safety_score < 0.7:
        if state.safety_revision_count < 2:
            return "revise"
        return "reject"
    return "finalize"
