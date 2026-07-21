"""Claim Verifier Node for Agentic RAG.

Extracts factual claims from tutor's response and verifies them against evidence.
Routes to revise/reject/finalize based on groundedness score.
"""

import json
import logging
import re
from dataclasses import dataclass

from src.graph.state import AgentState
from src.llm.router import ModelRouter

logger = logging.getLogger(__name__)

VERIFICATION_THRESHOLDS = {
    "minimum_claims": 1,
    "minimum_evidence": 1,
    "ungrounded_threshold": 0.3,
    "partial_threshold": 0.6,
}

MAX_REVISIONS = 2

QUOTE_RE = re.compile(r'"([^"]{10,})"')
CITATION_ID_RE = re.compile(r"\[id:([^\]]+)\]")


@dataclass
class Claim:
    """Represents a factual claim from the response."""

    text: str
    claim_type: str  # "definition", "process", "fact", "comparison"
    is_grounded: bool
    evidence_id: str | None = None
    confidence: float = 0.0


def _normalize(text: str) -> str:
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


def extract_claims_simple(response: str) -> list[Claim]:
    """Extract claims from response using simple heuristics."""
    claims = []

    # Simple claim extraction based on sentence structure
    sentences = [s.strip() for s in response.split(".") if len(s.strip()) > 20]

    for sentence in sentences[:10]:
        claim_type = "fact"
        if any(word in sentence.lower() for word in ["is", "are", "means"]):
            claim_type = "definition"
        elif any(word in sentence.lower() for word in ["process", "step", "first", "then"]):
            claim_type = "process"
        elif any(word in sentence.lower() for word in ["than", "more", "less", "compare"]):
            claim_type = "comparison"

        claims.append(
            Claim(
                text=sentence.strip(),
                claim_type=claim_type,
                is_grounded=False,
                evidence_id=None,
                confidence=0.5,
            )
        )

    return claims


def verify_claims_against_evidence(
    claims: list[Claim],
    evidence_ids: list[str],
    source_text: str,
) -> list[Claim]:
    """Verify claims against evidence using verbatim quotes and citation IDs.

    A claim is grounded if:
    1. It contains a verbatim quote found in the source text, OR
    2. It contains a [id:...] citation whose ID exists in evidence_ids
    """
    if not evidence_ids and not source_text:
        return claims

    normalized_sources = _normalize(source_text) if source_text else ""

    verified_count = 0
    for claim in claims:
        grounded = False
        found_id = None

        # Check 1: verbatim quote in source text
        quotes = QUOTE_RE.findall(claim.text)
        for q in quotes:
            if _normalize(q) in normalized_sources:
                grounded = True
                break

        # Check 2: citation ID in evidence_ids
        if not grounded:
            cited_ids = CITATION_ID_RE.findall(claim.text)
            for cid in cited_ids:
                if cid in evidence_ids:
                    grounded = True
                    found_id = cid
                    break

        if grounded:
            claim.is_grounded = True
            claim.evidence_id = found_id or (evidence_ids[0] if evidence_ids else None)
            claim.confidence = 0.85
            verified_count += 1

    logger.info("claims_verified", total=len(claims), grounded=verified_count)
    return claims


def calculate_groundedness(claims: list[Claim]) -> float:
    """Calculate overall groundedness score."""
    if not claims:
        return 0.0

    grounded = sum(1 for c in claims if c.is_grounded)
    return grounded / len(claims)


LLM_VERIFY_PROMPT = (
    "You are a strict but fair biology fact-checker. Given the student's "
    "question, the tutor's draft answer, and the retrieved evidence, determine "
    "whether each claim in the answer is supported.\n\n"
    "Return a JSON object:\n"
    '{{"verdict": "supported"/"partial"/"unsupported", '
    '"ungrounded_claims": ["claim text"], '
    '"groundedness_score": 0.0-1.0, '
    '"reason": "brief explanation"}}\n\n'
    "Base your judgment only on the provided evidence. "
    'Claims not found in evidence are "unsupported".'
)


async def _llm_verify(
    router: ModelRouter,
    question: str,
    draft: str,
    source_text: str,
) -> dict:
    """Use LLM to verify draft claims against source text."""
    messages = [
        {"role": "system", "content": LLM_VERIFY_PROMPT},
        {
            "role": "user",
            "content": (
                f"Student question: {question}\n\n"
                f"Tutor draft: {draft}\n\n"
                f"Retrieved evidence:\n{source_text[:8000]}"
            ),
        },
    ]
    try:
        result = await router.route(
            messages, request_type="claim_verify", temperature=0.1, max_tokens=500
        )
        content = result["content"]
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)
    except (json.JSONDecodeError, KeyError, Exception) as e:
        logger.warning("llm_verify_failed", error=str(e))
        return {
            "verdict": "unknown",
            "ungrounded_claims": [],
            "groundedness_score": 0.5,
            "reason": "LLM verification failed",
        }


class ClaimVerifierNode:
    """Verifies claims in the tutor's draft response against evidence.

    Uses LLM-based verification when available, falls back to heuristic-based
    verification (verbatim quotes + citation IDs).
    """

    def __init__(self, router: ModelRouter):
        self.router = router

    async def __call__(self, state: AgentState) -> AgentState:
        """Verify claims in the draft response.

        Args:
            state: AgentState with draft response and evidence_ids.

        Returns:
            Updated AgentState with verification results and safety_action.
        """
        draft = state.draft

        if not draft:
            state.safety_action = "finalize"
            state.safety_reason = "No draft to verify"
            return state

        # Collect source text for quote verification
        source_text = _collect_source_text(state)

        # LLM-based verification (primary path)
        llm_result = await _llm_verify(self.router, state.user_message, draft, source_text)

        llm_groundedness = llm_result.get("groundedness_score", 0.5)
        llm_ungrounded = llm_result.get("ungrounded_claims", [])

        # Fall back to heuristic verification if LLM result is uncertain
        if llm_result.get("verdict") == "unknown" or llm_groundedness == 0.5:
            claims = extract_claims_simple(draft)
            verified = verify_claims_against_evidence(claims, state.evidence_ids, source_text)
            groundedness = calculate_groundedness(verified)
            ungrounded = [c.text for c in verified if not c.is_grounded]
        else:
            groundedness = llm_groundedness
            ungrounded = llm_ungrounded

        state.groundedness_score = groundedness
        state.ungrounded_claims = ungrounded

        # Determine action
        if groundedness >= VERIFICATION_THRESHOLDS["partial_threshold"]:
            state.safety_action = "finalize"
            state.safety_reason = f"Claims sufficiently grounded: {groundedness:.2f}"
        elif groundedness >= VERIFICATION_THRESHOLDS["ungrounded_threshold"]:
            if state.revision_count < MAX_REVISIONS:
                state.safety_action = "revise"
                state.revision_count += 1
            else:
                state.safety_action = "finalize"
            state.safety_reason = f"Claims partially grounded: {groundedness:.2f}"
        else:
            state.safety_action = "reject"
            state.safety_reason = f"Claims poorly grounded: {groundedness:.2f}"

        logger.info(
            "claim_verification_complete",
            total_claims=max(len(ungrounded) + 1, 1),
            groundedness=groundedness,
            action=state.safety_action,
        )

        return state


def route_after_verification(state: AgentState) -> str:
    """Route after claim verification based on safety_action."""
    return state.safety_action or "finalize"
