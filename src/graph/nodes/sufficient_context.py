"""Sufficient Context Node for Agentic RAG.

Evaluates whether the collected evidence is sufficient to answer the user's question.
Returns SUFFICIENT or INSUFFICIENT with missing information details.

Implements 3-layer stopping mechanism per ADR-0004:
1. Hard cap: max iterations
2. Diminishing returns: no new evidence in last pass
3. Sufficient context: coverage threshold met

Phase 0: Simplified evaluation based on evidence count and coverage.
"""

import logging
from dataclasses import dataclass

from src.graph.state import AgentState

logger = logging.getLogger(__name__)

# Thresholds for sufficiency evaluation
SUFFICIENCY_THRESHOLD = 0.7
MIN_EVIDENCE_COUNT = 2
REPLAN_EVIDENCE_THRESHOLD = 0.5
REPLAN_MISSING_THRESHOLD = 2

# Iterative retrieval stopping criteria
MAX_ITERATIONS = 2
DIMINISHING_RETURNS_THRESHOLD = 0  # No new evidence = stop


@dataclass
class SufficiencyResult:
    """Result of context sufficiency evaluation."""

    is_sufficient: bool
    score: float  # 0.0 to 1.0
    missing_information: list[str]
    reason: str
    action: str  # "sufficient", "minor_gap", "major_gap"


def evaluate_sufficiency(state: AgentState) -> SufficiencyResult:
    """Evaluate whether evidence is sufficient to answer the question.

    Applies 3-layer stopping mechanism:
    1. Hard cap: retrieval_iterations >= MAX_ITERATIONS
    2. Diminishing returns: evidence_ids count unchanged from last pass
    3. Sufficient context: coverage threshold met

    Args:
        state: AgentState with evidence_ids, coverage_score, and missing_information.

    Returns:
        SufficiencyResult with sufficiency assessment and recommended action.
    """
    evidence_count = len(state.evidence_ids)
    coverage_score = state.coverage_score
    iterations = state.retrieval_iterations
    previous_count = state.previous_evidence_count

    # Layer 1: Hard cap — max iterations reached
    if iterations >= MAX_ITERATIONS:
        if evidence_count > 0:
            return SufficiencyResult(
                is_sufficient=True,
                score=coverage_score,
                missing_information=state.missing_information,
                reason=(
                    f"Max iterations ({MAX_ITERATIONS}) reached with "
                    f"{evidence_count} evidence records"
                ),
                action="sufficient",
            )
        return SufficiencyResult(
            is_sufficient=False,
            score=0.0,
            missing_information=state.missing_information or ["No evidence after max iterations"],
            reason=f"Max iterations ({MAX_ITERATIONS}) reached with no evidence",
            action="major_gap",
        )

    # Layer 2: Diminishing returns — no new evidence collected
    if iterations > 0 and evidence_count <= previous_count + DIMINISHING_RETURNS_THRESHOLD:
        if evidence_count > 0:
            return SufficiencyResult(
                is_sufficient=True,
                score=coverage_score,
                missing_information=state.missing_information,
                reason=f"Diminishing returns: no new evidence in iteration {iterations}",
                action="sufficient",
            )
        return SufficiencyResult(
            is_sufficient=False,
            score=0.0,
            missing_information=state.missing_information or ["No evidence collected"],
            reason="No evidence collected",
            action="major_gap",
        )

    # Layer 3: Sufficient context evaluation
    evidence_score = min(1.0, evidence_count / MIN_EVIDENCE_COUNT)
    base_score = (evidence_score + coverage_score) / 2

    missing = state.missing_information
    missing_penalty = len(missing) * 0.15
    final_score = max(0.0, base_score - missing_penalty)

    # Determine action
    if final_score >= SUFFICIENCY_THRESHOLD and not missing:
        action = "sufficient"
        reason = f"Sufficient evidence: {evidence_count} records, coverage={coverage_score:.2f}"
    elif final_score >= REPLAN_EVIDENCE_THRESHOLD and len(missing) < REPLAN_MISSING_THRESHOLD:
        action = "minor_gap"
        reason = f"Minor gap: missing {', '.join(missing[:2])}"
    else:
        action = "major_gap"
        reason = f"Major gap: {len(missing)} missing areas, score={final_score:.2f}"

    return SufficiencyResult(
        is_sufficient=action == "sufficient",
        score=final_score,
        missing_information=missing,
        reason=reason,
        action=action,
    )


class SufficientContextNode:
    """Evaluates context sufficiency in the Agentic RAG pipeline.

    Implements 3-layer stopping mechanism:
    1. Hard iteration cap (MAX_ITERATIONS)
    2. Diminishing returns detection
    3. Sufficient context termination signal

    Phase 0: Simplified evaluation.
    Phase 1+: LLM-based evaluation with detailed gap analysis.
    """

    async def __call__(self, state: AgentState) -> AgentState:
        """Evaluate sufficiency and update state.

        Also tracks previous evidence count for diminishing returns detection
        and increments retrieval_iterations for the hard cap.

        Args:
            state: AgentState with evidence_ids and coverage_score.

        Returns:
            Updated AgentState with sufficiency_score, sufficiency_reason,
            missing_information, and requires_iteration.
        """
        # Store previous evidence count before evaluation
        state.previous_evidence_count = len(state.evidence_ids)

        result = evaluate_sufficiency(state)

        state.sufficiency_score = result.score
        state.sufficiency_reason = result.reason
        state.missing_information = result.missing_information

        # Layer 1: Hard cap hit — stop iterating
        if state.retrieval_iterations >= MAX_ITERATIONS:
            state.requires_iteration = False
        else:
            state.requires_iteration = result.action != "sufficient"

        # Increment iteration counter for next pass
        state.retrieval_iterations += 1

        logger.info(
            "sufficiency_evaluated",
            score=result.score,
            action=result.action,
            iterations=state.retrieval_iterations,
            missing_count=len(result.missing_information),
            evidence_count=len(state.evidence_ids),
        )

        return state


def route_after_sufficiency(state: AgentState) -> str:
    """Route after sufficiency evaluation.

    Considers all 3 stopping layers:
    - Hard cap hit or sufficient context -> tutor
    - Minor gap -> rewrite
    - Major gap -> replan

    Returns:
        "tutor" if sufficient, "rewrite" for minor gaps, "replan" for major gaps.
    """
    # Hard cap or diminishing returns: route to tutor
    if not state.requires_iteration:
        return "tutor"

    if len(state.missing_information) < REPLAN_MISSING_THRESHOLD:
        return "rewrite"

    return "replan"
