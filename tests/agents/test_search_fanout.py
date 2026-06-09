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
