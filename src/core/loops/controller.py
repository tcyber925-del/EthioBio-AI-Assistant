"""Iterative retrieval loop controller.

Evaluates 3 stopping criteria and returns a LoopDecision."""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

NO_PROGRESS_THRESHOLD = 0.02
NO_PROGRESS_CONSECUTIVE = 2


@dataclass
class LoopDecision:
    should_continue: bool
    reason: str  # CONTINUE | MAX_ITERATIONS | NO_PROGRESS | NO_NEW_EVIDENCE


class RetrievalLoopController:
    """Decides whether the retrieval loop should continue or stop.

    Stateless — all state comes from the AgentState (or duck-typed equivalent).
    Order of checks:
    1. Max iterations — hard cap
    2. No progress — coverage gain < threshold for N consecutive iterations
    3. No new evidence — evidence count unchanged from previous pass
    """

    def decide(self, state) -> LoopDecision:
        iterations = state.retrieval_iterations
        max_iter = state.max_iterations

        # 1. Max iterations
        if iterations >= max_iter:
            logger.info("loop_stop: max_iterations", current=iterations, max=max_iter)
            return LoopDecision(should_continue=False, reason="MAX_ITERATIONS")

        # 2. No progress (requires at least NO_PROGRESS_CONSECUTIVE history entries)
        if len(state.coverage_history) >= NO_PROGRESS_CONSECUTIVE:
            all_values: list[float] = list(state.coverage_history) + [state.coverage_score]
            all_gains = [all_values[i + 1] - all_values[i] for i in range(len(all_values) - 1)]
            recent_gains = all_gains[-NO_PROGRESS_CONSECUTIVE:]
            if all(g < NO_PROGRESS_THRESHOLD for g in recent_gains):
                logger.info(
                    "loop_stop: no_progress",
                    gains=[round(g, 4) for g in recent_gains],
                )
                return LoopDecision(should_continue=False, reason="NO_PROGRESS")

        # 3. No new evidence (only after first iteration)
        if iterations > 0 and len(state.evidence_ids) <= state.previous_evidence_count:
            logger.info(
                "loop_stop: no_new_evidence",
                previous=state.previous_evidence_count,
                current=len(state.evidence_ids),
            )
            return LoopDecision(should_continue=False, reason="NO_NEW_EVIDENCE")

        return LoopDecision(should_continue=True, reason="CONTINUE")
