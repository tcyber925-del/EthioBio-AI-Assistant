"""Planner Agent for Agentic RAG.

Transforms user questions into structured execution plans.
Extends BaseAgent to use the existing LLM routing infrastructure.
"""

import json
import logging

from src.agents.base import BaseAgent
from src.agents.planner.models import Plan, ReasoningType, SubTask
from src.agents.planner.prompts import PLANNER_SYSTEM_PROMPT, build_planner_prompt

logger = logging.getLogger(__name__)

# Fallback plan when LLM fails
FALLBACK_PLAN = Plan(
    objective="Fallback: single curriculum retrieval",
    complexity_score=0.2,
    retrieval_domains=["curriculum"],
    subtasks=[
        SubTask(
            id="task_1",
            type="curriculum",
            objective="Retrieve general curriculum content",
            retrieval_sources=["curriculum"],
            priority=1,
            expected_output="General curriculum content",
        )
    ],
    reasoning_type=ReasoningType.FACT_LOOKUP,
    estimated_iterations=1,
)


class PlannerAgent(BaseAgent):
    """Planner Agent that generates structured execution plans.

    Phase 0: Generates plans from user queries using LLM.
    Consumed by PlannerNode in the Agentic RAG pipeline.
    """

    def __init__(self, llm_router):
        super().__init__(llm_router, name="planner")

    async def generate_plan(
        self,
        user_query: str,
        learner_snapshot: dict | None = None,
    ) -> Plan:
        """Generate a structured execution plan for the user query.

        Args:
            user_query: The user's question or request.
            learner_snapshot: Optional learner snapshot for personalization.

        Returns:
            Plan with subtasks, complexity, and reasoning type.
        """
        user_prompt = build_planner_prompt(user_query, learner_snapshot)

        try:
            result = await self._call_llm(
                system_prompt=PLANNER_SYSTEM_PROMPT,
                user_message=user_prompt,
                temperature=0.3,
                max_tokens=1024,
                request_type="planning",
            )

            content = result["content"]
            plan = self._parse_plan(content)
            return plan

        except Exception as e:
            logger.warning("planner_generation_failed: %s", str(e))
            return FALLBACK_PLAN

    def _parse_plan(self, content: str) -> Plan:
        """Parse LLM response into a Plan object.

        Handles common LLM output patterns (markdown code blocks, etc.).
        """
        # Try to extract JSON from code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        parsed = json.loads(content)

        # Parse subtasks
        subtasks = []
        for st in parsed.get("subtasks", []):
            subtasks.append(
                SubTask(
                    id=st.get("id", f"task_{len(subtasks) + 1}"),
                    type=st.get("type", "curriculum"),
                    objective=st.get("objective", ""),
                    retrieval_sources=st.get("retrieval_sources", []),
                    priority=st.get("priority", len(subtasks) + 1),
                    expected_output=st.get("expected_output", ""),
                )
            )

        # Parse reasoning type
        reasoning_str = parsed.get("reasoning_type", "explanation")
        try:
            reasoning_type = ReasoningType(reasoning_str)
        except ValueError:
            reasoning_type = ReasoningType.EXPLANATION

        return Plan(
            objective=parsed.get("objective", ""),
            complexity_score=float(parsed.get("complexity_score", 0.5)),
            retrieval_domains=parsed.get("retrieval_domains", []),
            subtasks=subtasks,
            reasoning_type=reasoning_type,
            estimated_iterations=int(parsed.get("estimated_iterations", 1)),
        )
