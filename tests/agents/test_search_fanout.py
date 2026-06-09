"""Tests for Search Fanout models."""
import pytest
from pydantic import ValidationError

from src.agents.search_fanout.models import (
    RetrievalStrategy,
    RetrievalStrategyName,
    RetrievalTask,
)


class TestRetrievalStrategyName:
    def test_has_five_strategies(self):
        assert len(RetrievalStrategyName) == 5

    def test_values(self):
        assert RetrievalStrategyName.SIMPLE == "SIMPLE"
        assert RetrievalStrategyName.COMPARISON == "COMPARISON"
        assert RetrievalStrategyName.PERSONALIZED == "PERSONALIZED"
        assert RetrievalStrategyName.REMEDIATION == "REMEDIATION"
        assert RetrievalStrategyName.MULTI_HOP == "MULTI_HOP"


class TestRetrievalTask:
    def test_has_required_fields(self):
        task = RetrievalTask(
            id="task_1",
            query="mitosis stages",
            target_source="curriculum",
            priority=8,
            estimated_cost=0.5,
            reasoning="Core concept retrieval",
        )
        assert task.id == "task_1"
        assert task.query == "mitosis stages"
        assert task.target_source == "curriculum"
        assert task.priority == 8
        assert task.estimated_cost == 0.5
        assert task.reasoning == "Core concept retrieval"

    def test_defaults(self):
        task = RetrievalTask(
            id="t1", query="test", target_source="curriculum", priority=5
        )
        assert task.estimated_cost == 0.0
        assert task.reasoning == ""

    def test_priority_range(self):
        RetrievalTask(id="t1", query="q", target_source="c", priority=1)
        RetrievalTask(id="t2", query="q", target_source="c", priority=10)
        with pytest.raises(ValidationError):
            RetrievalTask(id="t3", query="q", target_source="c", priority=0)
        with pytest.raises(ValidationError):
            RetrievalTask(id="t4", query="q", target_source="c", priority=11)

    def test_serialization(self):
        task = RetrievalTask(
            id="t1", query="meiosis", target_source="curriculum", priority=7
        )
        dumped = task.model_dump()
        assert dumped["query"] == "meiosis"
        assert dumped["priority"] == 7


class TestRetrievalStrategy:
    def test_has_required_fields(self):
        strategy = RetrievalStrategy(
            strategy_name=RetrievalStrategyName.SIMPLE,
            retrieval_mode="single",
            parallel_execution=False,
            expected_sources=["curriculum"],
        )
        assert strategy.strategy_name == "SIMPLE"
        assert strategy.retrieval_mode == "single"
        assert strategy.parallel_execution is False
        assert strategy.expected_sources == ["curriculum"]

    def test_defaults(self):
        strategy = RetrievalStrategy(strategy_name=RetrievalStrategyName.SIMPLE)
        assert strategy.retrieval_mode == "single"
        assert strategy.parallel_execution is False
        assert strategy.expected_sources == []


# ============================================================
# Routing Tests
# ============================================================


class TestSourceRouting:
    def test_routes_curriculum(self):
        from src.agents.search_fanout.routing import SOURCE_ROUTING

        assert SOURCE_ROUTING["curriculum"] == "curriculum"

    def test_routes_memory(self):
        from src.agents.search_fanout.routing import SOURCE_ROUTING

        assert SOURCE_ROUTING["memory"] == "memory"

    def test_routes_misconception_to_memory(self):
        from src.agents.search_fanout.routing import SOURCE_ROUTING

        assert SOURCE_ROUTING["misconception"] == "memory"

    def test_routes_learner_profile(self):
        from src.agents.search_fanout.routing import SOURCE_ROUTING

        assert SOURCE_ROUTING["learner_profile"] == "learner"

    def test_routes_recommendation(self):
        from src.agents.search_fanout.routing import SOURCE_ROUTING

        assert SOURCE_ROUTING["recommendation"] == "recommendation"

    def test_routes_comparison_to_curriculum(self):
        from src.agents.search_fanout.routing import SOURCE_ROUTING

        assert SOURCE_ROUTING["comparison"] == "curriculum"

    def test_routes_definition_to_curriculum(self):
        from src.agents.search_fanout.routing import SOURCE_ROUTING

        assert SOURCE_ROUTING["definition"] == "curriculum"

    def test_unknown_source_falls_back_to_curriculum(self):
        from src.agents.search_fanout.routing import _resolve_source

        assert _resolve_source("unknown") == "curriculum"


class TestRouteQueries:
    def test_routes_single_category(self):
        from src.agents.search_fanout.routing import route_queries

        groups = {"curriculum": ["mitosis stages", "cell cycle"]}
        tasks = route_queries(groups)
        assert len(tasks) == 2
        assert all(t.target_source == "curriculum" for t in tasks)

    def test_routes_multiple_categories(self):
        from src.agents.search_fanout.routing import route_queries

        groups = {"curriculum": ["mitosis"], "memory": ["past mistakes"]}
        tasks = route_queries(groups)
        assert len(tasks) == 2
        sources = {t.target_source for t in tasks}
        assert sources == {"curriculum", "memory"}

    def test_preserves_default_priority(self):
        from src.agents.search_fanout.routing import route_queries

        groups = {"curriculum": ["meiosis"]}
        tasks = route_queries(groups, default_priority=7)
        assert all(t.priority == 7 for t in tasks)

    def test_generates_unique_ids(self):
        from src.agents.search_fanout.routing import route_queries

        groups = {"curriculum": ["q1", "q2"], "memory": ["m1"]}
        tasks = route_queries(groups)
        ids = [t.id for t in tasks]
        assert len(ids) == len(set(ids))

    def test_empty_groups(self):
        from src.agents.search_fanout.routing import route_queries

        assert route_queries({}) == []


class TestDeriveStrategy:
    def test_single_curriculum_is_simple(self):
        from src.agents.search_fanout.routing import derive_strategy

        strategy = derive_strategy({"curriculum": ["q1"]})
        assert strategy.strategy_name == "SIMPLE"
        assert strategy.parallel_execution is False
        assert strategy.retrieval_mode == "single"

    def test_curriculum_with_comparison_is_comparison(self):
        from src.agents.search_fanout.routing import derive_strategy

        strategy = derive_strategy({"curriculum": ["q1"], "comparison": ["q2"]})
        assert strategy.strategy_name == "COMPARISON"
        assert strategy.parallel_execution is True

    def test_includes_memory_is_personalized(self):
        from src.agents.search_fanout.routing import derive_strategy

        strategy = derive_strategy({"curriculum": ["q1"], "memory": ["m1"]})
        assert strategy.strategy_name == "PERSONALIZED"

    def test_includes_recommendation_is_remediation(self):
        from src.agents.search_fanout.routing import derive_strategy

        strategy = derive_strategy({"curriculum": ["q1"], "recommendation": ["r1"]})
        assert strategy.strategy_name == "REMEDIATION"

    def test_three_or_more_sources_is_multi_hop(self):
        from src.agents.search_fanout.routing import derive_strategy

        strategy = derive_strategy(
            {
                "curriculum": ["q1"],
                "memory": ["m1"],
                "recommendation": ["r1"],
            }
        )
        assert strategy.strategy_name == "MULTI_HOP"

    def test_empty_groups_defaults_to_simple(self):
        from src.agents.search_fanout.routing import derive_strategy

        strategy = derive_strategy({})
        assert strategy.strategy_name == "SIMPLE"

    def test_expected_sources_matches_groups(self):
        from src.agents.search_fanout.routing import derive_strategy

        strategy = derive_strategy({"curriculum": ["q1"], "memory": ["m1"]})
        assert "curriculum" in strategy.expected_sources
        assert "memory" in strategy.expected_sources


# ============================================================
# Agent Tests
# ============================================================


class TestSearchFanoutAgent:
    def test_plan_creates_tasks(self):
        from src.agents.search_fanout.search_fanout import SearchFanoutAgent

        agent = SearchFanoutAgent()
        groups = {
            "curriculum": ["mitosis stages"],
            "memory": ["past mistakes meiosis"],
        }
        tasks, strategy = agent.plan(groups)
        assert len(tasks) == 2
        assert strategy.strategy_name == "PERSONALIZED"

    def test_plan_single_group(self):
        from src.agents.search_fanout.search_fanout import SearchFanoutAgent

        agent = SearchFanoutAgent()
        tasks, strategy = agent.plan({"curriculum": ["default query"]})
        assert len(tasks) == 1
        assert strategy.strategy_name == "SIMPLE"
        assert tasks[0].target_source == "curriculum"

    def test_plan_empty_groups(self):
        from src.agents.search_fanout.search_fanout import SearchFanoutAgent

        agent = SearchFanoutAgent()
        tasks, strategy = agent.plan({})
        assert len(tasks) == 0
        assert strategy.strategy_name == "SIMPLE"

    def test_plan_includes_reasoning(self):
        from src.agents.search_fanout.search_fanout import SearchFanoutAgent

        agent = SearchFanoutAgent()
        groups = {"curriculum": ["meiosis"]}
        tasks, _ = agent.plan(groups)
        assert "Routed from" in tasks[0].reasoning

    def test_plan_respects_max_queries(self):
        from src.agents.search_fanout.search_fanout import SearchFanoutAgent

        agent = SearchFanoutAgent(max_queries=2)
        groups = {"curriculum": ["q1", "q2", "q3", "q4"]}
        tasks, _ = agent.plan(groups)
        assert len(tasks) <= 2
