"""Planner Node for LangGraph integration.

Wraps PlannerAgent for use in the Agentic RAG pipeline.
Consumes AgentState, generates a Plan, and updates state.
"""

import logging

from src.agents.planner.planner import PlannerAgent
from src.graph.state import AgentState
from src.llm.router import ModelRouter

logger = logging.getLogger(__name__)


class PlannerNode:
    """LangGraph node that generates execution plans.

    Phase 0: Generates plan and populates state fields.
    Phase 1: Will be wired into build_agentic_graph().
    """

    def __init__(self, router: ModelRouter):
        self.router = router

    async def __call__(self, state: AgentState) -> AgentState:
        """Generate a plan and update state.

        Args:
            state: Current AgentState with user_message and optional learner_snapshot.

        Returns:
            Updated AgentState with execution_plan, subtasks, and complexity_score.
        """
        agent = PlannerAgent(self.router)

        # Use learner_snapshot if available, otherwise None
        snapshot = state.learner_snapshot if state.learner_snapshot else None

        plan = await agent.generate_plan(
            user_query=state.user_message,
            learner_snapshot=snapshot,
        )

        # Update state with plan
        state.execution_plan = plan.model_dump()
        state.subtasks = [s.model_dump() for s in plan.subtasks]
        state.complexity_score = plan.complexity_score

        logger.info(
            "plan_generated",
            objective=plan.objective,
            complexity=plan.complexity_score,
            subtask_count=len(plan.subtasks),
        )

        return state
