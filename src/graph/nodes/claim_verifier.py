"""Claim Verifier Node for Agentic RAG.

Extracts factual claims from tutor's response and verifies them against evidence.
Routes to revise/reject/finalize based on groundedness score.
"""

import logging
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


@dataclass
class Claim:
    """Represents a factual claim from the response."""

    text: str
    claim_type: str  # "definition", "process", "fact", "comparison"
    is_grounded: bool
    evidence_id: str | None = None
    confidence: float = 0.0


def extract_claims_simple(response: str) -> list[Claim]:
    """Extract claims from response using simple heuristics.

    Phase 1+: Use LLM for claim extraction.
    """
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


def verify_claims_against_evidence(claims: list[Claim], evidence_ids: list[str]) -> list[Claim]:
    """Verify claims against evidence IDs.

    Phase 1+: Use semantic similarity for verification.
    """
    if not evidence_ids:
        return claims

    verified_count = 0
    for claim in claims:
        if evidence_ids:
            claim.is_grounded = True
            claim.evidence_id = evidence_ids[0]
            claim.confidence = 0.8
            verified_count += 1

    logger.info("claims_verified", total=len(claims), grounded=verified_count)
    return claims


def calculate_groundedness(claims: list[Claim]) -> float:
    """Calculate overall groundedness score."""
    if not claims:
        return 0.0

    grounded = sum(1 for c in claims if c.is_grounded)
    return grounded / len(claims)


class ClaimVerifierNode:
    """Verifies claims in the tutor's draft response against evidence.

    Phase 0: Always finalize.
    Phase 1: Extract claims, verify against evidence, route based on groundedness.
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

        # Extract claims
        claims = extract_claims_simple(draft)

        # Verify against evidence
        verified_claims = verify_claims_against_evidence(claims, state.evidence_ids)

        # Calculate groundedness
        groundedness = calculate_groundedness(verified_claims)
        state.groundedness_score = groundedness

        # Store verification details
        ungrounded = [c.text for c in verified_claims if not c.is_grounded]
        state.ungrounded_claims = ungrounded

        # Determine action
        if len(verified_claims) < VERIFICATION_THRESHOLDS["minimum_claims"]:
            state.safety_action = "revise"
            state.safety_reason = f"Insufficient claims extracted: {len(verified_claims)}"
        elif groundedness >= VERIFICATION_THRESHOLDS["partial_threshold"]:
            state.safety_action = "finalize"
            state.safety_reason = f"Claims sufficiently grounded: {groundedness:.2f}"
        elif groundedness >= VERIFICATION_THRESHOLDS["ungrounded_threshold"]:
            state.safety_action = "revise"
            state.safety_reason = f"Claims partially grounded: {groundedness:.2f}"
        else:
            state.safety_action = "reject"
            state.safety_reason = f"Claims poorly grounded: {groundedness:.2f}"

        logger.info(
            "claim_verification_complete",
            total_claims=len(verified_claims),
            groundedness=groundedness,
            action=state.safety_action,
        )

        return state


def route_after_verification(state: AgentState) -> str:
    """Route after claim verification based on safety_action."""
    return state.safety_action or "finalize"
