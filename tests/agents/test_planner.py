"""Tests for the Planner Agent.

Tests Plan and SubTask models, PlannerAgent generation, and PlannerNode integration.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.planner.models import ComplexityLevel, Plan, ReasoningType, SubTask
from src.agents.planner.planner import FALLBACK_PLAN, PlannerAgent
from src.agents.planner.prompts import build_planner_prompt
from src.graph.nodes.planner import PlannerNode
from src.graph.state import AgentState

# ============================================================
# Model Tests
# ============================================================


class TestPlanModel:
    def test_plan_has_required_fields(self):
        plan = Plan(
            objective="Test plan",
            complexity_score=0.5,
            retrieval_domains=["curriculum"],
            subtasks=[],
            reasoning_type=ReasoningType.EXPLANATION,
            estimated_iterations=1,
        )
        assert plan.objective == "Test plan"
        assert plan.complexity_score == 0.5
        assert plan.retrieval_domains == ["curriculum"]
        assert plan.subtasks == []
        assert plan.reasoning_type == ReasoningType.EXPLANATION

    def test_plan_defaults(self):
        plan = Plan(objective="Test")
        assert plan.complexity_score == 0.5
        assert plan.retrieval_domains == []
        assert plan.subtasks == []
        assert plan.estimated_iterations == 1

    def test_plan_validates_complexity_range(self):
        with pytest.raises(Exception):
            Plan(objective="Test", complexity_score=1.5)  # Exceeds 1.0

    def test_plan_serialization(self):
        plan = Plan(
            objective="Test",
            subtasks=[SubTask(id="t1", type="curriculum", objective="Retrieve mitosis")],
        )
        dumped = plan.model_dump()
        assert dumped["objective"] == "Test"
        assert len(dumped["subtasks"]) == 1
        assert dumped["subtasks"][0]["id"] == "t1"


class TestSubTaskModel:
    def test_subtask_has_required_fields(self):
        subtask = SubTask(
            id="task_1",
            type="curriculum",
            objective="Retrieve mitosis",
        )
        assert subtask.id == "task_1"
        assert subtask.type == "curriculum"
        assert subtask.objective == "Retrieve mitosis"

    def test_subtask_defaults(self):
        subtask = SubTask(id="t1", type="curriculum", objective="Test")
        assert subtask.retrieval_sources == []
        assert subtask.priority == 1
        assert subtask.expected_output == ""

    def test_subtask_serialization(self):
        subtask = SubTask(
            id="t1",
            type="curriculum",
            objective="Test",
            retrieval_sources=["curriculum"],
            priority=2,
        )
        dumped = subtask.model_dump()
        assert dumped["retrieval_sources"] == ["curriculum"]
        assert dumped["priority"] == 2


class TestEnums:
    def test_reasoning_type_values(self):
        assert ReasoningType.FACT_LOOKUP == "fact_lookup"
        assert ReasoningType.EXPLANATION == "explanation"
        assert ReasoningType.COMPARISON == "comparison"
        assert ReasoningType.MULTI_HOP == "multi_hop"
        assert ReasoningType.PERSONALIZED == "personalized"
        assert ReasoningType.SOCRATIC == "socratic"
        assert ReasoningType.REMEDIATION == "remediation"

    def test_complexity_level_values(self):
        assert ComplexityLevel.LOW == "LOW"
        assert ComplexityLevel.MEDIUM == "MEDIUM"
        assert ComplexityLevel.HIGH == "HIGH"


# ============================================================
# Prompt Tests
# ============================================================


class TestPrompts:
    def test_build_planner_prompt_basic(self):
        prompt = build_planner_prompt("What is mitosis?")
        assert "What is mitosis?" in prompt
        assert "User query:" in prompt

    def test_build_planner_prompt_with_snapshot(self):
        snapshot = {
            "weak_topics": ["cell division", "meiosis"],
            "mastery_by_topic": {"mitosis": 80, "meiosis": 45},
            "misconceptions": [{"topic": "meiosis", "frequency": 3}],
        }
        prompt = build_planner_prompt("Compare mitosis and meiosis", snapshot)
        assert "cell division" in prompt
        assert "meiosis" in prompt
        assert "Low mastery" in prompt
        assert "Active misconceptions" in prompt

    def test_build_planner_prompt_empty_snapshot(self):
        prompt = build_planner_prompt("What is mitosis?", {})
        assert "What is mitosis?" in prompt
        assert "Learner context" not in prompt


# ============================================================
# PlannerAgent Tests
# ============================================================


class TestPlannerAgent:
    @pytest.mark.asyncio
    async def test_generate_plan_success(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "objective": "Define mitosis",
                        "complexity_score": 0.2,
                        "retrieval_domains": ["curriculum"],
                        "subtasks": [
                            {
                                "id": "task_1",
                                "type": "curriculum",
                                "objective": "Retrieve mitosis definition",
                                "retrieval_sources": ["curriculum"],
                                "priority": 1,
                                "expected_output": "Mitosis content",
                            }
                        ],
                        "reasoning_type": "fact_lookup",
                        "estimated_iterations": 1,
                    }
                ),
            }
        )

        agent = PlannerAgent(mock_router)
        plan = await agent.generate_plan("What is mitosis?")

        assert isinstance(plan, Plan)
        assert plan.objective == "Define mitosis"
        assert plan.complexity_score == 0.2
        assert len(plan.subtasks) == 1
        assert plan.subtasks[0].id == "task_1"
        assert plan.reasoning_type == ReasoningType.FACT_LOOKUP

    @pytest.mark.asyncio
    async def test_generate_plan_with_snapshot(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "objective": "Compare concepts",
                        "complexity_score": 0.7,
                        "retrieval_domains": ["curriculum", "misconceptions"],
                        "subtasks": [],
                        "reasoning_type": "comparison",
                        "estimated_iterations": 1,
                    }
                ),
            }
        )

        agent = PlannerAgent(mock_router)
        snapshot = {"weak_topics": ["meiosis"]}
        plan = await agent.generate_plan("Compare mitosis and meiosis", snapshot)

        assert plan.complexity_score == 0.7
        assert "misconceptions" in plan.retrieval_domains

    @pytest.mark.asyncio
    async def test_generate_plan_fallback_on_error(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(side_effect=Exception("LLM error"))

        agent = PlannerAgent(mock_router)
        plan = await agent.generate_plan("What is mitosis?")

        assert plan == FALLBACK_PLAN
        assert plan.objective == "Fallback: single curriculum retrieval"

    @pytest.mark.asyncio
    async def test_generate_plan_fallback_on_parse_error(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={"content": "not valid json"})

        agent = PlannerAgent(mock_router)
        plan = await agent.generate_plan("What is mitosis?")

        assert plan == FALLBACK_PLAN

    def test_parse_plan_with_code_block(self):
        mock_router = MagicMock()
        agent = PlannerAgent(mock_router)

        content = """```json
{
  "objective": "Test",
  "complexity_score": 0.3,
  "retrieval_domains": ["curriculum"],
  "subtasks": [],
  "reasoning_type": "explanation",
  "estimated_iterations": 1
}
```"""
        plan = agent._parse_plan(content)
        assert plan.objective == "Test"
        assert plan.complexity_score == 0.3

    def test_parse_plan_invalid_reasoning_type(self):
        mock_router = MagicMock()
        agent = PlannerAgent(mock_router)

        content = json.dumps(
            {
                "objective": "Test",
                "reasoning_type": "invalid_type",
                "subtasks": [],
            }
        )
        plan = agent._parse_plan(content)
        assert plan.reasoning_type == ReasoningType.EXPLANATION  # Default


# ============================================================
# PlannerNode Tests
# ============================================================


class TestPlannerNode:
    @pytest.mark.asyncio
    async def test_planner_node_updates_state(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "objective": "Define mitosis",
                        "complexity_score": 0.2,
                        "retrieval_domains": ["curriculum"],
                        "subtasks": [
                            {
                                "id": "task_1",
                                "type": "curriculum",
                                "objective": "Retrieve mitosis",
                                "retrieval_sources": ["curriculum"],
                                "priority": 1,
                                "expected_output": "Mitosis content",
                            }
                        ],
                        "reasoning_type": "fact_lookup",
                        "estimated_iterations": 1,
                    }
                ),
            }
        )

        node = PlannerNode(mock_router)
        state = AgentState(user_message="What is mitosis?")

        result = await node(state)

        assert result.execution_plan != {}
        assert result.complexity_score == 0.2
        assert len(result.subtasks) == 1

    @pytest.mark.asyncio
    async def test_planner_node_with_snapshot(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "objective": "Compare",
                        "complexity_score": 0.7,
                        "retrieval_domains": ["curriculum", "misconceptions"],
                        "subtasks": [],
                        "reasoning_type": "comparison",
                        "estimated_iterations": 1,
                    }
                ),
            }
        )

        node = PlannerNode(mock_router)
        state = AgentState(
            user_message="Compare mitosis and meiosis",
            learner_snapshot={"weak_topics": ["meiosis"]},
        )

        result = await node(state)
        assert result.complexity_score == 0.7
