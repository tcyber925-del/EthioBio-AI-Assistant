"""Sufficient Context Node for Agentic RAG.

Evaluates whether the collected evidence is sufficient to answer the user's question.
Returns SUFFICIENT or INSUFFICIENT with missing information details.

Termination decisions are delegated to RetrievalLoopController.
Gap-to-directive conversion is delegated to FeedbackProcessor.
Telemetry is emitted via record_loop_decision.
"""

import logging
from dataclasses import dataclass

from src.core.loops import FeedbackProcessor, RetrievalLoopController, record_loop_decision
from src.graph.state import AgentState

logger = logging.getLogger(__name__)

# Thresholds for sufficiency evaluation
SUFFICIENCY_THRESHOLD = 0.7
MIN_EVIDENCE_COUNT = 2
REPLAN_EVIDENCE_THRESHOLD = 0.5
REPLAN_MISSING_THRESHOLD = 2



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

    Computes a combined score from evidence count and coverage,
    then classifies as sufficient, minor_gap, or major_gap.

    Termination decisions (max iterations, no progress, no new evidence)
    are handled by RetrievalLoopController, not here.
    """
    evidence_count = len(state.evidence_ids)
    coverage_score = state.coverage_score

    evidence_score = min(1.0, evidence_count / MIN_EVIDENCE_COUNT)
    base_score = (evidence_score + coverage_score) / 2

    missing = state.missing_information
    missing_penalty = len(missing) * 0.15
    final_score = max(0.0, base_score - missing_penalty)

    if final_score >= SUFFICIENCY_THRESHOLD and not missing:
        action = "sufficient"
        reason = (
            f"Sufficient evidence: {evidence_count} records, "
            f"coverage={coverage_score:.2f}"
        )
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

    Delegates termination logic to RetrievalLoopController and
    gap-to-directive conversion to FeedbackProcessor.
    """

    def __init__(self) -> None:
        self.controller = RetrievalLoopController()
        self.feedback_processor = FeedbackProcessor()

    async def __call__(self, state: AgentState) -> AgentState:
        """Evaluate sufficiency and update state.

        Delegates termination logic to RetrievalLoopController and
        gap-to-directive conversion to FeedbackProcessor.

        Args:
            state: AgentState with evidence_ids and coverage_score.

        Returns:
            Updated AgentState with sufficiency_score, sufficiency_reason,
            missing_information, and requires_iteration.
        """
        state.previous_evidence_count = len(state.evidence_ids)

        result = evaluate_sufficiency(state)

        state.sufficiency_score = result.score
        state.sufficiency_reason = result.reason
        state.missing_information = result.missing_information

        # Append coverage to history before controller runs
        state.coverage_history.append(state.coverage_score)

        # Generate retrieval feedback for next iteration
        state.retrieval_feedback = self.feedback_processor.process(
            missing_information=state.missing_information,
            coverage_score=state.coverage_score,
        )

        # Let controller decide: should we continue?
        decision = self.controller.decide(state)
        state.requires_iteration = decision.should_continue
        state.termination_reason = decision.reason

        state.retrieval_iterations += 1

        # Emit telemetry
        record_loop_decision(state)

        logger.info(
            "sufficiency_evaluated score=%s action=%s iterations=%s termination=%s evidence_count=%s",
            round(result.score, 2),
            result.action,
            state.retrieval_iterations,
            state.termination_reason,
            len(state.evidence_ids),
        )

        return state


def route_after_sufficiency(state: AgentState) -> str:
    """Route after sufficiency evaluation.

    Priority:
    1. Controller says STOP (max iterations, no progress, no new evidence) → synthesis
    2. Sufficiency score >= threshold → synthesis (evidence is good enough)
    3. Minor gap → rewrite (back to plan_executor)
    4. Major gap → replan (back to planner)

    Returns:
        "synthesis" if stopped or sufficient,
        "rewrite" for minor gaps,
        "replan" for major gaps.
    """
    if not state.requires_iteration:
        return "synthesis"

    if state.sufficiency_score >= SUFFICIENCY_THRESHOLD:
        return "synthesis"

    if len(state.missing_information) < REPLAN_MISSING_THRESHOLD:
        return "rewrite"

    return "replan"
