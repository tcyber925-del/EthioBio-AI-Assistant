"""Tests for the Query Rewriter Agent.

Tests QueryBundle/RewrittenQuery/QueryCategory models,
QueryRewriterAgent generation, fallback behavior, and prompt building.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.query_rewriter.models import QueryBundle, QueryCategory, RewrittenQuery
from src.agents.query_rewriter.prompts import build_rewriter_prompt
from src.agents.query_rewriter.query_rewriter import QueryRewriterAgent

# ============================================================
# Model Tests
# ============================================================


class TestQueryCategory:
    """Tests for the QueryCategory enum."""

    def test_all_categories_present(self):
        assert QueryCategory.CURRICULUM == "curriculum"
        assert QueryCategory.MEMORY == "memory"
        assert QueryCategory.MISCONCEPTION == "misconception"
        assert QueryCategory.LEARNER_PROFILE == "learner_profile"
        assert QueryCategory.RECOMMENDATION == "recommendation"
        assert QueryCategory.COMPARISON == "comparison"
        assert QueryCategory.DEFINITION == "definition"

    def test_seven_categories(self):
        assert len(QueryCategory) == 7


class TestRewrittenQuery:
    """Tests for the RewrittenQuery model."""

    def test_has_required_fields(self):
        rq = RewrittenQuery(
            query="meiosis stages",
            source_type="curriculum",
            purpose="Retrieve meiosis stage descriptions",
            priority=8,
        )
        assert rq.query == "meiosis stages"
        assert rq.source_type == "curriculum"
        assert rq.purpose == "Retrieve meiosis stage descriptions"
        assert rq.priority == 8

    def test_defaults(self):
        rq = RewrittenQuery(query="test")
        assert rq.source_type == "curriculum"
        assert rq.purpose == ""
        assert rq.priority == 5

    def test_priority_range(self):
        RewrittenQuery(query="low", priority=1)
        RewrittenQuery(query="high", priority=10)
        with pytest.raises(Exception):
            RewrittenQuery(query="too low", priority=0)
        with pytest.raises(Exception):
            RewrittenQuery(query="too high", priority=11)

    def test_serialization(self):
        rq = RewrittenQuery(
            query="DNA replication",
            source_type="curriculum",
            purpose="Define DNA replication",
            priority=7,
        )
        dumped = rq.model_dump()
        assert dumped["query"] == "DNA replication"
        assert dumped["priority"] == 7


class TestQueryBundle:
    """Tests for the QueryBundle model."""

    def test_has_required_fields(self):
        bundle = QueryBundle(
            original_query="What is mitosis?",
            rewritten_queries=[
                RewrittenQuery(query="mitosis definition", source_type="definition"),
                RewrittenQuery(query="mitosis stages", source_type="curriculum"),
            ],
            estimated_coverage=0.85,
        )
        assert bundle.original_query == "What is mitosis?"
        assert len(bundle.rewritten_queries) == 2
        assert bundle.estimated_coverage == 0.85

    def test_defaults(self):
        bundle = QueryBundle(original_query="test")
        assert bundle.rewritten_queries == []
        assert bundle.estimated_coverage == 0.0

    def test_coverage_range(self):
        QueryBundle(original_query="t", estimated_coverage=0.0)
        QueryBundle(original_query="t", estimated_coverage=1.0)
        with pytest.raises(Exception):
            QueryBundle(original_query="t", estimated_coverage=-0.1)
        with pytest.raises(Exception):
            QueryBundle(original_query="t", estimated_coverage=1.1)


# ============================================================
# Prompt Tests
# ============================================================


class TestPrompts:
    """Tests for prompt building."""

    def test_build_rewriter_prompt_basic(self):
        prompt = build_rewriter_prompt("What is mitosis?")
        assert "What is mitosis?" in prompt
        assert "Original Query:" in prompt

    def test_build_rewriter_prompt_with_subtasks(self):
        subtasks = [
            {"objective": "Define mitosis", "type": "curriculum"},
            {"objective": "Compare with meiosis", "type": "comparison"},
        ]
        prompt = build_rewriter_prompt("Compare mitosis and meiosis", subtasks)
        assert "Define mitosis" in prompt
        assert "Compare with meiosis" in prompt
        assert "[curriculum]" in prompt
        assert "[comparison]" in prompt

    def test_build_rewriter_prompt_with_snapshot(self):
        snapshot = {
            "weak_topics": ["cell division", "meiosis"],
            "mastery_by_topic": {"mitosis": 80, "meiosis": 45},
            "misconceptions": [{"topic": "meiosis", "frequency": 3}],
        }
        prompt = build_rewriter_prompt(
            "Help me with cell division", subtasks=None, learner_snapshot=snapshot
        )
        assert "cell division" in prompt
        assert "meiosis" in prompt
        assert "Low mastery" in prompt
        assert "Active misconceptions" in prompt

    def test_build_rewriter_prompt_empty_snapshot(self):
        prompt = build_rewriter_prompt("What is osmosis?", learner_snapshot={})
        assert "What is osmosis?" in prompt
        assert "Learner Context" not in prompt


# ============================================================
# QueryRewriterAgent Tests
# ============================================================


class TestQueryRewriterAgent:
    """Tests for the QueryRewriterAgent."""

    @pytest.mark.asyncio
    async def test_rewrite_success(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "queries": [
                            {
                                "query": "mitosis definition",
                                "category": "definition",
                                "purpose": "Define mitosis",
                                "priority": 8,
                            },
                            {
                                "query": "mitosis stages",
                                "category": "curriculum",
                                "purpose": "List mitosis stages",
                                "priority": 7,
                            },
                        ],
                        "coverage_score": 0.9,
                        "missing_topics": [],
                    }
                ),
            }
        )

        agent = QueryRewriterAgent(mock_router)
        bundle = await agent.rewrite("What is mitosis?")

        assert isinstance(bundle, QueryBundle)
        assert bundle.original_query == "What is mitosis?"
        assert len(bundle.rewritten_queries) == 2
        assert bundle.estimated_coverage == 0.9
        assert bundle.rewritten_queries[0].source_type == "definition"
        assert bundle.rewritten_queries[1].source_type == "curriculum"

    @pytest.mark.asyncio
    async def test_rewrite_with_subtasks(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "queries": [
                            {
                                "query": "mitosis vs meiosis differences",
                                "category": "comparison",
                                "purpose": "Compare mitosis and meiosis",
                                "priority": 9,
                            },
                            {
                                "query": "cell division misconceptions",
                                "category": "misconception",
                                "purpose": "Find student misconceptions",
                                "priority": 8,
                            },
                        ],
                        "coverage_score": 0.85,
                        "missing_topics": [],
                    }
                ),
            }
        )

        agent = QueryRewriterAgent(mock_router)
        subtasks = [
            {"objective": "Compare mitosis and meiosis", "type": "comparison"},
            {"objective": "Identify misconceptions", "type": "misconceptions"},
        ]
        bundle = await agent.rewrite(
            "Compare mitosis and meiosis and help with my misconceptions",
            subtasks=subtasks,
        )

        assert len(bundle.rewritten_queries) == 2
        assert bundle.rewritten_queries[0].source_type == "comparison"
        assert bundle.rewritten_queries[1].source_type == "misconception"

    @pytest.mark.asyncio
    async def test_rewrite_with_snapshot(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "queries": [
                            {
                                "query": "genetics misconceptions",
                                "category": "misconception",
                                "purpose": "Personalized misconception retrieval",
                                "priority": 9,
                            },
                            {
                                "query": "genetics learner history",
                                "category": "memory",
                                "purpose": "Past genetics interactions",
                                "priority": 8,
                            },
                        ],
                        "coverage_score": 0.8,
                        "missing_topics": [],
                    }
                ),
            }
        )

        agent = QueryRewriterAgent(mock_router)
        snapshot = {"weak_topics": ["genetics"], "misconceptions": [{"topic": "Punnett squares"}]}
        bundle = await agent.rewrite(
            "Why do I struggle with genetics?",
            learner_snapshot=snapshot,
        )

        assert len(bundle.rewritten_queries) >= 2
        assert any(rq.source_type == "misconception" for rq in bundle.rewritten_queries)
        assert any(rq.source_type == "memory" for rq in bundle.rewritten_queries)

    @pytest.mark.asyncio
    async def test_rewrite_fallback_on_llm_error(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(side_effect=Exception("LLM error"))

        agent = QueryRewriterAgent(mock_router)
        bundle = await agent.rewrite("What is photosynthesis?")

        assert isinstance(bundle, QueryBundle)
        assert len(bundle.rewritten_queries) >= 1
        assert bundle.estimated_coverage <= 0.5

    @pytest.mark.asyncio
    async def test_rewrite_fallback_on_parse_error(self):
        mock_router = AsyncMock()
        mock_router.route = AsyncMock(return_value={"content": "not valid json"})

        agent = QueryRewriterAgent(mock_router)
        bundle = await agent.rewrite("What is osmosis?")

        assert isinstance(bundle, QueryBundle)
        assert len(bundle.rewritten_queries) >= 1

    def test_parse_bundle_with_code_block(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        content = """```json
{
  "queries": [
    {
      "query": "osmosis definition",
      "category": "definition",
      "purpose": "Define osmosis",
      "priority": 9
    }
  ],
  "coverage_score": 0.95,
  "missing_topics": []
}
```"""
        bundle = agent._parse_bundle(content, "What is osmosis?")
        assert bundle.original_query == "What is osmosis?"
        assert len(bundle.rewritten_queries) == 1
        assert bundle.rewritten_queries[0].query == "osmosis definition"
        assert bundle.rewritten_queries[0].source_type == "definition"
        assert bundle.estimated_coverage == 0.95

    def test_parse_bundle_invalid_category_falls_back(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        content = json.dumps(
            {
                "queries": [
                    {
                        "query": "test query",
                        "category": "invalid_category",
                        "purpose": "test",
                        "priority": 5,
                    }
                ],
                "coverage_score": 0.5,
            }
        )
        bundle = agent._parse_bundle(content, "test")
        assert bundle.rewritten_queries[0].source_type == "curriculum"

    def test_validate_category_valid(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)
        assert agent._validate_category("memory") == "memory"
        assert agent._validate_category("comparison") == "comparison"

    def test_validate_category_invalid(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)
        assert agent._validate_category("invalid") == "curriculum"

    def test_fallback_with_subtasks(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        subtasks = [
            {"objective": "Define mitosis", "type": "curriculum"},
            {"objective": "Explain meiosis", "type": "curriculum"},
        ]
        bundle = agent._build_fallback("Compare cell division", subtasks)

        assert len(bundle.rewritten_queries) == 2
        assert bundle.rewritten_queries[0].query == "Define mitosis"
        assert bundle.rewritten_queries[1].query == "Explain meiosis"

    def test_fallback_without_subtasks(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        bundle = agent._build_fallback("What is biology?")

        assert len(bundle.rewritten_queries) == 1
        assert bundle.rewritten_queries[0].query == "What is biology?"
        assert bundle.rewritten_queries[0].source_type == "curriculum"

    def test_group_by_source(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        bundle = QueryBundle(
            original_query="test",
            rewritten_queries=[
                RewrittenQuery(query="q1", source_type="curriculum"),
                RewrittenQuery(query="q2", source_type="curriculum"),
                RewrittenQuery(query="q3", source_type="memory"),
            ],
        )

        groups = agent.group_by_source(bundle)
        assert len(groups["curriculum"]) == 2
        assert len(groups["memory"]) == 1
        assert "q1" in groups["curriculum"]
        assert "q3" in groups["memory"]

    def test_group_by_source_empty(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        bundle = QueryBundle(original_query="test")
        groups = agent.group_by_source(bundle)
        assert groups == {}

    def test_heuristic_coverage_all_covered(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        queries = [
            RewrittenQuery(query="q1", source_type="curriculum"),
            RewrittenQuery(query="q2", source_type="misconception"),
        ]
        subtasks = [
            {"objective": "Find content", "type": "curriculum"},
            {"objective": "Find misconceptions", "type": "misconception"},
        ]

        score = agent._calculate_heuristic_coverage(queries, subtasks)
        assert score == 1.0

    def test_heuristic_coverage_partial(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        queries = [RewrittenQuery(query="q1", source_type="curriculum")]
        subtasks = [
            {"objective": "Find content", "type": "curriculum"},
            {"objective": "Find memory", "type": "memory"},
        ]

        score = agent._calculate_heuristic_coverage(queries, subtasks)
        assert score == 0.5

    def test_heuristic_coverage_no_subtasks(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        score = agent._calculate_heuristic_coverage([], None)
        assert score is None

    def test_heuristic_coverage_minimum_floor(self):
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        queries = [RewrittenQuery(query="q1", source_type="memory")]
        subtasks = [
            {"objective": "Find content", "type": "curriculum"},
            {"objective": "Find misconceptions", "type": "misconception"},
            {"objective": "Find comparisons", "type": "comparison"},
        ]

        score = agent._calculate_heuristic_coverage(queries, subtasks)
        assert score == 0.1  # floor

    def test_heuristic_coverage_floors_llm_score(self):
        """Bundle coverage should be min(LLM, heuristic)."""
        mock_router = MagicMock()
        agent = QueryRewriterAgent(mock_router)

        content = """```json
{
  "queries": [
    {"query": "mitosis", "category": "curriculum", "purpose": "", "priority": 5}
  ],
  "coverage_score": 1.0
}
```"""
        subtasks = [
            {"objective": "Find content", "type": "curriculum"},
            {"objective": "Check memory", "type": "memory"},
        ]
        bundle = agent._parse_bundle(content, "test", subtasks)
        assert bundle.estimated_coverage < 1.0
        assert bundle.estimated_coverage == 0.5
