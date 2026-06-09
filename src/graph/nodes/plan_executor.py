"""Plan Executor node for Agentic RAG.

Executes a Plan's subtasks sequentially, running Rewriter -> Fanout -> Retrievers
per subtask. Manages the loop until all subtasks complete.

Phase 0: Skeleton — runs subtasks but uses simplified retrieval.
"""

import logging

from src.graph.nodes.search_fanout import SearchFanoutNode
from src.graph.state import AgentState
from src.retrieval.adapter import VectorStoreAdapter

logger = logging.getLogger(__name__)


class PlanExecutor:
    """Executes a Plan's subtasks sequentially.

    Each subtask goes through:
    1. Query rewriting (simplified in Phase 0)
    2. Retrieval (via existing RetrievalNode logic)
    3. Evidence collection

    Subtasks run sequentially so later subtasks can benefit from
    earlier evidence. Retrieval within a subtask can be parallelized.
    """

    def __init__(self, adapter: VectorStoreAdapter):
        """Initialize with a VectorStoreAdapter for retrieval.

        Args:
            adapter: VectorStoreAdapter instance for curriculum retrieval.
        """
        self.adapter = adapter
        self.search_fanout = SearchFanoutNode(adapter)

    async def execute_plan(self, state: AgentState) -> AgentState:
        """Execute all subtasks in the plan sequentially.

        Args:
            state: AgentState with execution_plan and subtasks populated.

        Returns:
            Updated AgentState with evidence_ids, coverage_score, etc.
        """
        subtasks = state.subtasks
        if not subtasks:
            logger.warning("no_subtasks_to_execute")
            return state

        logger.info("plan_execution_start", subtask_count=len(subtasks))

        for i, subtask in enumerate(subtasks):
            subtask_id = subtask.get("id", f"task_{i + 1}")
            subtask_type = subtask.get("type", "curriculum")
            objective = subtask.get("objective", "")

            logger.info(
                "subtask_execution_start",
                subtask_id=subtask_id,
                type=subtask_type,
                objective=objective[:100],
            )

            # Phase 0: Simplified retrieval per subtask
            # In Phase 1+, this will use QueryRewriter + Fanout + EvidenceGraph
            await self._execute_subtask(state, subtask, i)

            logger.info("subtask_execution_complete", subtask_id=subtask_id)

        # Phase 0: Set coverage based on evidence collected
        state.coverage_score = min(1.0, len(state.evidence_ids) * 0.2)
        state.evidence_summary = f"Collected {len(state.evidence_ids)} evidence records"

        logger.info(
            "plan_execution_complete",
            evidence_count=len(state.evidence_ids),
            coverage=state.coverage_score,
        )

        return state

    async def _execute_subtask(
        self,
        state: AgentState,
        subtask: dict,
        index: int,
    ) -> None:
        """Execute a single subtask using SearchFanout for parallel retrieval.

        Phase 0: Uses simplified retrieval directly from the adapter.
        Phase 1: Delegates to SearchFanout for parallel multi-index retrieval.
        """
        objective = subtask.get("objective", state.user_message)
        query = objective if objective else state.user_message

        # On re-entry (iteration > 0), append retrieval feedback directives
        # to make the search more targeted toward identified gaps
        if state.retrieval_iterations > 0 and state.retrieval_feedback:
            feedback_prefix = "; ".join(state.retrieval_feedback[:2])
            query = f"{query} — {feedback_prefix}"

        # Use SearchFanout for parallel retrieval across multiple indices
        state.retrieval_queries = [query]
        state.retrieval_indices = ["curriculum"]  # Expand based on subtask type

        try:
            await self.search_fanout(state)
        except Exception as e:
            logger.warning("subtask_retrieval_failed: %s", str(e))


def route_after_plan_execution(state: AgentState) -> str:
    """Route after plan execution based on evidence collection.

    Returns:
        "context_check" if evidence was collected, "finalize" otherwise.
    """
    if state.evidence_ids:
        return "context_check"
    return "finalize"
